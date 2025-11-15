#!/usr/bin/env python3
"""Collect basic inventory information from one or more iLO endpoints."""

import json
import os
import sys
from typing import Any, Dict, Tuple

import requests
from requests import Session
from requests.exceptions import RequestException

REDFISH_ROOT = os.getenv("REDFISH_ROOT", "/redfish/v1")
REQUEST_TIMEOUT = int(os.getenv("REDFISH_TIMEOUT", "30"))


def env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def get_verify_setting():
    ca_bundle = os.getenv("REDFISH_CA_BUNDLE")
    if ca_bundle:
        return ca_bundle
    return env_bool("REDFISH_VERIFY_TLS", True)


VERIFY = get_verify_setting()


def get_credentials() -> Tuple[str, str]:
    username = os.getenv("ILO_USERNAME") or os.getenv("ILO_USER")
    password = os.getenv("ILO_PASSWORD") or os.getenv("ILO_PASS")
    if not username or not password:
        raise RuntimeError(
            "Set ILO_USERNAME and ILO_PASSWORD environment variables (or provide them via "
            "a wrapper script) before running redfish_inventory.py."
        )
    return username, password


def create_session(session: Session, host: str, username: str, password: str) -> Tuple[str, str]:
    url = f"https://{host}{REDFISH_ROOT}/SessionService/Sessions"
    payload = {"UserName": username, "Password": password}
    response = session.post(url, json=payload, verify=VERIFY, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    token = response.headers.get("X-Auth-Token") or response.headers.get("x-auth-token")
    if not token:
        raise RuntimeError("Redfish session created successfully but no X-Auth-Token was returned.")
    location = response.headers.get("Location") or response.headers.get("location")
    if not location:
        # Some iLO versions omit Location but include the session URI in the body.
        try:
            location = response.json().get("@odata.id", "")
        except ValueError:
            location = ""
    return token, location


def get_system_inventory(session: Session, host: str, token: str) -> Dict[str, Any]:
    url = f"https://{host}{REDFISH_ROOT}/Systems/1"
    response = session.get(
        url,
        headers={"X-Auth-Token": token},
        verify=VERIFY,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def delete_session(session: Session, host: str, token: str, location: str) -> None:
    if not location:
        return
    if location.startswith("http"):
        url = location
    else:
        url = f"https://{host}{location}"
    try:
        session.delete(
            url,
            headers={"X-Auth-Token": token},
            verify=VERIFY,
            timeout=REQUEST_TIMEOUT,
        )
    except RequestException:
        # Session expiry failures are non-fatal; best-effort cleanup only.
        pass


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} ilo-host [ilo-host2 ...]", file=sys.stderr)
        sys.exit(1)

    username, password = get_credentials()
    inventory = []

    with requests.Session() as session:
        session.headers.update({"Accept": "application/json"})
        for host in sys.argv[1:]:
            token = ""
            location = ""
            try:
                token, location = create_session(session, host, username, password)
                system = get_system_inventory(session, host, token)
                inventory.append(
                    {
                        "host": host,
                        "model": system.get("Model"),
                        "serial": system.get("SerialNumber"),
                        "bios": system.get("BiosVersion"),
                        "manufacturer": system.get("Manufacturer"),
                    }
                )
            except (RequestException, RuntimeError) as exc:
                inventory.append({"host": host, "error": str(exc)})
            finally:
                if token:
                    delete_session(session, host, token, location)

    print(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    main()
