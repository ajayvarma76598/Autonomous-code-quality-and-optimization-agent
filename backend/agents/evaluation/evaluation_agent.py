import logging
from langchain_core.messages import AIMessage
from backend.workflows.state import AgentState, StateManager, TaskStatus
from backend.agents.base_agent import BaseAgent
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class EvaluationFailure(BaseModel):
    category: Literal["Accuracy", "Security", "Completeness", "Formatting"] = Field(description="The category of the failure.")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(description="The severity of the failure.")
    message: str = Field(description="A detailed message explaining what failed.")
    suggested_fix: str = Field(description="A targeted suggestion on how to fix this specific failure without regenerating the entire response.")

class ClaimEvidenceValidation(BaseModel):
    claim: str = Field(description="The specific factual statement or finding in the output.")
    evidence_state: Literal["STRONG", "PARTIAL", "MISSING"] = Field(description="STRONG if backed by source code/AST/Sonar, PARTIAL if backed by docs, MISSING if unsupported.")
    evidence_type: Literal["SOURCE_CODE", "STATIC_ANALYSIS", "SQL_METADATA", "DOCUMENTATION", "INFERRED"] = Field(description="The provenance tier of the supporting evidence.")
    confidence: float = Field(description="Calibrated confidence score (0.0 to 1.0) based on evidence provenance.")
    reasoning: str = Field(description="Explanation of the evidence grounding state.")

class EvaluationResult(BaseModel):
    verdict: Literal["PASS", "RETRY", "FAIL"] = Field(description="PASS if acceptable, RETRY if fixable, FAIL if fundamentally broken or ungrounded.")
    critique: str = Field(default="", description="Detailed qualitative feedback explaining the verdict.")
    confidence_score: float = Field(description="Calibrated aggregate confidence score from 0.0 to 1.0.")
    total_claims: int = Field(default=1, description="Total number of factual statements in the output.")
    supported_claims: int = Field(default=1, description="Number of factual statements backed by STRONG or PARTIAL evidence.")
    claim_faithfulness_score: float = Field(default=1.0, description="Calculated ratio: supported_claims / total_claims.")
    claim_validations: List[ClaimEvidenceValidation] = Field(default_factory=list, description="Per-claim 3-state evidence validations.")
    failures: List[EvaluationFailure] = Field(default_factory=list, description="List of specific failures if the verdict is not PASS.")
    critique: str = Field(description="Detailed reasoning for the verdict.")

