"""Keep geocoding secrets on server; browser gets public map key and markers."""

import json
import re
import sqlite3
from datetime import datetime, timezone
from urllib.parse import quote
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
        if matched.startswith(new_prefix) and old_prefix + matched[len(new_prefix):] == requested:
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
            tail = address[len(old_prefix):]
            base_queries.extend(old_prefix + district + " " + tail for district in HWASEONG_DISTRICTS)
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
                locality = matched.split(" " + lot, 1)[0] if lot and query.endswith(" " + lot) else matched
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
                    valid[(lat, lon)] = {"latitude": lat, "longitude": lon, "matched_address": matched}
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


def cached_markers(rows, settings, resolve=False):
    markers = []
    missing = []
    with sqlite3.connect(settings.database_path) as db:
        for row in rows:
            lot = lot_from_name(row.get("apt_name"))
            cache_key = row["address"] + ("|lot:" + lot if lot else "")
            cached = db.execute(
                "SELECT latitude,longitude,matched_address FROM geocode_cache WHERE address=?",
                (cache_key,),
            ).fetchone()
            if cached is None and resolve:
                found = geocode(row["address"], settings, apt_name=row.get("apt_name"))
                if found:
                    cached = (found["latitude"], found["longitude"], found["matched_address"])
                    db.execute(
                        "INSERT OR REPLACE INTO geocode_cache VALUES(?,?,?,?,?)",
                        (cache_key, *cached, datetime.now(timezone.utc).isoformat()),
                    )
            if cached:
                markers.append(
                    {
                        **row,
                        "latitude": cached[0],
                        "longitude": cached[1],
                        "matched_address": cached[2],
                    }
                )
            else:
                missing.append(row["apt_name"])
    return markers, missing


def map_html(markers, client_id):
    data = json.dumps(markers, ensure_ascii=False, default=str).replace("<", "\\u003c")
    key = quote(client_id, safe="")
    return (
        """<!doctype html><html lang="ko"><meta charset="utf-8"><style>body{margin:0;font:14px system-ui}#map{height:520px}#status{padding:10px;color:#456}.info{padding:14px;max-width:290px;line-height:1.7}</style><div id="status">네이버 지도 불러오는 중…</div><div id="map"></div>
<script>const rows="""
        + data
        + """;const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let attempts=0;let initialized=false;
function initMap(){if(initialized)return;if(!window.naver||!window.naver.maps||!window.naver.maps.Map){if(++attempts<100){setTimeout(initMap,100);}else{document.getElementById('status').textContent='지도 SDK 초기화 실패. 네이버 Web Dynamic Map과 허용 URL 설정을 확인하세요.';}return;}initialized=true;try{
const center=rows.length?new naver.maps.LatLng(rows[0].latitude,rows[0].longitude):new naver.maps.LatLng(37.5665,126.978);
const map=new naver.maps.Map('map',{center,zoom:13,zoomControl:true});const bounds=new naver.maps.LatLngBounds();
rows.forEach(r=>{const pos=new naver.maps.LatLng(r.latitude,r.longitude);bounds.extend(pos);const marker=new naver.maps.Marker({position:pos,map,title:r.apt_name});
const money=v=>(Number(v)/1e8).toLocaleString('ko-KR',{maximumFractionDigits:2})+'억 원';
const info=new naver.maps.InfoWindow({content:'<div class="info"><b>'+escapeHtml(r.apt_name)+'</b><br>'+escapeHtml(r.address)+'<br>거래 참조가격 '+money(r.purchase_reference_price)+'<br>거래일 '+escapeHtml(r.reference_deal_date)+'<br>면적 '+escapeHtml(r.exclusive_area_m2)+'㎡<br>합성 고객 '+escapeHtml(r.loan_summary.customers)+'명<br>최초 원금 합계 '+money(r.loan_summary.original)+'<br>잔액 합계 '+money(r.loan_summary.balance)+'</div>'});naver.maps.Event.addListener(marker,'click',()=>info.open(map,marker));});if(rows.length>1)map.fitBounds(bounds);document.getElementById('status').textContent=rows.length?'단지를 누르면 가격과 대출 정보를 볼 수 있습니다.':'지도를 표시했습니다. 단지 좌표를 불러오는 중이거나 확인 가능한 좌표가 없습니다.';}catch(error){document.getElementById('status').textContent='지도 초기화 오류: '+error.name;}}
function queueMap(){setTimeout(initMap,0);}
window.navermap_authFailure=()=>document.getElementById('status').textContent='지도 인증 실패: NAVER 키와 허용 웹 서비스 URL을 확인하세요.';
</script><script src="https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId="""
        + key
        + """&callback=queueMap" onerror="document.getElementById('status').textContent='지도 스크립트를 불러오지 못했습니다.'"></script></html>"""
    )
