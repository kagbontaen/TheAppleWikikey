# TheAppleWiki API (Python)

A lightweight Python client for fetching iOS firmware keys from TheAppleWiki.

## Features

* Resolve build IDs from iOS versions
* Discover firmware update lines
* Fetch firmware keys
* Local caching (7-day TTL)
* CLI + Python API support

## Installation

```bash
git clone https://github.com/kagbontaen/TheAppleWikikey.git
cd TheAppleWikikey
pip install -r requirements.txt
```

## Usage (Python)

```python
from theapplewiki_api.client import AppleWikiClient

client = AppleWikiClient(debug=True)

keys = client.get_keys(
    device="iPhone10,6",
    version="16.0"
)

print(keys)
```

## Usage (CLI)

```bash
python cli.py -p iPhone10,6 -s 16.0
python cli.py -m n66ap -s 15.0.1  # Using device model
python cli.py -p iPhone9,3 -b 19H370  # Using build ID
python cli.py --bulk "iPhone9,3,15.0.1,19H370" "iPhone10,6,16.0" --debug
```

## Notes

* Data is sourced from TheAppleWiki (community-maintained)
* Uses api.ipsw.me for device/build resolution
* Includes request throttling to avoid abuse