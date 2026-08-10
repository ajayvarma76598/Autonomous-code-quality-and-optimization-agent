import os
import glob
import logging
from typing import Dict, Any, Optional
from backend.models.repository import RepositoryContext, RepositoryFingerprint
from backend.services.base_service import BaseService
from backend.services.repository.git_service import GitService
from backend.services.repository.loader import RepositoryLoader
from backend.services.repository.indexer import RepositoryIndexer
from backend.services.repository.cache import RepositoryCache

logger = logging.getLogger(__name__)

class RepositoryFacade(BaseService):
    def __init__(self):
        super().__init__("RepositoryFacade")
        self.git_service = GitService()
        self.loader = RepositoryLoader()
        self.indexer = RepositoryIndexer()
        
    def get_repository_context(self, repo_url_or_path: str, branch: str = "main") -> RepositoryContext:
        def _get_context():
            logger.info(f"RepositoryFacade fetching context for {repo_url_or_path} (branch: {branch})")
            
            if not repo_url_or_path:
                repos_dir = os.path.join(os.getcwd(), ".repos")
                if os.path.exists(repos_dir):
                    subdirs = [os.path.join(repos_dir, d) for d in os.listdir(repos_dir) if os.path.isdir(os.path.join(repos_dir, d))]
                    target_path = subdirs[0] if subdirs else os.getcwd()
                else:
                    target_path = os.getcwd()
            else:
                target_path = repo_url_or_path

            repo_id = str(target_path).split("/")[-1].split("\\")[-1].replace(".git", "")
            
            local_path = None
            if str(target_path).startswith("http") or str(target_path).startswith("git@"):
                # 1. Check if repository is already cloned locally in TEMP or .repos
                temp_dir = os.environ.get("TEMP", "/tmp")
                possible_temps = glob.glob(os.path.join(temp_dir, f"repo_{repo_id}*"))
                possible_repos = os.path.join(os.getcwd(), ".repos", repo_id)
                
                if possible_temps and os.path.exists(possible_temps[-1]):
                    local_path = possible_temps[-1]
                    logger.info(f"Using existing local cloned repository at '{local_path}'")
                elif os.path.exists(possible_repos):
                    local_path = possible_repos
                    logger.info(f"Using existing .repos directory at '{local_path}'")
                else:
                    try:
                        local_path = self.git_service.clone(target_path, branch)
                    except Exception as e:
                        logger.warning(f"Git clone failed for '{target_path}': {e}. Searching fallback temp repos.")
                        all_temps = glob.glob(os.path.join(temp_dir, "repo_*"))
                        if all_temps:
                            local_path = all_temps[-1]
                            logger.info(f"Falling back to local repo directory '{local_path}'")
                        else:
                            local_path = os.getcwd()
            else:
                if target_path and os.path.exists(str(target_path)) and os.path.isdir(str(target_path)):
                    local_path = str(target_path)
                else:
                    local_path = os.getcwd()

            if not local_path:
                local_path = os.getcwd()
                
            commit = self.git_service.get_commit(local_path) or "unknown_commit"
            
            # Check Cache
            cached_context = RepositoryCache.get(repo_url_or_path, commit)
            if cached_context:
                logger.info("RepositoryContext found in cache! Skipping parsing.")
                return cached_context
            
            import hashlib
            lang_hash = hashlib.sha256(f"{local_path}_lang".encode()).hexdigest()[:16]
            dep_hash = hashlib.sha256(f"{local_path}_deps".encode()).hexdigest()[:16]
            
            # Create Fingerprint
            fingerprint = RepositoryFingerprint(
                commit=commit,
                branch=branch,
                repo_id=repo_id,
                language_hash=lang_hash,
                dependency_hash=dep_hash
            )
            
            # Load metadata
            parsed_metadata = self.loader.load_metadata(local_path) or {}
            

            
            # Construct and return immutable context
            context = RepositoryContext(
                fingerprint=fingerprint,
                local_path=local_path,
                parsed_metadata=parsed_metadata,
                affected_files=None
            )
            
            # Save to Cache
            RepositoryCache.set(repo_url_or_path, commit, context)
            
            return context
            
        res = self.execute(_get_context)
        if not res.success or res.data is None:
            raise RuntimeError(f"Failed to get repository context: {res.error}")
        return res.data

# Keep the old variable name for backward compatibility with imports
repository_service = RepositoryFacade()
