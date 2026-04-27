#!/usr/bin/env python3
import argparse
import json
import sys
from theapplewiki_api import AppleWikiClient
from theapplewiki_api.utils import map_model_to_product, fetch_firmware_keys

def main():
    parser = argparse.ArgumentParser(description="Fetch iOS firmware keys from TheAppleWiki")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--product", help="Device identifier, e.g., iPhone9,3")
    group.add_argument("-m", "--model", help="Device model, e.g., n66ap (will be converted to product identifier)")
    parser.add_argument("-s", "--ios", help="iOS version, e.g., 15.0.1")
    parser.add_argument("-b", "--build", help="Firmware build, e.g., 19H370")
    parser.add_argument("--bulk", nargs="+", help="Bulk fetch: space-separated list of product,version,build triples, e.g., 'iPhone9,3,15.0.1,19H370'")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Resolve product from model if needed
    product = args.product
    if args.model:
        print(f"[*] Mapping model {args.model} to product identifier...")
        product = map_model_to_product(args.model)
        if not product:
            print(f"[-] Could not map model {args.model} to a product identifier")
            return
        print(f"[+] Mapped to product: {product}")

    if args.bulk:
        for entry in args.bulk:
            parts = entry.split(",")
            prod = parts[0]
            version = parts[1] if len(parts) > 1 and parts[1] else None
            build = parts[2] if len(parts) > 2 and parts[2] else None
            if not version and not build:
                print(f"[-] Entry '{entry}' must include at least version or build")
                continue
            fetch_firmware_keys(prod, version, build, debug=args.debug)
    else:
        if not args.ios and not args.build:
            parser.error("You must provide at least one of --ios (-s) or --build (-b)")
        client = AppleWikiClient(debug=args.debug)
        keys = client.get_keys(product, args.ios, args.build)
        if keys:
            print(json.dumps(keys, indent=2))
        else:
            print("No keys found", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()