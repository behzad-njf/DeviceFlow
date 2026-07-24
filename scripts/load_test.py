#!/usr/bin/env python3
"""
Simple load / soak harness for DeviceFlow send API.

Usage:
  python scripts/load_test.py --base http://127.0.0.1:8000 --token JWT --project slug --n 50 --concurrency 5
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def send_one(base: str, token: str, project: str, i: int) -> tuple[int, float, str]:
    started = time.perf_counter()
    body = json.dumps(
        {
            "to": f"+98912{i:07d}"[-12:],
            "text": f"load-test-{i}",
            "project": project,
        }
    ).encode()
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/v1/messages/send/",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            _ = resp.read()
            return resp.status, (time.perf_counter() - started) * 1000, "ok"
    except urllib.error.HTTPError as exc:
        return exc.code, (time.perf_counter() - started) * 1000, str(exc)
    except Exception as exc:  # noqa: BLE001
        return 0, (time.perf_counter() - started) * 1000, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    latencies: list[float] = []
    statuses: dict[int, int] = {}
    errors = 0
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(send_one, args.base, args.token, args.project, i)
            for i in range(args.n)
        ]
        for fut in as_completed(futures):
            code, ms, _msg = fut.result()
            statuses[code] = statuses.get(code, 0) + 1
            latencies.append(ms)
            if code not in {200, 202}:
                errors += 1
    elapsed = time.perf_counter() - t0
    print("DeviceFlow load test report")
    print(f"  requests: {args.n}")
    print(f"  concurrency: {args.concurrency}")
    print(f"  wall_seconds: {elapsed:.2f}")
    print(f"  rps: {args.n / elapsed:.2f}")
    print(f"  errors: {errors}")
    print(f"  status_counts: {statuses}")
    if latencies:
        print(f"  latency_ms_p50: {statistics.median(latencies):.1f}")
        print(f"  latency_ms_avg: {statistics.mean(latencies):.1f}")
        print(f"  latency_ms_max: {max(latencies):.1f}")


if __name__ == "__main__":
    main()
