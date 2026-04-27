import requests
import urllib.request
import urllib.parse
import json
import time
from .cache import load_cache, save_cache

# Configuration
USER_AGENT = "kinc-firmwareKeysFetcher/1.1"
BASE = "https://theapplewiki.com/wiki/Special:Ask"
POLITE_DELAY = 2  # seconds

def smw_pretty_encode(text):
    standard_encoded = urllib.parse.quote(text, safe='')
    return standard_encoded.replace('%', '-')

def smw_path_escape(text):
    return text.replace("[", "-5B").replace("]", "-5D").replace(" ", "-20").replace(":", "-3A").replace(",", "%2C")

def map_model_to_product(model):
    """Map a device model (e.g., n66ap) to a product identifier (e.g., iPhone8,1) using api.ipsw.me"""
    try:
        resp = requests.get('https://api.ipsw.me/v4/devices')
        resp.raise_for_status()
        devices = resp.json()
        for dev in devices:
            # Search recursively in the device dict for the model
            def search_obj(o):
                if isinstance(o, str):
                    return model.lower() == o.lower() or model.lower() in o.lower()
                if isinstance(o, dict):
                    return any(search_obj(v) for v in o.values())
                if isinstance(o, list):
                    return any(search_obj(v) for v in o)
                return False

            if search_obj(dev):
                product = dev.get('identifier') or dev.get('product') or dev.get('name')
                if product:
                    return product
        return None
    except requests.exceptions.RequestException as e:
        print(f"[-] Failed to query api.ipsw.me for devices: {e}")
        return None