class EvaluationAgent(BaseAgent):
    def __init__(self):
        super().__init__("evaluation")

    def execute(self, state: AgentState) -> AgentState:
        """
        Handles requests to evaluate LLM responses, faithfulness, and benchmark queries.
        Uses a ChatPromptTemplate to cleanly inject the question and the draft answer.
        Forces the LLM to output precise structured mathematical scores via Pydantic.
        """
        session_id = state.get('shared', {}).get('session_id', 'unknown')
        logger.info(f"Evaluation Agent processing state for session {session_id}")
        
        from langchain_core.prompts import ChatPromptTemplate
        
        import time
        start_time = time.time()
        draft = state.get("final_response", "No draft provided.")
        query = state.get("shared", {}).get("query", "")
        
        # Tier 1 Optimization Check: Skip Tier 2 LLM Evaluation if Deterministic Validation passed!
        existing_eval = state.get("analysis", {}).get("evaluation", {})
        if isinstance(existing_eval, dict) and not existing_eval.get("requires_llm_eval", True):
            logger.info(f"[EvaluationAgent] [Tier 1 Optimization] Deterministic Validation passed (Confidence: {existing_eval.get('confidence', 0.90)}). Skipping Tier 2 LLM evaluation.")
            return state

        eval_template = ChatPromptTemplate.from_messages([
            ("system", "You are an impartial Quality Gate and Anti-Hallucination Evaluator.\n"
                       "Your job is to evaluate each claim in the draft answer against the task requirements and evidence.\n"
                       "EVIDENCE VALIDATION RULES:\n"
                       "1. Classify each claim into a 3-State Evidence Validation:\n"
                       "   - STRONG: Directly supported by Source Code, AST nodes, or SonarQube static analysis (Trust: 0.90 - 0.99).\n"
                       "   - PARTIAL: Supported by documentation text or generalized summaries (Trust: 0.45 - 0.60).\n"
                       "   - MISSING: Unsupported or hallucinated assumption (Trust: 0.10 - 0.30).\n"
                       "2. If more than 30% of claims are MISSING evidence, you MUST flag verdict as RETRY or FAIL.\n"
                       "3. If any leaked API keys, tokens, or PII are found, fail immediately with Security category."),
            ("human", "Task Context:\n{question}\n\nActual Output:\n{draft_answer}")
        ])
        
        # Isolate inputs to strictly task and output
        draft = state.get("final_response", "No draft provided.")
        query = state.get("shared", {}).get("query", "")
        
        messages = eval_template.format_messages(
            question=query, 
            draft_answer=draft
        )
        
        # Invoke the LLM natively, forcing Structured Output with full agent run_name
        structured_llm = self.llm.with_structured_output(EvaluationResult, method="function_calling").with_config({"run_name": "EvaluationAgent"})
        result = structured_llm.invoke(messages)
        
        eval_duration = time.time() - start_time
        logger.info(f"Evaluation took {eval_duration:.2f}s. Verdict: {result.verdict} (Confidence: {result.confidence_score})")
        
        # Scrub the critique of deterministic PII (Email, Phone, IP, Credit Cards)
        from backend.services.pii_service import pii_service
        result.critique = pii_service.anonymize_text(result.critique)
            
        # The Evaluation Agent NO LONGER mutates workflow state or routes!
        # It strictly places the verdict in the analysis dictionary.
        # Compute faithfulness as ratio of supported/total claims
        faithfulness = round(result.claim_faithfulness_score, 4) if result.total_claims > 0 else round(result.confidence_score, 4)
        # Relevancy: use confidence_score as proxy since the LLM judges overall quality
        relevancy = round(result.confidence_score, 4)
        # Recall: fraction of supported (STRONG) claims out of total
        strong_claims = sum(1 for c in result.claim_validations if c.evidence_state == "STRONG")
        recall = round(strong_claims / result.total_claims, 4) if result.total_claims > 0 else 0.0
        # Context precision: fraction of STRONG claims out of all non-missing
        non_missing = sum(1 for c in result.claim_validations if c.evidence_state != "MISSING")
        context_precision = round(strong_claims / non_missing, 4) if non_missing > 0 else 0.0

        eval_metrics = {
            "verdict":              result.verdict,
            "confidence":           result.confidence_score,
            "faithfulness":         faithfulness,
            "relevancy":            relevancy,
            "recall":               recall,
            "context_precision":    context_precision,
            "total_claims":         result.total_claims,
            "supported_claims":     result.supported_claims,
            "failures":             [f.dict() for f in result.failures],
            "critique":             result.critique,
            "eval_duration_seconds": eval_duration,
        }

        state = StateManager.save_analysis(state, "evaluation", eval_metrics)
        
        # Persist evaluation metrics to database
        try:
            from backend.database.session import SessionLocal
            from backend.repositories.evaluation_repository import evaluation_repository
            db = SessionLocal()
            try:
                workflow_id = state.get("workflow_id")
                evaluation_repository.save_evaluation(
                    db=db,
                    workflow_id=workflow_id,
                    metrics_data=eval_metrics,
                    passed=(result.verdict == "PASS")
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to persist evaluation metrics to DB: {e}")
        
        state = StateManager.append_message(state, AIMessage(content=f"Evaluator Verdict: {result.verdict}\nCritique: {result.critique}"))
        
        return state
