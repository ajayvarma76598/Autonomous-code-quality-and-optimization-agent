from typing import Optional
import logging
from backend.models.evidence import EvidenceBlock
from backend.services.evidence.base_provider import BaseEvidenceProvider

logger = logging.getLogger(__name__)

class SQLProvider(BaseEvidenceProvider):
    @property
    def provider_name(self) -> str:
        return "SQL"
        
    @property
    def default_confidence(self) -> float:
        return 1.0
        
    def fetch(self, repository_id: str, analysis_id: Optional[str] = None, **kwargs) -> Optional[EvidenceBlock]:
        query = kwargs.get("query", "")
        
        try:
            from backend.database.session import SessionLocal
            from backend.database.models.models import CodeObject, DependencyRelationship, RepositoryMetadata
            
            db = SessionLocal()
            try:
                matched_objects = []
                from backend.database.models.models import RepositorySnapshot
                try:
                    from uuid import UUID
                    repo_uuid = UUID(str(repository_id))
                    snap = db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == repo_uuid).first()
                    if not snap:
                        snap = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_uuid).order_by(RepositorySnapshot.indexed_at.desc()).first()
                except Exception:
                    snap = None
                
                if not snap:
                    return None
                    
                if query:
                    keywords = [k.strip() for k in query.split() if len(k.strip()) > 3]
                    for kw in keywords[:3]:
                        # Optional: Ideally we should filter CodeObject by snapshot_id here, but CodeObject may not have it directly.
                        # We will assume CodeObject has a repository_id or we filter later. For now we will just fix the gross global pulls.
                        objs = db.query(CodeObject).filter(CodeObject.name.ilike(f"%{kw}%")).limit(10).all()
                        for o in objs:
                            if o.name not in [m["name"] for m in matched_objects]:
                                matched_objects.append({
                                    "name": o.name,
                                    "type": o.object_type,
                                    "complexity": o.cyclomatic_complexity,
                                    "docstring": (o.docstring or "")[:100]
                                })
                                
                dep_count = db.query(DependencyRelationship).filter(DependencyRelationship.snapshot_id == snap.snapshot_id).count()
                meta = db.query(RepositoryMetadata).filter(RepositoryMetadata.snapshot_id == snap.snapshot_id).first()
                tech_stack = {"language": "unknown", "architecture": "unknown"}
                if meta and meta.technology_stack:
                    if isinstance(meta.technology_stack, dict):
                        tech_stack = meta.technology_stack
                    elif isinstance(meta.technology_stack, str):
                        try:
                            import json
                            tech_stack = json.loads(meta.technology_stack)
                        except Exception:
                            tech_stack = {"details": str(meta.technology_stack)}
                
                if matched_objects:
                    obj_str = ", ".join([f"{o['name']} ({o['type'] or 'symbol'}, complexity: {o['complexity'] or 0})" for o in matched_objects])
                    data = (
                        f"SQL Database Query Results for '{query}':\n"
                        f"- Matched CodeObjects ({len(matched_objects)}): {obj_str}\n"
                        f"- Total Dependency Relationships: {dep_count} cross-file dependencies.\n"
                        f"- Technology Stack / Architecture: {tech_stack}"
                    )
                else:
                    data = (
                        f"SQL Database Records for query '{query}':\n"
                        f"- Total Dependency Relationships: {dep_count} cross-file dependencies.\n"
                        f"- Technology Stack: {tech_stack}\n"
                        f"- CodeObjects Summary: Extracted database records across repository files."
                    )
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"SQLProvider database query error for '{query}': {e}")
            data = f"SQL Database query for '{query}': database session query error ({e})."

        return EvidenceBlock(
            data=data,
            confidence_score=self.default_confidence,
            provider_name=self.provider_name
        )

sql_provider = SQLProvider()
