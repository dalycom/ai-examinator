#!/usr/bin/env python3
"""Lightweight load smoke test for API health and auth (Phase 6)."""

from __future__ import annotations

import argparse
import concurrent.futures
import statistics
import time
from uuid import uuid4

import httpx


def _one_request(base_url: str, path: str) -> float:
    started = time.perf_counter()
    response = httpx.get(f"{base_url}{path}", timeout=10.0)
    response.raise_for_status()
    return (time.perf_counter() - started) * 1000


def run_load(base_url: str, *, workers: int, requests_per_worker: int, path: str) -> None:
    total = workers * requests_per_worker
    latencies: list[float] = []
    started = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one_request, base_url, path) for _ in range(total)]
        for future in concurrent.futures.as_completed(futures):
            latencies.append(future.result())

    elapsed = time.perf_counter() - started
    print(f"Target: {base_url}{path}")
    print(f"Requests: {total} | Workers: {workers} | Duration: {elapsed:.2f}s")
    print(f"Throughput: {total / elapsed:.1f} req/s")
    print(f"Latency ms — p50: {statistics.median(latencies):.1f} | p95: {_percentile(latencies, 95):.1f}")


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def run_auth_smoke(base_url: str) -> None:
    slug = f"load-{uuid4().hex[:8]}"
    email = f"admin+{slug}@example.com"
    password = "LoadTestPassword123!"
    register = httpx.post(
        f"{base_url}/api/v1/auth/register-organization",
        json={
            "organization_name": f"Load Org {slug}",
            "organization_slug": slug,
            "admin_email": email,
            "admin_full_name": "Load Tester",
            "admin_password": password,
            "default_locale": "en",
        },
        timeout=15.0,
    )
    register.raise_for_status()
    login = httpx.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=15.0,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    me = httpx.get(
        f"{base_url}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    me.raise_for_status()
    print("Auth smoke: register → login → me OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Examinator load smoke test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--requests", type=int, default=20, help="Requests per worker")
    parser.add_argument("--path", default="/health")
    parser.add_argument("--auth-smoke", action="store_true")
    args = parser.parse_args()

    if args.auth_smoke:
        run_auth_smoke(args.base_url)
    run_load(args.base_url, workers=args.workers, requests_per_worker=args.requests, path=args.path)


if __name__ == "__main__":
    main()
