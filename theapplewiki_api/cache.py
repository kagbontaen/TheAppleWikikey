import os
import json
import time

CACHE_DIR = ".cache"
CACHE_TTL = 7 * 24 * 60 * 60  # 7 days
os.makedirs(CACHE_DIR, exist_ok=True)

def cache_path(device, build=None, version=None):
    if build and version:
        return os.path.join(CACHE_DIR, f"{device}_{build}_{version}.json")
    elif build:
        return os.path.join(CACHE_DIR, f"{device}_{build}.json")
    elif version:
        return os.path.join(CACHE_DIR, f"{device}_{version}.json")
    else:
        return os.path.join(CACHE_DIR, f"{device}_unknown.json")

def cache_valid(path):
    return os.path.exists(path) and (time.time() - os.path.getmtime(path)) < CACHE_TTL

def load_cache(device, build=None, version=None):
    # Exact match
    exact_path = cache_path(device, build, version)
    if cache_valid(exact_path):
        with open(exact_path, "r") as f:
            print(f"[+] Using cached data: {exact_path}")
            return json.load(f)
    # Fallback: search for any file containing build or version
    for fname in os.listdir(CACHE_DIR):
        if device in fname and ((build and build in fname) or (version and version in fname)):
            path = os.path.join(CACHE_DIR, fname)
            if cache_valid(path):
                print(f"[+] Using fallback cached data: {path}")
                with open(path, "r") as f:
                    return json.load(f)
    return None

def save_cache(data, device, build=None, version=None):
    path = cache_path(device, build, version)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"[+] Saved cache {path}")