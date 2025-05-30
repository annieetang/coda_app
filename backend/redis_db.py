import redis
from typing import Optional, Dict

class RedisDatabase:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True  # This ensures strings are returned instead of bytes
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