import logging

from backend.models.evidence import EvidenceBlock
from backend.services.evidence.base_provider import BaseEvidenceProvider

logger = logging.getLogger(__name__)


class MetadataProvider(BaseEvidenceProvider):
    @property
    def provider_name(self) -> str:
        return "RepositoryMetadata"

    @property
    def default_confidence(self) -> float:
        return 1.0

    def fetch(
        self, repository_id: str, analysis_id: str | None = None, **kwargs
    ) -> EvidenceBlock | None:
        try:
            from backend.database.models.models import Repository, RepositoryMetadata
            from backend.database.session import SessionLocal

            db = SessionLocal()
            try:
                from backend.database.models.models import RepositorySnapshot

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

                meta = (
                    db.query(RepositoryMetadata)
                    .filter(RepositoryMetadata.snapshot_id == snap.snapshot_id)
                    .first()
                )
                repo = (
                    db.query(Repository)
                    .filter(Repository.repository_id == snap.repository_id)
                    .first()
                )

                language = (
                    repo.default_language
                    if repo and repo.default_language
                    else "unknown"
                )
                tech_stack = (
                    meta.technology_stack if meta and meta.technology_stack else {}
                )

                data = {
                    "language": language,
                    "technology_stack": tech_stack,
                    "architecture_summary": meta.architecture_summary
                    if meta and meta.architecture_summary
                    else "Architecture summary not yet generated. Please re-ingest the repository.",
                    "entry_points": meta.entry_points
                    if meta and meta.entry_points
                    else [],
                }
            finally:
                db.close()
        except Exception as e:
            logger.info(f"MetadataProvider fallback query: {e}")
            data = {
                "language": "unknown",
                "framework": "unknown",
                "architecture": "unknown",
            }

        return EvidenceBlock(
            data=data,
            confidence_score=self.default_confidence,
            provider_name=self.provider_name,
        )


metadata_provider = MetadataProvider()
