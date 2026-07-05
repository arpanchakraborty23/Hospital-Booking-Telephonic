import os
import json
import logging
from typing import Optional
import redis as redis_lib
from dotenv import load_dotenv

load_dotenv()

class RedisClient:
    """Redis client wrapper for session storage."""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis_lib.Redis] = None
        self._initialized = False
        self.logger = logging.getLogger(__name__)

    def connect(self) -> redis_lib.Redis:  # Lazy connection with ping health check
        if not self._initialized:
            try:
                self.client = redis_lib.from_url(self.redis_url, decode_responses=True)
                self.client.ping()
                self._initialized = True
                self.logger.info("Connected to Redis at %s", self.redis_url)
            except Exception as e:
                self.logger.error("Failed to connect to Redis: %s", e)
                raise
        return self.client

    def set_json(self, key: str, data: dict, ttl: Optional[int] = None) -> None:  # Serialize dict to JSON and store with optional TTL
        self.connect()
        self.client.set(key, json.dumps(data))
        if ttl is not None:
            self.client.expire(key, ttl)

    def get_json(self, key: str) -> Optional[dict]:  # Deserialize JSON value from Redis
        self.connect()
        data = self.client.get(key)
        if data is not None:
            return json.loads(data)
        return None

    def append_to_array(self, key: str, array_field: str, item: dict, ttl: Optional[int] = None) -> None:  # Read-modify-write: appends to a JSON array field
        data = self.get_json(key)
        if data is None:
            data = {}
        if array_field not in data:
            data[array_field] = []
        data[array_field].append(item)
        self.set_json(key, data, ttl)

    def delete(self, key: str) -> None:  # Remove key from Redis
        self.connect()
        self.client.delete(key)

    def disconnect(self) -> None:  # Close connection, reset state
        if self.client is not None:
            self.client.close()
            self._initialized = False
            self.client = None
            self.logger.info("Disconnected from Redis")
