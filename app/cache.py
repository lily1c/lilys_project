import os
import redis

cache = None

def init_cache():
    global cache
    try:
        cache = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
            socket_timeout=1
        )
        # Try to ping, if fails, set cache back to None
        cache.ping()
    except Exception:
        cache = None
    return cache

def get_cache():
    global cache
    if cache is None:
        init_cache()
    return cache
