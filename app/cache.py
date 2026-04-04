import os
import redis

cache = None

def init_cache():
    global cache
    cache = redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )
    return cache

def get_cache():
    global cache
    if cache is None:
        init_cache()
    return cache
