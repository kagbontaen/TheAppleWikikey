#!/usr/bin/env python3
import argparse
import json
import sys
from theapplewiki_api import AppleWikiClient

def main():
    parser = argparse.ArgumentParser(
        description='Fetch iOS firmware keys from TheAppleWiki',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py -p iPhone10,6 -s 16.0
  python cli.py --device iPhone12,1 --version 15.4 --debug
        """
    )
    parser.add_argument(
        '-p', '--device',
        required=True,
        help='Device identifier (e.g., iPhone10,6)'
    )
    parser.add_argument(
        '-s', '--version',
        required=True,
        help='iOS version (e.g., 16.0)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )

    args = parser.parse_args()

    client = AppleWikiClient(debug=args.debug)

    try:
        keys = client.get_keys(args.device, args.version)
        if keys:
            print(json.dumps(keys, indent=2))
        else:
            print("No keys found for the specified device and version.", file=sys.stderr)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()