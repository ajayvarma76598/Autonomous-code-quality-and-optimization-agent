from typing import Any


class RepositoryCache:
    _cache: dict[str, Any] = {}

    @classmethod
    def get(cls, repository_url: str, commit_hash: str) -> Any | None:
        key = f"{repository_url}@{commit_hash}"
        return cls._cache.get(key)

    @classmethod
    def set(cls, repository_url: str, commit_hash: str, context: Any) -> None:
        key = f"{repository_url}@{commit_hash}"
        cls._cache[key] = context
