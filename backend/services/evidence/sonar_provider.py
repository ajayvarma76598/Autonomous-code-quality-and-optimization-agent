import logging

from backend.models.evidence import EvidenceBlock
from backend.services.evidence.base_provider import BaseEvidenceProvider

logger = logging.getLogger(__name__)


class SonarProvider(BaseEvidenceProvider):
    @property
    def provider_name(self) -> str:
        return "SonarQube"

    @property
    def default_confidence(self) -> float:
        return 0.95

    def fetch(
        self, repository_id: str, analysis_id: str | None = None, **kwargs
    ) -> EvidenceBlock | None:
        try:
            from backend.database.models.models import CodeQualityMetric, RepositoryFile
            from backend.database.session import SessionLocal

            db = SessionLocal()
            try:
                from backend.database.models.models import RepositorySnapshot

                snap = None
                if repository_id:
                    try:
                        from uuid import UUID

                        repo_uuid = UUID(str(repository_id))
                        snap = (
                            db.query(RepositorySnapshot)
                            .filter(RepositorySnapshot.snapshot_id == repo_uuid)
                            .first()
                        )
                        if not snap:
                            snap = (
                                db.query(RepositorySnapshot)
                                .filter(RepositorySnapshot.repository_id == repo_uuid)
                                .order_by(RepositorySnapshot.indexed_at.desc())
                                .first()
                            )
                    except Exception:
                        snap = None

                if not snap:
                    return None
                if snap:
                    files = (
                        db.query(RepositoryFile)
                        .filter(RepositoryFile.snapshot_id == snap.snapshot_id)
                        .all()
                    )
                    file_ids = [f.file_id for f in files]
                    metrics = (
                        db.query(CodeQualityMetric)
                        .filter(CodeQualityMetric.file_id.in_(file_ids))
                        .all()
                        if file_ids
                        else []
                    )
                else:
                    files = []
                    metrics = []

                if metrics:
                    avg_coverage = sum(
                        m.test_coverage_percentage or 0.0 for m in metrics
                    ) / len(metrics)
                    total_complexity = sum(
                        m.cyclomatic_complexity or 0.0 for m in metrics
                    )
                    total_smells = sum(m.code_smell_count or 0 for m in metrics)
                    total_vulnerabilities = sum(
                        m.security_vulnerability_count or 0 for m in metrics
                    )
                    total_bugs = sum(getattr(m, "bugs_count", 0) or 0 for m in metrics)
                    total_hotspots = sum(
                        getattr(m, "security_hotspots_count", 0) or 0 for m in metrics
                    )
                    avg_maintainability = sum(
                        m.maintainability_index or 0.0 for m in metrics
                    ) / len(metrics)
                    gate_passed = all(
                        (m.test_coverage_percentage or 0) >= 80.0 for m in metrics
                    )
                    data = f"Coverage: {avg_coverage:.1f}%, Quality Gate: {gate_passed}, Bugs: {total_bugs}, Code Smells: {total_smells}, Security Vulnerabilities: {total_vulnerabilities}, Security Hotspots: {total_hotspots}, Complexity: {int(total_complexity)}, Maintainability Index: {avg_maintainability:.1f}"
                elif files:
                    file_count = len(files)
                    total_lines = sum(f.line_count or 0 for f in files)
                    data = (
                        f"SonarQube scan has not run yet for this repository snapshot. "
                        f"Repository contains {file_count} files ({total_lines} total lines). "
                        f"Trigger a SonarQube scan to populate metrics."
                    )
                else:
                    data = "SonarQube metrics analysis uninitialized in database."
            finally:
                db.close()
        except Exception as e:
            logger.error(f"SonarProvider query error: {e}")
            data = "SonarQube metrics analysis uninitialized in database."

        return EvidenceBlock(
            data=data,
            confidence_score=self.default_confidence,
            provider_name=self.provider_name,
        )


sonar_provider = SonarProvider()
