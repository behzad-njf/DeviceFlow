#!/usr/bin/env python3
"""
Mock DeviceFlow Android agent for local testing without a phone.

Supports SMS send, OTA install_update, and USSD (ussd_run) actions.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

AGENT_VERSION = "0.2.0-mock"
CAPABILITIES = [
    "sms.send",
    "sms.receive",
    "ussd.run",
    "ota.update",
]


def request(method: str, url: str, token: str | None = None, payload: dict | None = None):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Device {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def main() -> int:
    global AGENT_VERSION
    parser = argparse.ArgumentParser(description="DeviceFlow mock agent")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--code", required=True, help="Pairing code from dashboard")
    parser.add_argument("--poll", type=float, default=2.0)
    parser.add_argument("--fail-rate", type=float, default=0.0)
    parser.add_argument("--version", default=AGENT_VERSION)
    args = parser.parse_args()
    AGENT_VERSION = args.version
    base = args.base_url.rstrip("/")

    print(f"Pairing with {base} ...")
    try:
        _, pair = request(
            "POST",
            f"{base}/agent/pair/",
            payload={
                "pairing_code": args.code,
                "device_info": {
                    "agent_version": AGENT_VERSION,
                    "model": "MockAgent",
                    "android_version": "14",
                    "capabilities": CAPABILITIES,
                    "sims": [
                        {
                            "slot_index": 1,
                            "operator": "MockTel",
                            "phone_number": "+10000000000",
                        }
                    ],
                },
            },
        )
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        return 1

    token = pair["device_token"]
    device_id = pair["device_id"]
    print(f"Paired device_id={device_id} version={AGENT_VERSION} caps={CAPABILITIES}")

    while True:
        try:
            request(
                "POST",
                f"{base}/agent/heartbeat/",
                token=token,
                payload={
                    "battery": 88,
                    "charging": True,
                    "signal": "excellent",
                    "network": "wifi",
                    "queue_size": 0,
                    "agent_version": AGENT_VERSION,
                    "capabilities": CAPABILITIES,
                    # Tehran — so the dashboard map has something without a physical phone.
                    "lat": 35.6892,
                    "lng": 51.3890,
                    "accuracy_m": 25,
                    "location_updated_at_ms": int(time.time() * 1000),
                    "permissions": {"sms": True, "phone": True, "location": True},
                    "sims": [
                        {
                            "slot_index": 1,
                            "operator": "MockTel",
                            "phone_number": "+10000000000",
                        }
                    ],
                },
            )
            _, pending = request(
                "GET", f"{base}/agent/commands/pending/", token=token
            )
            for cmd in pending.get("results", []):
                ctype = cmd.get("type")
                if ctype == "command.control":
                    payload = cmd.get("payload") or {}
                    action = payload.get("action")
                    params = payload.get("params") or {}
                    command_id = cmd.get("command_id")
                    print(f"CONTROL -> {action} {params}")
                    result = {"status": "acked", "action": action}
                    if action == "install_update":
                        new_ver = params.get("version") or AGENT_VERSION
                        AGENT_VERSION = str(new_ver)
                        result["version"] = AGENT_VERSION
                        print(f"OTA applied -> version={AGENT_VERSION}")
                    elif action == "ussd_run":
                        code = params.get("code") or "*141#"
                        sim_slot = params.get("sim_slot")
                        result["ussd_code"] = code
                        result["ussd_response"] = f"Mock balance OK for {code}"
                        if sim_slot is not None:
                            result["sim_slot"] = sim_slot
                        print(f"USSD -> SIM{sim_slot or 'default'} {code} => {result['ussd_response']}")
                    elif action == "call_place":
                        result["to"] = params.get("to")
                        result["note"] = "mock call placed"
                    elif action == "call_log_read":
                        result["entries"] = [
                            {"number": "+10000000001", "type": "missed", "ts": time.time()}
                        ]
                    elif action == "contacts_read":
                        result["ok"] = True
                        result["handled"] = True
                        result["contacts"] = [
                            {"name": "Ali Rezaei", "phone": "09121234567"},
                            {"name": "Sara Karimi", "phone": "+989351112233"},
                            {"name": "Invalid Entry", "phone": "123"},
                            {"name": "Office", "phone": "02188776655"},
                            {"name": "Duplicate", "phone": "09121234567"},
                        ]
                        result["count"] = len(result["contacts"])
                        result["truncated"] = False
                        print(f"CONTACTS -> {result['count']} rows")
                    request(
                        "POST",
                        f"{base}/agent/commands/{command_id}/ack/",
                        token=token,
                        payload={"status": "acked", "result": result},
                    )
                    continue
                if ctype != "command.send_sms":
                    continue
                payload = cmd["payload"]
                message_id = payload["message_id"]
                print(f"SEND -> {payload['to']}: {payload['text'][:60]}")
                request(
                    "POST",
                    f"{base}/agent/messages/{message_id}/status/",
                    token=token,
                    payload={"status": "sending"},
                )
                time.sleep(0.2)
                request(
                    "POST",
                    f"{base}/agent/messages/{message_id}/status/",
                    token=token,
                    payload={
                        "status": "sent",
                        "latency_ms": 150,
                        "sim_slot": payload.get("sim_slot") or 1,
                    },
                )
                print(f"SENT message_id={message_id}")
        except Exception as exc:  # noqa: BLE001
            print(f"loop error: {exc}", file=sys.stderr)
        time.sleep(args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
