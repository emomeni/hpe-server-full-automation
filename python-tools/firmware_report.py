#!/usr/bin/env python3
"""Simple example that reads compliance output and aggregates a report.

Intended to be fed with JSON from Ansible or redfish_inventory.py.
"""
import json
import sys
from collections import Counter


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} audit.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    bios_versions = Counter(d.get("bios") for d in data if d.get("bios"))

    print("Firmware summary:")
    for version, count in bios_versions.items():
        print(f"  BIOS {version}: {count} server(s)")


if __name__ == "__main__":
    main()
