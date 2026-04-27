import os
import json
import time

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)
TTL = 7 * 24 * 3600  # 7 days in seconds

def get_cached(key):
    """Get cached data if not expired"""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if time.time() - data.get('timestamp', 0) > TTL:
            os.remove(path)
            return None
        return data.get('value')
    except (json.JSONDecodeError, KeyError):
        return None

def set_cached(key, value):
    """Cache the data with timestamp"""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    data = {
        'timestamp': time.time(),
        'value': value
    }
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass  # Ignore cache write errors