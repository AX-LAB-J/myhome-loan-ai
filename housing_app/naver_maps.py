"""Keep geocoding secrets on server; browser gets public map key and markers."""

import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx


GEOCODE_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
HWASEONG_DISTRICTS = ("동탄구", "만세구", "병점구", "효행구")


def lot_from_name(apt_name):
    match = re.search(r"\((\d{1,5}(?:-\d{1,5})?)\)", str(apt_name))
    if not match:
        return None
    return match.group(1).removesuffix("-0")


def same_locality(requested, matched):
    """Accept a new Hwaseong district only when the remaining address is identical."""
    if matched == requested:
        return True
    old_prefix = "경기도 화성시 "
    if not requested.startswith(old_prefix):
        return False
    for district in HWASEONG_DISTRICTS:
        new_prefix = old_prefix + district + " "
        if matched.startswith(new_prefix) and old_prefix + matched[len(new_prefix) :] == requested:
            return True
    return False


def geocode(address, settings, client=None, apt_name=None):
    if (
        not settings.naver_maps_client_id
        or not settings.naver_maps_client_secret.get_secret_value()
    ):
        raise ValueError("NAVER_MAPS_CLIENT_ID와 NAVER_MAPS_CLIENT_SECRET을 설정하세요.")
    owned = client is None
    client = client or httpx.Client(timeout=15)
    try:
        lot = lot_from_name(apt_name)
        base_queries = [address]
        old_prefix = "경기도 화성시 "
        if address.startswith(old_prefix) and not any(
            address.startswith(old_prefix + district + " ") for district in HWASEONG_DISTRICTS
        ):
            tail = address[len(old_prefix) :]
            base_queries.extend(
                old_prefix + district + " " + tail for district in HWASEONG_DISTRICTS
            )
        # A lot number in the complex name is more precise than the dong centre.
        queries = ([base + " " + lot for base in base_queries] if lot else []) + base_queries
        found = {}
        lot_found = {}
        for query in queries:
            response = client.get(
                GEOCODE_URL,
                params={"query": query, "count": 10},
                headers={
                    "X-NCP-APIGW-API-KEY-ID": settings.naver_maps_client_id,
                    "X-NCP-APIGW-API-KEY": settings.naver_maps_client_secret.get_secret_value(),
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            payload = response.json()
            matches = payload.get("addresses", [])
            if payload.get("status") != "OK":
                continue
            valid = {}
            for item in matches:
                matched = item.get("jibunAddress") or item.get("roadAddress", "")
                locality = (
                    matched.split(" " + lot, 1)[0] if lot and query.endswith(" " + lot) else matched
                )
                if lot and query.endswith(" " + lot) and locality == matched:
                    continue
                if not same_locality(address, locality):
                    continue
                if locality != matched and not matched.startswith(locality + " " + lot):
                    continue
                try:
                    lat, lon = float(item["y"]), float(item["x"])
                except (KeyError, TypeError, ValueError):
                    continue
                if 32 <= lat <= 39.5 and 124 <= lon <= 132:
                    valid[(lat, lon)] = {
                        "latitude": lat,
                        "longitude": lon,
                        "matched_address": matched,
                    }
            if len(valid) == 1:
                if lot and query.endswith(" " + lot):
                    lot_found.update({v["matched_address"]: v for v in valid.values()})
                    if query == address + " " + lot:
                        return next(iter(valid.values()))
                    continue
                found.update({v["matched_address"]: v for v in valid.values()})
                if query == address:
                    return next(iter(valid.values()))
        if len(lot_found) == 1:
            return next(iter(lot_found.values()))
        if len(lot_found) > 1:
            return None
        if len(found) == 1:
            return next(iter(found.values()))
        return None
    finally:
        if owned:
            client.close()


GEOCODE_WORKERS = 8


def cache_key(row):
    lot = lot_from_name(row.get("apt_name"))
    return row["address"] + ("|lot:" + lot if lot else "")


def cached_markers(rows, settings, resolve=False):
    """Attach cached coordinates; with ``resolve``, geocode uncached addresses in parallel
    through one shared HTTP client and store the results."""
    keys = [cache_key(row) for row in rows]
    with sqlite3.connect(settings.database_path) as db:
        placeholders = ",".join("?" for _ in keys) or "''"
        cached = {
            key: (lat, lon, matched)
            for key, lat, lon, matched in db.execute(
                "SELECT address,latitude,longitude,matched_address FROM geocode_cache "
                f"WHERE address IN ({placeholders})",
                keys,
            )
        }
        pending = {key: row for key, row in zip(keys, rows) if key not in cached}
        if resolve and pending:
            with httpx.Client(timeout=15) as client, ThreadPoolExecutor(GEOCODE_WORKERS) as pool:
                found = pool.map(
                    lambda row: geocode(row["address"], settings, client, row.get("apt_name")),
                    pending.values(),
                )
                now = datetime.now(timezone.utc).isoformat()
                for key, hit in zip(pending, found):
                    if hit:
                        cached[key] = (hit["latitude"], hit["longitude"], hit["matched_address"])
                        db.execute(
                            "INSERT OR REPLACE INTO geocode_cache VALUES(?,?,?,?,?)",
                            (key, *cached[key], now),
                        )
    markers, missing = [], []
    for key, row in zip(keys, rows):
        if key in cached:
            lat, lon, matched = cached[key]
            markers.append({**row, "latitude": lat, "longitude": lon, "matched_address": matched})
        else:
            missing.append(row["apt_name"])
    return markers, missing
