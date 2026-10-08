import { useEffect, useRef, useState } from 'react'
import type { Trade } from '../api'
import { won } from '../format'

type NaverGlobal = { maps: {
  Map: new (node: HTMLElement, options: object) => MapInstance
  LatLng: new (lat: number, lon: number) => unknown
  LatLngBounds: new () => { extend(point: unknown): void }
  Marker: new (options: object) => MarkerInstance
  InfoWindow: new (options: object) => { open(map: MapInstance, marker: MarkerInstance): void; close(): void }
  Event: { addListener(target: object, event: string, callback: () => void): void }
}}
type MapInstance = { fitBounds(bounds: object): void; setCenter(point: unknown): void }
type MarkerInstance = { setMap(map: MapInstance | null): void }
declare global { interface Window { naver?: NaverGlobal; navermap_authFailure?: () => void } }

let sdkPromise: Promise<NaverGlobal> | undefined
function loadSdk(clientId: string): Promise<NaverGlobal> {
  if (window.naver?.maps?.Map) return Promise.resolve(window.naver)
  if (sdkPromise) return sdkPromise
  sdkPromise = new Promise<NaverGlobal>((resolve, reject) => {
    const script = document.createElement('script')
    let timedOut = false
    const timeout = window.setTimeout(() => { timedOut = true; reject(new Error('네이버 지도 로딩 시간이 초과되었습니다.')) }, 15000)
    const finish = () => {
      if (timedOut) return
      if (window.naver?.maps?.Map) { window.clearTimeout(timeout); resolve(window.naver) }
      else window.setTimeout(finish, 100)
    }
    window.navermap_authFailure = () => { window.clearTimeout(timeout); reject(new Error('지도 인증 실패: 네이버 Cloud에 현재 접속 도메인을 등록해주세요.')) }
    script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(clientId)}`
    script.onload = finish
    script.onerror = () => { window.clearTimeout(timeout); reject(new Error('네이버 지도 스크립트를 불러오지 못했습니다.')) }
    document.head.appendChild(script)
  }).catch(error => { sdkPromise = undefined; throw error })
  return sdkPromise
}

export default function NaverMap({ clientId, markers, onSelect }: { clientId: string; markers: Trade[]; onSelect?: (trade: Trade) => void }) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapInstance | null>(null)
  const pins = useRef<MarkerInstance[]>([])
  const info = useRef<{close(): void} | null>(null)
  const [status, setStatus] = useState('지도 불러오는 중…')

  useEffect(() => {
    if (!clientId) { setStatus('네이버 지도 Client ID가 설정되지 않았습니다.'); return }
    let active = true
    loadSdk(clientId).then(naver => {
      if (!active || !container.current) return
      if (!mapRef.current) mapRef.current = new naver.maps.Map(container.current, { center: new naver.maps.LatLng(37.5665, 126.978), zoom: 11, zoomControl: true })
      setStatus('')
    }).catch(error => { if (active) setStatus(error instanceof Error ? error.message : '지도를 불러오지 못했습니다.') })
    return () => { active = false }
  }, [clientId])

  useEffect(() => {
    const map = mapRef.current
    const naver = window.naver
    if (!map || !naver) return
    pins.current.forEach(pin => pin.setMap(null)); pins.current = []; info.current?.close()
    const bounds = new naver.maps.LatLngBounds()
    const groups = new Map<string, Trade[]>()
    markers.forEach(row => {
      if (row.latitude == null || row.longitude == null) return
      const key = `${row.latitude.toFixed(6)}|${row.longitude.toFixed(6)}`
      groups.set(key, [...(groups.get(key) ?? []), row])
    })
    groups.forEach(rows => {
      const row = rows[0]
      const hasOwned = rows.some(item => item.is_owned)
      const point = new naver.maps.LatLng(row.latitude!, row.longitude!)
      bounds.extend(point)
      const marker = new naver.maps.Marker({ map, position: point,
        title: hasOwned ? `내 주택 포함 · ${row.address}` : rows.length > 1 ? `${row.address} · ${rows.length}개 단지` : row.apt_name,
        ...(rows.length > 1 || hasOwned ? { icon: { content: `<span class="map-group-pin${hasOwned ? ' map-owned-pin' : ''}">${hasOwned ? '⌂' : ''}${rows.length > 1 ? rows.length : ''}</span>` } } : {}) })
      pins.current.push(marker)
      naver.maps.Event.addListener(marker, 'click', () => {
        info.current?.close()
        const card = document.createElement('div'); card.className = 'map-popup'
        const title = document.createElement('strong'); title.textContent = `${hasOwned ? '내 주택 포함 · ' : ''}${rows.length > 1 ? `${row.address} · ${rows.length}개 항목` : row.apt_name}`; card.append(title)
        if (rows.length > 1) {
          const note = document.createElement('span'); note.textContent = '같은 동 중심 좌표에 표시된 단지입니다.'; card.append(note)
          rows.forEach(item => {
            const choice = document.createElement('button'); choice.type = 'button'
            choice.textContent = `${item.is_owned ? '내 주택 · ' : ''}${item.apt_name} · ${won(item.purchase_reference_price)}`
            choice.addEventListener('click', () => { onSelect?.(item); info.current?.close() })
            card.append(choice)
          })
        } else {
          onSelect?.(row)
          const details = [row.address, `거래 참조가격 ${won(row.purchase_reference_price)}`, `면적 ${row.exclusive_area_m2}㎡ · ${row.reference_deal_date}`, `고객 ${row.loan_summary?.customers ?? 0}명`, `최초 원금 ${won(row.loan_summary?.original)}`, `대출 잔액 ${won(row.loan_summary?.balance)}`, '좌표는 동 주소의 중심점 또는 단지명에 명시된 지번 기준입니다.']
          details.forEach(text => { const line = document.createElement('span'); line.textContent = text; card.append(line) })
        }
        const popup = new naver.maps.InfoWindow({ content: card })
        popup.open(map, marker); info.current = popup
      })
    })
    if (pins.current.length > 1) map.fitBounds(bounds)
    else if (pins.current.length === 1) {
      const first = markers.find(row => row.latitude != null && row.longitude != null)!
      map.setCenter(new naver.maps.LatLng(first.latitude!, first.longitude!))
    }
  }, [markers, status, onSelect])

  return <div className="map-shell">
    <div className="naver-map" ref={container} role="application" aria-label="네이버 아파트 지도" />
    {status && <div className="map-status" role="status">{status}</div>}
    {!status && markers.length > 0 && <div className="map-precision-note">{markers.some(row => row.is_owned) ? '⌂ 내 주택 · ' : ''}동 중심/지번 좌표 · 같은 위치는 묶어 표시</div>}
  </div>
}

