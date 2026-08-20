from pydantic import BaseModel, Field


class RetrievalIntent(BaseModel):
    query: str = Field(description="The refined search query.")
    search_type: str = Field(
        description="One of: 'ast', 'dependency', 'semantic', 'exact'."
    )
    target_modules: list[str] = Field(
        default_factory=list,
        description="Specific modules or directories to restrict the search to.",
    )


class RetrievalPlan(BaseModel):
    intents: list[RetrievalIntent] = Field(
        description="List of targeted retrieval intents."
    )


class QueryPlanner:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, user_question: str, context: str = "") -> list[RetrievalIntent]:
        """
        Translates a natural language question from an agent into targeted retrieval intents via LLM.
        """
        try:
            structured_llm = self.llm.with_structured_output(
                RetrievalPlan, method="function_calling"
            )
            prompt = f"Deconstruct this user question into 1-3 targeted code/doc retrieval intents:\nUser Question: '{user_question}'\nContext: '{context}'"
            plan_obj: RetrievalPlan = structured_llm.invoke(prompt)
            if plan_obj and plan_obj.intents:
                return plan_obj.intents
        except Exception:
            pass

        # Dynamic fallback based on query keywords
        q_lower = user_question.lower()
        search_type = (
            "ast"
            if ("class" in q_lower or "function" in q_lower)
            else "dependency"
            if "dep" in q_lower
            else "semantic"
        )
        return [
            RetrievalIntent(query=user_question, search_type=search_type),
            RetrievalIntent(query=user_question, search_type="semantic"),
        ]
