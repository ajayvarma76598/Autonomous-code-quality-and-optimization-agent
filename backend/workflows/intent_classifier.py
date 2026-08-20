import logging
import re
from enum import StrEnum

logger = logging.getLogger(__name__)


class ComplexityLevel(StrEnum):
    L1_RETRIEVAL = "L1"  # Fast retrieval/lookup only (< 1.5s)
    L2_SINGLE_AGENT = "L2"  # Single domain worker agent (2 - 4s)
    L3_MULTI_AGENT = "L3"  # Parallel multi-agent domain review (4 - 8s)
    L4_FULL_AUDIT = "L4"  # Complete system audit (10 - 20s)


class IntentClassifier:
    """
    Dynamic Rule-Based Intent & Complexity Classifier.
    Classifies user natural language queries into L1-L4 complexity tiers
    without invoking slow LLM orchestration for 85%+ of requests.
    """

    def __init__(self):
        # L1: Direct Retrieval Patterns (file lookups, directory lists, component enumeration)
        self.l1_patterns = [
            re.compile(
                r"\b(list|show|find|get|display|where is|locate)\b.*\b(file|files|"
                r"controller|service|module|folder|directory|class|classes|function|"
                r"functions|endpoint|endpoints)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"^\s*(what|which)\s+(files|controllers|services|modules|classes|functions)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(repository structure|folder structure|file tree)\b", re.IGNORECASE
            ),
        ]

        # L2: Targeted Single-Domain Agent Patterns
        self.l2_agent_patterns = {
            "architecture": [
                re.compile(
                    r"\b(architecture|design pattern|diagram|solid|dependency graph|"
                    r"component interaction|module flow)\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(how does|explain how)\b.*\b(work|interact|communicate|connect|integrate)\b",
                    re.IGNORECASE,
                ),
            ],
            "performance": [
                re.compile(
                    r"\b(performance|bottleneck|slow|memory leak|big o|complexity|n\+1|latency|optimize|speed up)\b",
                    re.IGNORECASE,
                ),
            ],
            "coverage": [
                re.compile(
                    r"\b(test|coverage|unit test|mock|edge case|missing test|qa|uncovered)\b",
                    re.IGNORECASE,
                ),
            ],
            "quality": [
                re.compile(
                    r"\b(code smell|refactor|quality|clean code|sonar|cyclomatic|duplication|lint)\b",
                    re.IGNORECASE,
                ),
            ],
            "documentation": [
                re.compile(
                    r"\b(document|docstring|readme|generate docs|api doc|swagger)\b",
                    re.IGNORECASE,
                ),
            ],
        }

        # L4: Full Audit Patterns
        self.l4_patterns = [
            re.compile(
                r"\b(full audit|complete audit|entire codebase|entire repository|"
                r"comprehensive security review|deep systemic scan)\b",
                re.IGNORECASE,
            ),
        ]

    def classify(self, query: str) -> tuple[ComplexityLevel, str | None, list[str]]:
        """
        Dynamically classifies a natural language query string.
        Returns:
            - ComplexityLevel (L1, L2, L3, L4)
            - Primary Target Agent (or None for L1/L3/L4)
            - List of target workers
        """
        clean_q = query.strip()

        # 1. Check L4 Full System Audit
        for pat in self.l4_patterns:
            if pat.search(clean_q):
                logger.info(
                    f"[IntentClassifier] Query '{clean_q[:40]}...' classified as L4_FULL_AUDIT"
                )
                return (
                    ComplexityLevel.L4_FULL_AUDIT,
                    "manager",
                    ["architecture", "coverage", "performance", "quality"],
                )

        # 2. Check L1 Direct Retrieval
        for pat in self.l1_patterns:
            if pat.search(clean_q):
                logger.info(
                    f"[IntentClassifier] Query '{clean_q[:40]}...' classified as L1_RETRIEVAL"
                )
                return ComplexityLevel.L1_RETRIEVAL, "repository", ["repository"]

        # 3. Check L2 Targeted Single Agent
        for agent_name, patterns in self.l2_agent_patterns.items():
            for pat in patterns:
                if pat.search(clean_q):
                    logger.info(
                        f"[IntentClassifier] Query '{clean_q[:40]}...' classified as L2_SINGLE_AGENT ({agent_name})"
                    )
                    return ComplexityLevel.L2_SINGLE_AGENT, agent_name, [agent_name]

        # 4. Default to L3 Multi-Agent Parallel Review if query is broad or unspecified
        logger.info(
            f"[IntentClassifier] Query '{clean_q[:40]}...' classified as L3_MULTI_AGENT (Default Parallel)"
        )
        return (
            ComplexityLevel.L3_MULTI_AGENT,
            "manager",
            ["architecture", "coverage", "performance"],
        )


intent_classifier = IntentClassifier()