def buildid(device, version=None, verbose=False):
    """Resolve a firmware build identifier for a device and version using api.ipsw.me."""
    if not device or not version:
        return None

    url = f"https://api.ipsw.me/v4/device/{device}?type=ipsw"
    if verbose:
        print(f"[DEBUG] buildid query URL: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        firmwares = data.get('firmwares', [])
        candidate = next((f for f in firmwares if f.get('version') == version), None)
        if not candidate:
            candidate = next((f for f in firmwares if f.get('version', '').startswith(version)), None)
        if candidate:
            build_id = candidate.get('buildid')
            if verbose:
                print(f"[DEBUG] Resolved buildid {build_id} for {device} {version}")
            return build_id
    except requests.exceptions.RequestException as e:
        print(f"[-] buildid request failed: {e}")
    return None

def discover_update_line(device, version=None, build=None, verbose=False):
    """Discover the update line (firmware version identifier) for a device/build combination.

    Uses TheAppleWiki semantic query syntax to find the matching Keys entry.
    Returns (update_line, discovered_build) tuple.
    """
    if not device:
        return None, None

    if version and not build:
        build = buildid(device, version, verbose=verbose)

    parts = ["[[:Keys:+]]"]
    parts.append(f"[[Has firmware device::{device}]]")
    if build:
        parts.append(f"[[Has firmware build::{build}]]")

    parts.append("?Has firmware build=build")
    parts.append("?Has firmware codename=codename")
    parts.append("?Has firmware version=version")
    parts.append("?Has firmware device=device")
    parts.append("limit=10")
    parts.append("offset=0")
    parts.append("format=json")

    pretty_path = "/".join([smw_pretty_encode(p) for p in parts])

    if verbose:
        print(f"[DEBUG] SMW Query parts: {parts}")
        print(f"[DEBUG] Pretty path: {pretty_path}")

    url = f"{BASE}/{pretty_path}"
    if verbose:
        print(f"[DEBUG] Request URL: {url}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            if verbose:
                print(f"[DEBUG] Response status: {r.status}")
                print(f"[DEBUG] Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    except Exception as e:
        print(f"[-] Discovery request failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return None, None

    results = {}
    if isinstance(data, dict):
        if "query" in data and isinstance(data["query"], dict):
            results = data["query"].get("results", {})
        elif "results" in data:
            results = data["results"]
        else:
            results = data  # direct results dict

    if verbose:
        print(f"[DEBUG] Found {len(results)} results")
        if results:
            print(f"[DEBUG] Result keys: {list(results.keys())[:5]}")

    if not results:
        print(f"[!] No firmware keys found for {device}" + (f" version {version}" if version else "") + (f" build {build}" if build else ""))
        return None, None

    for page_title, entry in results.items():
        if not page_title.startswith("Keys:"):
            continue

        name = page_title[len("Keys:"):].strip()
        parts = name.split()
        if len(parts) < 1:
            continue

        update_line = parts[0]
        discovered_build = parts[1] if len(parts) > 1 else None

        if not discovered_build and version:
            discovered_build = buildid(device, version, verbose=verbose)
            if verbose and discovered_build:
                print(f"[DEBUG] buildid() returned {discovered_build}")

        if verbose:
            print(f"[+] Discovered: update_line={update_line}, build={discovered_build}, page={page_title}")
        return update_line, discovered_build

    if version:
        fallback_build = buildid(device, version, verbose=verbose)
        if fallback_build:
            if verbose:
                print(f"[DEBUG] Fallback buildid() returned {fallback_build}")
            return None, fallback_build

    print(f"[!] No Keys entries matched the criteria")
    return None, None

def fetch_keys(device, build, update, verbose=False):
    subobject = f"Keys:{update} {build} ({device})"
    parts = [
        f"[[-2DHas subobject::{subobject}]]",
        "?Has filename=filename",
        "?Has firmware device=device",
        "?Has key=key",
        "?Key DevKBAG=devkbag",
        "?Has key IV=iv",
        "?Key KBAG=kbag",
        "mainlabel=filename",
        "limit=100",
        "offset=0",
        "format=json",
        "searchlabel=Keys",
        "type=simple"
    ]
    pretty_path = "/".join([smw_pretty_encode(p) for p in parts])
    url = BASE + "/" + pretty_path
    if verbose:
        print(f"[DEBUG] Fetch keys URL: {url}")

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except Exception as e:
        print(f"[-] Fetch keys request failed: {e}")
        return None

    return data if isinstance(data, dict) and data else None

def fetch_firmware_keys(device, version=None, build=None, debug=False):
    cached = load_cache(device, build, version)
    if cached:
        keys = cached
        final_build = build
    else:
        if not buildid:
            build = buildid(device, version, verbose=debug)
        update_line, discovered_build = discover_update_line(device, version, build, verbose=debug)
        if not update_line:
            print(f"[-] Failed to discover update line for {device}")
            return None

        final_build = build if build else discovered_build
        if not final_build:
            print(f"[-] Could not determine firmware build for {device}")
            return None

        if debug:
            print(f"[DEBUG] Waiting {POLITE_DELAY}s before fetching keys...")
        time.sleep(POLITE_DELAY)

        keys = fetch_keys(device, final_build, update_line, verbose=debug)
        if not keys:
            print(f"[-] Failed to fetch keys for {device} {final_build}")
            return None

        save_cache(keys, device, final_build, version)

    output_file = f"{device}_{final_build if final_build else version}.json"
    with open(output_file, "w") as f:
        json.dump(keys, f, separators=(",", ":"))
    print(f"[+] Keys saved to {output_file}")
    return keys

def map_model_to_product(model):
    """Map a device model (e.g., n66ap) to a product identifier (e.g., iPhone8,1) using api.ipsw.me"""
    try:
        resp = requests.get('https://api.ipsw.me/v4/devices')
        resp.raise_for_status()
        devices = resp.json()
        for dev in devices:
            # Search recursively in the device dict for the model
            def search_obj(o):
                if isinstance(o, str):
                    return model.lower() == o.lower() or model.lower() in o.lower()
                if isinstance(o, dict):
                    return any(search_obj(v) for v in o.values())
                if isinstance(o, list):
                    return any(search_obj(v) for v in o)
                return False

            if search_obj(dev):
                product = dev.get('identifier') or dev.get('product') or dev.get('name')
                if product:
                    return product
        return None
    except requests.exceptions.RequestException as e:
        print(f"[-] Failed to query api.ipsw.me for devices: {e}")
        return None

def buildid(device, version=None, verbose=False):
    """Resolve a firmware build identifier for a device and version using api.ipsw.me."""
    if not device or not version:
        return None

    url = f"https://api.ipsw.me/v4/device/{device}?type=ipsw"
    if verbose:
        print(f"[DEBUG] buildid query URL: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        firmwares = data.get('firmwares', [])
        candidate = next((f for f in firmwares if f.get('version') == version), None)
        if not candidate:
            candidate = next((f for f in firmwares if f.get('version', '').startswith(version)), None)
        if candidate:
            build_id = candidate.get('buildid')
            if verbose:
                print(f"[DEBUG] Resolved buildid {build_id} for {device} {version}")
            return build_id
    except requests.exceptions.RequestException as e:
        print(f"[-] buildid request failed: {e}")
    return None

def discover_update_line(device, version=None, build=None, verbose=False):
    """Discover the update line (firmware version identifier) for a device/build combination.

    Uses TheAppleWiki semantic query syntax to find the matching Keys entry.
    Returns (update_line, discovered_build) tuple.
    """
    if not device:
        return None, None

    if version and not build:
        build = buildid(device, version, verbose=verbose)

    parts = ["[[:Keys:+]]"]
    parts.append(f"[[Has firmware device::{device}]]")
    if build:
        parts.append(f"[[Has firmware build::{build}]]")

    parts.append("?Has firmware build=build")
    parts.append("?Has firmware codename=codename")
    parts.append("?Has firmware version=version")
    parts.append("?Has firmware device=device")
    parts.append("limit=10")
    parts.append("offset=0")
    parts.append("format=json")

    pretty_path = "/".join([smw_pretty_encode(p) for p in parts])

    if verbose:
        print(f"[DEBUG] SMW Query parts: {parts}")
        print(f"[DEBUG] Pretty path: {pretty_path}")

    url = f"{BASE}/{pretty_path}"
    if verbose:
        print(f"[DEBUG] Request URL: {url}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            if verbose:
                print(f"[DEBUG] Response status: {r.status}")
                print(f"[DEBUG] Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    except Exception as e:
        print(f"[-] Discovery request failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return None, None

    results = {}
    if isinstance(data, dict):
        if "query" in data and isinstance(data["query"], dict):
            results = data["query"].get("results", {})
        elif "results" in data:
            results = data["results"]
        else:
            results = data  # direct results dict

    if verbose:
        print(f"[DEBUG] Found {len(results)} results")
        if results:
            print(f"[DEBUG] Result keys: {list(results.keys())[:5]}")

    if not results:
        print(f"[!] No firmware keys found for {device}" + (f" version {version}" if version else "") + (f" build {build}" if build else ""))
        return None, None

    for page_title, entry in results.items():
        if not page_title.startswith("Keys:"):
            continue

        name = page_title[len("Keys:"):].strip()
        parts = name.split()
        if len(parts) < 1:
            continue

        update_line = parts[0]
        discovered_build = parts[1] if len(parts) > 1 else None

        if not discovered_build and version:
            discovered_build = buildid(device, version, verbose=verbose)
            if verbose and discovered_build:
                print(f"[DEBUG] buildid() returned {discovered_build}")

        if verbose:
            print(f"[+] Discovered: update_line={update_line}, build={discovered_build}, page={page_title}")
        return update_line, discovered_build

    if version:
        fallback_build = buildid(device, version, verbose=verbose)
        if fallback_build:
            if verbose:
                print(f"[DEBUG] Fallback buildid() returned {fallback_build}")
            return None, fallback_build

    print(f"[!] No Keys entries matched the criteria")
    return None, None

def fetch_keys(device, build, update, verbose=False):
    subobject = f"Keys:{update} {build} ({device})"
    parts = [
        f"[[-2DHas subobject::{subobject}]]",
        "?Has filename=filename",
        "?Has firmware device=device",
        "?Has key=key",
        "?Key DevKBAG=devkbag",
        "?Has key IV=iv",
        "?Key KBAG=kbag",
        "mainlabel=filename",
        "limit=100",
        "offset=0",
        "format=json",
        "searchlabel=Keys",
        "type=simple"
    ]
    pretty_path = "/".join([smw_pretty_encode(p) for p in parts])
    url = BASE + "/" + pretty_path
    if verbose:
        print(f"[DEBUG] Fetch keys URL: {url}")

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except Exception as e:
        print(f"[-] Fetch keys request failed: {e}")
        return None

    return data if isinstance(data, dict) and data else None