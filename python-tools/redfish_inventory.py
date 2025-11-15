#!/usr/bin/env python3
import requests
import json
import sys

ILO_USER = "automation"
ILO_PASS = "SuperSecretPassword123!"
REDFISH_ROOT = "/redfish/v1"


def get_session(host):
    url = f"https://{host}{REDFISH_ROOT}/SessionService/Sessions"
    payload = {"UserName": ILO_USER, "Password": ILO_PASS}
    r = requests.post(url, json=payload, verify=False)
    r.raise_for_status()
    token = r.headers.get("X-Auth-Token")
    return token


def get_system_inventory(host, token):
    url = f"https://{host}{REDFISH_ROOT}/Systems/1"
    r = requests.get(url, headers={"X-Auth-Token": token}, verify=False)
    r.raise_for_status()
    return r.json()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} ilo-host [ilo-host2 ...]", file=sys.stderr)
        sys.exit(1)

    inventory = []
    for host in sys.argv[1:]:
        try:
            token = get_session(host)
            system = get_system_inventory(host, token)
            inventory.append(
                {
                    "host": host,
                    "model": system.get("Model"),
                    "serial": system.get("SerialNumber"),
                    "bios": system.get("BiosVersion"),
                    "manufacturer": system.get("Manufacturer"),
                }
            )
        except Exception as exc:
            inventory.append({"host": host, "error": str(exc)})

    print(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    main()
