import functools
import inspect
from datetime import datetime, timedelta
from typing import Optional, Any


class TTLCache:
    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: dict = {}
        self._timestamps: dict = {}
        self.default_ttl = timedelta(seconds=default_ttl_seconds)

    def _is_expired(self, key: str) -> bool:
        if key not in self._timestamps:
            return True
        return datetime.now() - self._timestamps[key] > self.default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache and not self._is_expired(key):
            return self._cache[key]
        self.delete(key)
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
        if ttl:
            self._timestamps[key] = datetime.now() - timedelta(seconds=self.default_ttl.total_seconds() - ttl)

    def delete(self, key: str):
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self):
        self._cache.clear()
        self._timestamps.clear()


def ttl_cache(cache):
    def decorator(func):
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            bound.arguments.pop("self", None)
            key_parts = []
            for name, value in bound.arguments.items():
                if isinstance(value, list):
                    value = tuple(sorted(str(v) for v in value))
                    key_parts.append((name, value))

            key = (func.__module__, func.__qualname__, tuple(key_parts))
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        return wrapper

    return decorator
