import redis.asyncio as redis

from chatbot.config import REDIS_URL

redis_client = redis.Redis.from_url(
    REDIS_URL if REDIS_URL else "", decode_responses=True
)
