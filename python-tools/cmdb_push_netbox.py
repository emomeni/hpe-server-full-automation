#!/usr/bin/env python3
import os
import sys
import json
import requests

NETBOX_URL = os.getenv("NETBOX_URL", "https://netbox.example.com")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN", "NB_TOKEN_PLACEHOLDER")
NETBOX_SITE = os.getenv("NETBOX_SITE", "dc1")

HEADERS = {
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def create_or_update_device(dev):
    url = f"{NETBOX_URL}/api/dcim/devices/"
    params = {"serial": dev["serial"]}
    r = requests.get(url, headers=HEADERS, params=params, verify=False)
    r.raise_for_status()
    results = r.json().get("results", [])

    payload = {
        "name": dev["host"],
        "device_type": dev["model"],
        "serial": dev["serial"],
        "site": NETBOX_SITE,
        "status": "active",
    }

    if results:
        device_id = results[0]["id"]
        r = requests.patch(f"{url}{device_id}/", headers=HEADERS, json=payload, verify=False)
    else:
        r = requests.post(url, headers=HEADERS, json=payload, verify=False)

    r.raise_for_status()
    return r.json()


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} inventory.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    for dev in data:
        if dev.get("error"):
            print(f"[WARN] Skipping {dev['host']} - error: {dev['error']}")
            continue
        resp = create_or_update_device(dev)
        print(f"[OK] Synced {dev['host']} -> NetBox ID {resp.get('id')}")


if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    main()
