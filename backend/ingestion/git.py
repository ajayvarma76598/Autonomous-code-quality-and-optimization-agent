import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)


class GitService:
    def __init__(self):
        env_dir = os.environ.get("REPOS_STORAGE_DIR")
        if env_dir:
            self.workspace_dir = env_dir
        else:
            self.workspace_dir = os.path.join(os.getcwd(), ".repos")
        os.makedirs(self.workspace_dir, exist_ok=True)

    def clone_repository(self, git_url: str, branch: str | None = None) -> str:
        """
        Clones a git repository into a temporary workspace directory and returns the path.
        """
        import uuid

        clean_url = git_url.strip().rstrip("/")
        parts = clean_url.split("/")

        # Check if URL is an organization/user profile URL rather than a repo URL
        if len(parts) <= 4 and ("github.com" in clean_url or "gitlab.com" in clean_url):
            logger.warning(
                f"URL '{git_url}' appears to be an organization or user profile URL, not a specific repository URL."
            )
            raise ValueError(
                f"URL '{git_url}' is an organization/user URL. Please provide a full repository URL (e.g., https://github.com/Wholesome-Care/repo-name)"
            )

        repo_name = parts[-1].replace(".git", "")
        # Append a short UUID to guarantee directory uniqueness and prevent clone failures
        unique_id = uuid.uuid4().hex[:8]
        repo_path = os.path.join(self.workspace_dir, f"repo_{repo_name}_{unique_id}")

        # Clean up existing clone if any
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)

        logger.info(f"Cloning {clean_url} (branch: {branch}) into {repo_path}")
        clone_cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--no-tags",
            "--shallow-submodules"
        ]
        
        if branch:
            clone_cmd.extend(["--branch", branch, "--single-branch"])
            
        clone_cmd.extend([clean_url, repo_path])

        try:
            # Shallow clone to drastically reduce latency and I/O
            subprocess.run(
                clone_cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            return repo_path
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Git clone failed for {clean_url}: {e.stderr.strip() if e.stderr else e}"
            )
            raise RuntimeError(
                f"Failed to clone repository '{clean_url}': {e.stderr.strip() if e.stderr else 'Repository not found'}"
            )

    def get_remote_commit_hash(self, git_url: str, branch: str = "main") -> str:
        """
        Gets the latest commit hash from the remote repository without cloning it.
        """
        try:
            result = subprocess.run(
                ["git", "ls-remote", git_url, f"refs/heads/{branch}"],
                check=True,
                capture_output=True,
                text=True,
            )
            output = result.stdout.strip()
            if output:
                return output.split()[0]
            return ""
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get remote commit hash for {git_url}: {e}")
            return ""

    def get_latest_commit(self, repo_path: str) -> dict[str, str]:
        """
        Gets the latest commit hash, author, and message for the cloned repository.
        """
        if (
            not repo_path
            or not os.path.exists(repo_path)
            or not os.path.isdir(repo_path)
        ):
            logger.warning(
                f"Directory invalid or not found for git commit check: '{repo_path}'"
            )
            return {
                "commit_hash": "local_commit",
                "author": "local_user",
                "message": "Non-git or invalid directory",
            }

        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%an|%s"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            output = result.stdout.strip().split("|", 2)
            if len(output) == 3:
                return {
                    "commit_hash": output[0],
                    "author": output[1],
                    "message": output[2],
                }
            return {
                "commit_hash": "local_commit",
                "author": "local_user",
                "message": "No commit output",
            }
        except Exception as e:
            logger.warning(f"Failed to get commit info for '{repo_path}': {e}")
            return {
                "commit_hash": "local_commit",
                "author": "local_user",
                "message": f"Git log fallback: {e}",
            }


git_service = GitService()
