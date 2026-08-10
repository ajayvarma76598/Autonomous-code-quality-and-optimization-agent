from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SonarFinding(BaseModel):
    rule_id: str = Field(description="The SonarQube rule ID.")
    severity: str = Field(description="Severity (e.g. BLOCKER, CRITICAL, MAJOR).")
    component: str = Field(description="The file path or component name.")
    line: Optional[int] = Field(default=None, description="The line number where the issue occurs.")
    message: str = Field(description="Description of the issue.")
    effort: Optional[str] = Field(default=None, description="Estimated remediation effort.")
    type: str = Field(description="Type of issue (BUG, VULNERABILITY, CODE_SMELL).")
    tags: List[str] = Field(default_factory=list, description="Tags associated with the finding.")

class SonarContext(BaseModel):
    issues: List[SonarFinding] = Field(default_factory=list, description="List of normalized SonarQube findings.")
    coverage: float = Field(default=0.0, description="Overall test coverage percentage.")
    duplication: float = Field(default=0.0, description="Code duplication percentage.")
    complexity: int = Field(default=0, description="Total cyclomatic complexity of the project.")
    hotspots: List[Dict[str, Any]] = Field(default_factory=list, description="Security hotspots.")
    quality_gate_passed: bool = Field(default=True, description="Whether the project passed the Sonar quality gate.")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional raw metrics from the scanner.")
