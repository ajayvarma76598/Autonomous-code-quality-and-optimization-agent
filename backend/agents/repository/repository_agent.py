import logging
from langchain_core.messages import AIMessage
from backend.workflows.state import AgentState, StateManager, TaskStatus
from backend.agents.base_agent import BaseAgent
from backend.services.repository_service import repository_service

logger = logging.getLogger(__name__)

class RepositoryAgent(BaseAgent):
    def __init__(self):
        super().__init__("repository")

    def execute(self, state: AgentState) -> AgentState:
        """
        Ingests the repository and publishes a clean, immutable RepositoryContext to the shared state.
        Removes direct Git operations and eager-parsing tools from the agent.
        """
        session_id = state.get('shared', {}).get('session_id', 'unknown')
        logger.info(f"Repository Agent processing state for session {session_id}")
        
        shared = state.get('shared', {})
        repo_path_or_url = shared.get('repo_path_or_url') or shared.get('repository_path')
        snapshot_id = shared.get('snapshot_id')
        repository_id = shared.get('repository_id')
        
        from backend.database.session import SessionLocal
        from backend.database.models.models import Repository, RepositorySnapshot
        db = SessionLocal()
        try:
            snap = None
            if snapshot_id:
                snap = db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == snapshot_id).first()
            if not snap and repository_id:
                try:
                    from uuid import UUID
                    repo_uuid = UUID(str(repository_id))
                    snap = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_uuid).order_by(RepositorySnapshot.indexed_at.desc()).first()
                except Exception:
                    snap = None
            if not snap:
                snap = db.query(RepositorySnapshot).order_by(RepositorySnapshot.indexed_at.desc()).first()
                
            if snap and snap.repository_id:
                repo = db.query(Repository).filter(Repository.repository_id == snap.repository_id).first()
                if repo:
                    if repo.git_url:
                        repo_path_or_url = repo.git_url
                    elif repo.name:
                        import os
                        possible_local = os.path.join(os.getcwd(), ".repos", repo.name)
                        if os.path.exists(possible_local):
                            repo_path_or_url = possible_local
        except Exception as db_e:
            logger.warning(f"Failed to lookup repository git_url from DB: {db_e}")
        finally:
            db.close()

        if not repo_path_or_url:
            query_val = shared.get('query', '')
            import os
            if query_val and (query_val.startswith('http') or query_val.startswith('git@') or (os.path.exists(query_val) and os.path.isdir(query_val))):
                repo_path_or_url = query_val
            else:
                # Check for any cloned repos in .repos directory
                import os
                repos_dir = os.path.join(os.getcwd(), ".repos")
                if os.path.exists(repos_dir):
                    subdirs = [os.path.join(repos_dir, d) for d in os.listdir(repos_dir) if os.path.isdir(os.path.join(repos_dir, d))]
                    if subdirs:
                        repo_path_or_url = subdirs[0]
        
        try:
            # 1. Delegate mechanical parsing and cloning to the service
            context = repository_service.get_repository_context(repo_path_or_url)
            if not context:
                raise ValueError("Repository service returned empty context")
            
            # 2. Publish the immutable context to the SharedState
            if "shared" not in state:
                state["shared"] = {}
            state["shared"]["repository_context"] = context
            
            # 3. Fetch canonical data and persist it (Phase 16B)
            from backend.services.persistence_service import persistence_service
            from backend.services.quality_service import quality_service
            
            analysis_id = session_id
            repository_id = context.fingerprint.repo_id or session_id
            
            # Persist Metadata
            persistence_service.queue_metadata(analysis_id, context.parsed_metadata)
            
            # Persist Sonar Metrics
            sonar_context = quality_service.fetch_sonar_context(context.local_path)
            persistence_service.queue_sonar_metrics(analysis_id, "global", sonar_context)
            
            # Persist Dependencies dynamically from DB
            from backend.database.session import SessionLocal
            from backend.database.models.models import DependencyRelationship
            db = SessionLocal()
            try:
                db_deps = db.query(DependencyRelationship).all()
                deps = [{"source": str(d.source_object_id), "target": str(d.target_object_id), "type": d.relationship_type or "import"} for d in db_deps] if db_deps else []
            finally:
                db.close()
            persistence_service.queue_dependencies(analysis_id, deps)
            
            # 4. We can optionally do some LLM reasoning here based on the context's parsed_metadata 
            # if we wanted to summarize it, but the main goal is providing the context to downstream agents.
            summary_msg = f"Repository successfully processed. Fingerprint: {context.fingerprint.commit} ({context.fingerprint.branch}). Available at: {context.local_path}"
            
            state = StateManager.append_message(state, AIMessage(content=summary_msg))
            state = StateManager.update_workflow_status(state, TaskStatus.COMPLETE)
            
        except Exception as e:
            logger.error(f"Failed to process repository: {e}")
            state = StateManager.append_message(state, AIMessage(content=f"Repository ingestion failed: {e}"))
            state = StateManager.update_workflow_status(state, TaskStatus.FAILED)
            
        return state
