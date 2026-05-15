#!/usr/bin/env python3
"""Robomow3 cloud API probe — login, list devices, fetch dashboard.

Usage:
    python3 probe_robomow.py --email YOU@EXAMPLE.COM --password SECRET
    python3 probe_robomow.py          # reads from .env (EMAIL / PASSWORD)

Reverse-engineered from Robomow 3.0 APK v3.5.6.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import aiohttp
import asyncio

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
log = logging.getLogger("probe_robomow")

AUTH_SUBDOMAIN = "myrobomow"
API_BRAND = "robomow"

AUTH_BASE_URL = f"https://{AUTH_SUBDOMAIN}.robomow.com/api"
AUTH_ENDPOINT = f"{AUTH_BASE_URL}/v2/mobile/authenticate"

IOT_BASE_URL = "https://lvxp2hg7h7.execute-api.eu-central-1.amazonaws.com/Prod"

CUSTOMER_DEVICES = f"{IOT_BASE_URL}/api/V6/{API_BRAND}/customer/get-devices"
CUSTOMER_DETAILS = f"{IOT_BASE_URL}/api/V6/{API_BRAND}/customer/details"

def device_url(device_id: str, action: str) -> str:
    return f"{IOT_BASE_URL}/api/V6/{API_BRAND}/device/{device_id}/{action}"


async def authenticate(session, email, password):
    payload = {"email": email, "password": password}
    headers = {"Content-Type": "application/json"}
    async with session.post(AUTH_ENDPOINT, json=payload, headers=headers) as resp:
        text = await resp.text()
        log.debug("AUTH response %d: %s", resp.status, text[:2000])
        resp.raise_for_status()
        return json.loads(text)


def _auth_headers(auth_token):
    return {"Authorization": auth_token, "Content-Type": "application/json"}


async def api_get(session, url, auth_token):
    headers = _auth_headers(auth_token)
    log.info("GET %s", url)
    async with session.get(url, headers=headers) as resp:
        text = await resp.text()
        log.debug("Response %d: %s", resp.status, text[:3000])
        resp.raise_for_status()
        return json.loads(text)


async def api_post(session, url, auth_token, payload=None):
    headers = _auth_headers(auth_token)
    log.info("POST %s", url)
    async with session.post(url, json=payload or {}, headers=headers) as resp:
        text = await resp.text()
        log.debug("Response %d: %s", resp.status, text[:3000])
        resp.raise_for_status()
        return json.loads(text)


async def main(email, password, device_id=None):
    async with aiohttp.ClientSession() as session:
        auth = await authenticate(session, email, password)
        print("\n===== AUTH RESPONSE =====")
        print(json.dumps(auth, indent=2, default=str))

        auth_token = auth.get("AccessToken")
        if not auth_token:
            log.error("No AccessToken. Keys: %s", list(auth.keys()))
            sys.exit(1)

        print("\n===== CUSTOMER DEVICES =====")
        try:
            devices = await api_get(session, CUSTOMER_DEVICES, auth_token)
            print(json.dumps(devices, indent=2, default=str))
        except Exception as e:
            log.warning("get-devices failed: %s", e)
            devices = None

        if device_id:
            target = device_id
        elif devices:
            dev_list = devices if isinstance(devices, list) else devices.get("products") or []
            if isinstance(dev_list, list) and dev_list:
                target = dev_list[0].get("serialNumber") or dev_list[0].get("deviceId")
            else:
                return
        else:
            return

        for action in ["get-dashboard", "get-robot-details", "get-settings",
                        "get-scheduler", "get-on-connection-data"]:
            print(f"\n===== {action.upper()} =====")
            try:
                result = await api_get(session, device_url(target, action), auth_token)
                print(json.dumps(result, indent=2, default=str))
            except Exception as e:
                log.warning("%s failed: %s", action, e)


def _load_env():
    for p in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.is_file():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            break


if __name__ == "__main__":
    _load_env()
    parser = argparse.ArgumentParser(description="Probe Robomow3 cloud API")
    parser.add_argument("--email", default=os.environ.get("EMAIL"))
    parser.add_argument("--password", default=os.environ.get("PASSWORD"))
    parser.add_argument("--device-id", default=os.environ.get("DEVICE_ID"))
    args = parser.parse_args()

    if not args.email or not args.password:
        print("Provide --email and --password, or set EMAIL/PASSWORD in .env")
        sys.exit(1)

    asyncio.run(main(args.email, args.password, args.device_id))
