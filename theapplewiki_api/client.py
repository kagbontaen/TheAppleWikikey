import time
from .utils import load_cache, save_cache, buildid, discover_update_line, fetch_keys, POLITE_DELAY

class AppleWikiClient:
    def __init__(self, debug=False):
        self.debug = debug

    def get_keys(self, device, version=None, build=None):
        """Get firmware keys for device and version/build"""
        if self.debug:
            print(f"Getting keys for {device} {version or ''} {build or ''}".strip())

        # Check cache first
        cached = load_cache(device, build, version)
        if cached:
            return cached

        # Resolve build if needed
        if version and not build:
            build = buildid(device, version, verbose=self.debug)

        if not build:
            if self.debug:
                print(f"Could not determine build for {device} {version}")
            return None

        # Discover update line
        update_line, discovered_build = discover_update_line(device, version, build, verbose=self.debug)
        if not update_line:
            if self.debug:
                print(f"Failed to discover update line for {device}")
            return None

        final_build = build if build else discovered_build
        if not final_build:
            if self.debug:
                print(f"Could not determine final build for {device}")
            return None

        if self.debug:
            print(f"Waiting {POLITE_DELAY}s before fetching keys...")
        time.sleep(POLITE_DELAY)

        # Fetch keys
        keys = fetch_keys(device, final_build, update_line, verbose=self.debug)
        if not keys:
            if self.debug:
                print(f"Failed to fetch keys for {device} {final_build}")
            return None

        # Save cache
        save_cache(keys, device, final_build, version)

        return keys