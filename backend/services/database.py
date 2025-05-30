import redis
from typing import Dict

class RedisDatabase:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)

    def save_hash(self, score_name: str, score_hash: str) -> None:
        """Save a score hash to Redis."""
        self.redis_client.hset('score_hashes', score_name, score_hash)

    def get_hash(self, score_name: str) -> str:
        """Get a score hash from Redis."""
        return self.redis_client.hget('score_hashes', score_name)

    def get_all_hashes(self) -> Dict[str, str]:
        """Get all score hashes from Redis."""
        hashes = self.redis_client.hgetall('score_hashes')
        return {k.decode('utf-8'): v.decode('utf-8') for k, v in hashes.items()} 