import hashlib
import json
import logging
import os
from typing import Any

import redis

logger = logging.getLogger(__name__)


class RetrievalCache:
    """
    A caching layer for Vector/BM25 retrieval to prevent parallel agents
    from hitting the database with the exact same query multiple times.
    """

    def __init__(self):
        redis_host = os.environ.get("REDIS_HOST")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        redis_password = os.environ.get("REDIS_PASSWORD", None)
        self.redis_client = None
        self._local_cache = {}

        if not redis_host:
            logger.info(
                "REDIS_HOST not set in environment. Retrieval cache using local fallback dict."
            )
            return

        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=1,  # Use db=1 to separate from semantic cache
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            logger.info(
                f"[Redis PING] Testing connection to {redis_host}:{redis_port} (db=1)"
            )
            self.redis_client.ping()
            logger.info(
                f"[Redis PING] Connected successfully to Redis for retrieval cache at {redis_host}:{redis_port} (db=1)"
            )
        except Exception as e:
            logger.warning(
                f"Failed to connect to Redis for retrieval cache: {e}. Using local fallback dict."
            )
            self.redis_client = None

    def _generate_key(self, query: str, top_k: int) -> str:
        # Create a deterministic hash for the cache key
        payload = f"{query}:{top_k}"
        return "retrieval:" + hashlib.md5(payload.encode("utf-8")).hexdigest()

    def get(self, query: str, top_k: int) -> list[dict[str, Any]] | None:
        key = self._generate_key(query, top_k)
        if self.redis_client:
            try:
                logger.info(
                    f"[Redis GET] Fetching key '{key}' (db=1) for query: '{query}'"
                )
                data = self.redis_client.get(key)
                if data:
                    logger.info(f"[Redis Retrieval Cache HIT] Key '{key}' (db=1)")
                    return json.loads(data)
                else:
                    logger.info(f"[Redis Retrieval Cache MISS] Key '{key}' (db=1)")
            except Exception as e:
                logger.error(f"[Redis GET ERROR] Error reading key '{key}': {e}")
        else:
            if key in self._local_cache:
                logger.info(f"[Local Retrieval Cache HIT] Key '{key}'")
                return self._local_cache[key]

        return None

    def set(self, query: str, top_k: int, results: Any):
        key = self._generate_key(query, top_k)

        # Safely convert Pydantic objects or dicts into JSON-serializable list
        serializable_results = []
        if isinstance(results, list):
            for r in results:
                if hasattr(r, "model_dump"):
                    serializable_results.append(r.model_dump())
                elif hasattr(r, "dict"):
                    serializable_results.append(r.dict())
                elif isinstance(r, dict):
                    serializable_results.append(r)
                else:
                    serializable_results.append(str(r))
        else:
            serializable_results = str(results)

        if self.redis_client:
            try:
                # Cache for 10 minutes (600 seconds) - usually enough for a session graph execution
                logger.info(f"[Redis SETEX] Writing key '{key}' with 600s TTL (db=1)")
                self.redis_client.setex(key, 600, json.dumps(serializable_results))
                logger.info(
                    f"[Redis SETEX SUCCESS] Key '{key}' saved successfully (db=1)"
                )
            except Exception as e:
                logger.error(f"[Redis SETEX ERROR] Error writing key '{key}': {e}")
        else:
            self._local_cache[key] = serializable_results


retrieval_cache = RetrievalCache()
