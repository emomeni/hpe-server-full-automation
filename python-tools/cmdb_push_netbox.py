#!/usr/bin/env python3
"""Synchronise inventory records into NetBox."""

import json
import os
import sys
from typing import Any, Dict, Optional

import requests
from requests import Session
from requests.exceptions import RequestException

NETBOX_URL = os.getenv("NETBOX_URL", "https://netbox.example.com").rstrip("/")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN")
NETBOX_SITE = os.getenv("NETBOX_SITE", "dc1")
NETBOX_TIMEOUT = int(os.getenv("NETBOX_TIMEOUT", "30"))


def env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def get_verify_setting():
    ca_bundle = os.getenv("NETBOX_CA_BUNDLE")
    if ca_bundle:
        return ca_bundle
    return env_bool("NETBOX_VERIFY_TLS", True)


VERIFY = get_verify_setting()


def build_session() -> Session:
    if not NETBOX_TOKEN:
        raise RuntimeError("Set the NETBOX_TOKEN environment variable before running cmdb_push_netbox.py.")

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Token {NETBOX_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    return session


def resolve_site_id(session: Session) -> int:
    url = f"{NETBOX_URL}/api/dcim/sites/"
    for lookup_field in ("slug", "name"):
        response = session.get(
            url,
            params={lookup_field: NETBOX_SITE},
            verify=VERIFY,
            timeout=NETBOX_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return results[0]["id"]
    raise RuntimeError(f"Unable to resolve NetBox site '{NETBOX_SITE}'.")


def resolve_device_type_id(session: Session, model: str) -> Optional[int]:
    url = f"{NETBOX_URL}/api/dcim/device-types/"
    response = session.get(
        url,
        params={"model": model},
        verify=VERIFY,
        timeout=NETBOX_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if results:
        return results[0]["id"]
    return None


def create_or_update_device(session: Session, site_id: int, dev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not dev.get("serial"):
        raise RuntimeError(f"Device {dev.get('host')} is missing a serial number; skipping sync.")

    model = dev.get("model")
    if not model:
        raise RuntimeError(f"Device {dev.get('host', dev.get('serial'))} is missing a model identifier; skipping sync.")

    device_type_id = resolve_device_type_id(session, model)
    if device_type_id is None:
        print(
            f"[WARN] Skipping {dev.get('host', dev.get('serial'))}: NetBox device type for model '{model}' was not found.",
            file=sys.stderr,
        )
        return None
    url = f"{NETBOX_URL}/api/dcim/devices/"
    response = session.get(
        url,
        params={"serial": dev["serial"]},
        verify=VERIFY,
        timeout=NETBOX_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    payload = {
        "name": dev.get("host") or dev["serial"],
        "device_type": device_type_id,
        "serial": dev["serial"],
        "site": site_id,
        "status": "active",
    }

    if results:
        device_id = results[0]["id"]
        response = session.patch(
            f"{url}{device_id}/",
            json=payload,
            verify=VERIFY,
            timeout=NETBOX_TIMEOUT,
        )
    else:
        response = session.post(
            url,
            json=payload,
            verify=VERIFY,
            timeout=NETBOX_TIMEOUT,
        )

    response.raise_for_status()
    return response.json()


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} inventory.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as handle:
        data = json.load(handle)

    try:
        with build_session() as session:
            site_id = resolve_site_id(session)
            for dev in data:
                if dev.get("error"):
                    print(f"[WARN] Skipping {dev['host']} - error: {dev['error']}")
                    continue
                try:
                    response = create_or_update_device(session, site_id, dev)
                except RuntimeError as exc:
                    print(f"[WARN] Skipping {dev.get('host', dev.get('serial'))}: {exc}")
                    continue
                if not response:
                    continue
                print(f"[OK] Synced {dev['host']} -> NetBox ID {response.get('id')}")
    except (RequestException, RuntimeError) as exc:
        print(f"[ERROR] NetBox synchronisation failed: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
