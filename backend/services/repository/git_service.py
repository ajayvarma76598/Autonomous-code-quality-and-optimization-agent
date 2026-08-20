from backend.ingestion.git import git_service as underlying_git
from backend.services.base_service import BaseService


class GitService(BaseService):
    def __init__(self):
        super().__init__("GitService")

    def clone(self, url: str, branch: str = "main") -> str:
        def _clone():
            return underlying_git.clone_repository(url, branch)

        return self.execute(_clone).data

    def get_commit(self, local_path: str) -> str:
        def _get_commit():
            info = underlying_git.get_latest_commit(local_path)
            return info.get("commit_hash", "unknown_commit")

        res = self.execute(_get_commit)
        if res.success and res.data:
            return str(res.data)
        return "unknown_commit"
