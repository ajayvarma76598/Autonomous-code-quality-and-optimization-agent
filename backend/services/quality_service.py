from backend.models.quality import SonarContext, SonarFinding
from backend.services.base_service import BaseService


class QualityIntelligenceService(BaseService):
    def __init__(self):
        super().__init__("QualityIntelligenceService")

    def fetch_sonar_context(
        self, repo_url_or_path: str, branch: str = "main"
    ) -> SonarContext:
        """
        Queries CodeQualityMetric from PostgreSQL database and returns a normalized SonarContext.
        """

        def _fetch():
            from backend.database.models.models import CodeQualityMetric
            from backend.database.session import SessionLocal

            db = SessionLocal()
            try:
                metrics = db.query(CodeQualityMetric).all()
                if metrics:
                    avg_coverage = sum(
                        m.test_coverage_percentage or 0.0 for m in metrics
                    ) / len(metrics)
                    total_complexity = sum(
                        m.cyclomatic_complexity or 0.0 for m in metrics
                    )
                    total_smells = sum(m.code_smell_count or 0 for m in metrics)
                    gate_passed = all(
                        (m.test_coverage_percentage or 0) >= 80.0 for m in metrics
                    )

                    findings = [
                        SonarFinding(
                            rule_id="sonar:CQM01",
                            severity="HIGH" if total_smells > 500 else "MEDIUM",
                            component="repository_files",
                            message=f"Aggregate cyclomatic complexity across metrics: {int(total_complexity)}",
                            effort="45min",
                            type="CODE_SMELL",
                        )
                    ]
                    return SonarContext(
                        issues=findings,
                        coverage=round(avg_coverage, 1),
                        duplication=0.0,
                        complexity=int(total_complexity),
                        quality_gate_passed=gate_passed,
                    )
                else:
                    return SonarContext(
                        issues=[],
                        coverage=0.0,
                        duplication=0.0,
                        complexity=0,
                        quality_gate_passed=False,
                    )
            finally:
                db.close()

        return self.execute(_fetch).data


quality_service = QualityIntelligenceService()
