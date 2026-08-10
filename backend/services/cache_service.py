import os
import json
import logging
import numpy as np
import redis

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        redis_host = os.environ.get("REDIS_HOST","127.0.0.1")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        redis_password = os.environ.get("REDIS_PASSWORD", None)
        self.redis_client = None

        if not redis_host:
            logger.info("REDIS_HOST not set in environment. Redis semantic cache disabled.")
            return

        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=0,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            logger.info(f"[Redis PING] Testing connection to {redis_host}:{redis_port} (db=0)")
            self.redis_client.ping()
            logger.info(f"[Redis PING] Connected successfully to Redis at {redis_host}:{redis_port} (db=0)")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Semantic caching will be disabled.")
            self.redis_client = None

    def _cosine_similarity(self, vec1, vec2):
        if not vec1 or not vec2:
            return 0.0
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
    def check_exact_cache(self, session_id: str, query_text: str) -> dict:
        """
        Sub-millisecond exact string match in Redis before calling OpenAI embedding service.
        """
        if not self.redis_client or not query_text:
            return None
        cache_key = "semantic_cache_global"
        try:
            cached_entries = self.redis_client.lrange(cache_key, 0, -1)
            q_clean = query_text.strip().lower()
            for entry_json in cached_entries:
                entry = json.loads(entry_json)
                if entry.get("query", "").strip().lower() == q_clean:
                    logger.info(f"[Redis FAST Cache HIT] Sub-1ms exact text match for session {session_id}")
                    return {
                        "response": entry.get("response", ""),
                        "metadata": entry.get("metadata", {})
                    }
            return None
        except Exception as e:
            logger.error(f"[Redis Exact Cache Error] {e}")
            return None

    def check_cache(self, session_id: str, query_text: str, query_embedding: list) -> dict:
        """
        Checks Redis for highly similar past queries in the same session.
        Returns the cached response dict if found, else None.
        """
        if not self.redis_client or not query_embedding:
            return None
            
        cache_key = "semantic_cache_global"
        
        try:
            # Get all past queries for this session
            logger.info(f"[Redis LRANGE] Reading list key '{cache_key}' (db=0)")
            cached_entries = self.redis_client.lrange(cache_key, 0, -1)
            logger.info(f"[Redis LRANGE] Retrieved {len(cached_entries)} entries for key '{cache_key}'")
            
            for entry_json in cached_entries:
                entry = json.loads(entry_json)
                cached_embedding = entry.get("embedding", [])
                
                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                
                # Using 0.95 as the threshold for semantic equivalence
                if similarity >= 0.95:
                    logger.info(f"[Redis Cache HIT] Similarity: {similarity:.4f} for session {session_id}")
                    return {
                        "response": entry.get("response", ""),
                        "metadata": entry.get("metadata", {})
                    }
                    
            logger.info(f"[Redis Cache MISS] No match above threshold for session {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"[Redis LRANGE ERROR] Error checking cache for key '{cache_key}': {e}")
            return None

    def get_cached_response(self, session_id: str, query_embedding: list, query_text: str = "", similarity_threshold: float = 0.95) -> dict:
        """
        Alias for check_cache for API compatibility.
        """
        return self.check_cache(session_id=session_id, query_text=query_text, query_embedding=query_embedding)
            
    def save_to_cache(self, session_id: str, query_text: str, query_embedding: list, response: str, metadata: dict):
        """
        Saves a query and its response to the session's Redis list.
        Sets a TTL to expire the cache eventually.
        """
        if not self.redis_client:
            return
            
        cache_key = "semantic_cache_global"
        
        entry = {
            "query": query_text,
            "embedding": query_embedding,
            "response": response,
            "metadata": metadata
        }
        
        try:
            logger.info(f"[Redis RPUSH] Writing entry to key '{cache_key}' (db=0)")
            self.redis_client.rpush(cache_key, json.dumps(entry))
            # Set TTL to 24 hours (86400 seconds) so memory doesn't bloat indefinitely
            logger.info(f"[Redis EXPIRE] Setting 86400s TTL on key '{cache_key}' (db=0)")
            self.redis_client.expire(cache_key, 86400) 
            logger.info(f"[Redis SAVE SUCCESS] Entry saved and TTL updated for key '{cache_key}'")
        except Exception as e:
            logger.error(f"[Redis SAVE ERROR] Error saving to key '{cache_key}': {e}")

cache_service = CacheService()
