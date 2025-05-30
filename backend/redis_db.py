import redis
from typing import Optional, Dict
from urllib.parse import urlparse

class RedisDatabase:
    def __init__(self, url: Optional[str] = None):
        """Initialize Redis connection
        Args:
            url: Redis URL string. If None, connects to localhost
        """
        if url:
            self.redis_client = redis.from_url(
                url,
                decode_responses=True  # This ensures strings are returned instead of bytes
            )
        else:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
        self._init_defaults()

    def _init_defaults(self):
        """Initialize default values if database is empty"""
        if not self.redis_client.exists('score_hashes'):
            defaults = {
                "test_score.mxl": "LTPXc",
                "sonata01-1.mxl": "NfdXc",
            }
            self.redis_client.hset('score_hashes', mapping=defaults)

    def get_hash(self, score_name: str) -> Optional[str]:
        """Get a single hash by score name"""
        return self.redis_client.hget('score_hashes', score_name)

    def save_hash(self, score_name: str, score_hash: str):
        """Save a single hash"""
        self.redis_client.hset('score_hashes', score_name, score_hash)

    def get_all_hashes(self) -> Dict[str, str]:
        """Get all score hashes"""
        return self.redis_client.hgetall('score_hashes')

    def delete_hash(self, score_name: str):
        """Delete a hash by score name"""
        self.redis_client.hdel('score_hashes', score_name) 