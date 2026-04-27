import time
import requests
from .cache import get_cached, set_cached
from .utils import get_build_id, get_device_name, parse_keys_from_page

class AppleWikiClient:
    def __init__(self, debug=False):
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TheAppleWiki-API/1.0'
        })
        self.last_request = 0
        self.throttle_delay = 1  # 1 second between requests

    def _throttle(self):
        """Throttle requests to avoid abuse"""
        now = time.time()
        elapsed = now - self.last_request
        if elapsed < self.throttle_delay:
            time.sleep(self.throttle_delay - elapsed)
        self.last_request = time.time()

    def get_keys(self, device, version):
        """Get firmware keys for device and version"""
        if self.debug:
            print(f"Getting keys for {device} {version}")

        # Get build ID
        build = get_build_id(device, version)
        if not build:
            if self.debug:
                print(f"Build ID not found for {device} {version}")
            return None

        if self.debug:
            print(f"Build ID: {build}")

        # Check cache
        cache_key = f"{device}_{version}_{build}"
        cached = get_cached(cache_key)
        if cached:
            if self.debug:
                print("Using cached data")
            return cached

        # Fetch from wiki
        keys = self._fetch_keys(device, build, version)
        if keys:
            set_cached(cache_key, keys)
            if self.debug:
                print("Keys fetched and cached")
        else:
            if self.debug:
                print("Keys not found")

        return keys

    def _fetch_keys(self, device, build, version):
        """Fetch keys from TheAppleWiki"""
        device_name = get_device_name(device)
        if not device_name:
            return None

        url = f"https://theapplewiki.com/wiki/{device_name}"
        if self.debug:
            print(f"Fetching from {url}")

        self._throttle()
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return parse_keys_from_page(response.text, version, build)
        except requests.RequestException as e:
            if self.debug:
                print(f"Request error: {e}")
            return None