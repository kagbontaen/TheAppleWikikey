import requests
from bs4 import BeautifulSoup
import json

def get_build_id(device, version):
    """Get build ID for device and version from api.ipsw.me"""
    url = f"https://api.ipsw.me/v4/device/{device}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        for firmware in data.get('firmwares', []):
            if firmware.get('version') == version:
                return firmware.get('buildid')
    except Exception as e:
        print(f"Error getting build ID: {e}")
    return None

def get_device_name(device):
    """Get device name for wiki URL"""
    url = f"https://api.ipsw.me/v4/device/{device}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        name = data.get('name', device)
        # Format for wiki: iPhone_X -> iPhone_X
        return name.replace(' ', '_').replace(',', '_')
    except Exception as e:
        print(f"Error getting device name: {e}")
    return device

def parse_keys_from_page(html, version, build):
    """Parse keys from TheAppleWiki page HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    # Find header containing the version
    header = soup.find(['h2', 'h3', 'h4'], string=lambda text: text and version in text.strip())
    if not header:
        return None
    # Find the next pre with class 'keys'
    pre = header.find_next('pre', class_='keys')
    if not pre:
        return None
    try:
        return json.loads(pre.text.strip())
    except json.JSONDecodeError:
        return None