import { useMemo } from 'react'
import { ChevronRight } from 'lucide-react'
import type { Buyer, ExploreResult, PlanResult, Trade } from '../api'
import NaverMap from '../components/NaverMap'
import { BandBar, PlanWarnings, Row } from '../components/ui'
import { band, bandLabels, boundaryMoney, money, rangeCap, tierCap, withinRange, type Range } from '../format'

const AREA_CHOICES = [59, 84, 99, 114]
const YEAR_CHOICES = Array.from({ length: 9 }, (_, i) => 2026 - i)
const LIST_TABS: Range[] = ['all', 'possible', 'safe', 'limit']
const MAP_TABS = ['possible', 'safe', 'limit'] as const

export type Sort = 'low' | 'new'

export default function ExploreScreen(props: {
  buyer: Buyer; regions: Record<string, string[]>; plan: PlanResult | null; explore: ExploreResult | null
  range: Range; onRange: (range: Range) => void; sort: Sort; onSort: (sort: Sort) => void
  mapView: boolean; onListView: () => void; mapMarkers: Trade[]; mapError: string; naverClientId: string
  selected: Trade | null; onMapSelect: (trade: Trade) => void; onChoose: (trade: Trade) => void
  onFilter: (patch: Partial<Buyer>) => void; onHome: () => void; onOwnedHome: () => void
}) {
  const { buyer, regions, plan, explore, range, sort, selected } = props
  const bands = plan?.bands
  const inRange = useMemo(
    () => (explore?.rows ?? []).filter(row => withinRange(row.purchase_reference_price, range, bands)),
    [explore, range, bands],
  )
  const rows = useMemo(
    () => sort === 'new' ? [...inRange].sort((a, b) => b.reference_deal_date.localeCompare(a.reference_deal_date)) : inRange,
    [inRange, sort],
  )
  // Map markers carry coordinates; prices and plans come from the list so both views agree.
  const visibleMarkers = useMemo(() => {
    const byComplex = new Map(inRange.map(row => [row.complex_id, row]))
    return props.mapMarkers.flatMap(marker => {
      if (marker.is_owned) return [marker]
      const trade = byComplex.get(marker.complex_id)
      return trade ? [{ ...trade, latitude: marker.latitude, longitude: marker.longitude, loan_summary: marker.loan_summary }] : []
    })
  }, [props.mapMarkers, inRange])

  const lowestPrice = explore?.rows.length ? Math.min(...explore.rows.map(row => row.purchase_reference_price)) : null
  const emptyMessage = range === 'all'
    ? '현재 지역·면적·거래 기간에 맞는 단지가 없습니다. 조건을 바꿔 보세요.'
    : `${bandLabels[range]} 상한 이하 단지가 0곳입니다. ${lowestPrice != null && bands && lowestPrice > rangeCap(range, bands) ? `이 지역 최저 참조가격 ${money(lowestPrice)}이 ${bandLabels[range]} 상한보다 높습니다.` : '현재 지역·면적·기간에 해당하는 단지가 없습니다.'} 전체 목록에서 다른 단지를 확인할 수 있습니다.`

  return <>
    <section className="mobile-card compact">
      <div className="title-row"><h2>내 구매력 구간</h2><button className="text-link" onClick={props.onHome}>자세히 <ChevronRight size={15} /></button></div>
      {bands && <><BandBar bands={bands} /><p className="hint">안정권 {tierCap(0, bands.safe)} · 가능권 {tierCap(bands.safe, bands.possible)} · 한계권 {tierCap(bands.possible, bands.maximum)} · 범위 밖 {boundaryMoney(bands.maximum)} 초과</p></>}
    </section>
    <div className="filter-row">
      <label>시·도<select value={buyer.sido} onChange={e => {
        const sido = e.target.value
        props.onFilter({ sido, sigungu: regions[sido]?.[0] ?? buyer.sigungu })
      }}>{Object.keys(regions).map(v => <option key={v}>{v}</option>)}</select></label>
      <label>지역<select value={buyer.sigungu} onChange={e => props.onFilter({ sigungu: e.target.value })}>
        {(regions[buyer.sido] ?? [buyer.sigungu]).map(v => <option key={v}>{v}</option>)}
      </select></label>
      <label>전용면적<select value={buyer.area} onChange={e => props.onFilter({ area: Number(e.target.value) })}>
        {Array.from(new Set([buyer.area, ...AREA_CHOICES])).sort((a, b) => a - b).map(v => <option value={v} key={v}>{Number(v.toFixed(1))}㎡ ±{Math.round(buyer.area_tolerance * 100)}%</option>)}
      </select></label>
      <label>거래 시작연도<select value={buyer.min_year} onChange={e => props.onFilter({ min_year: Number(e.target.value) })}>
        {YEAR_CHOICES.map(v => <option value={v} key={v}>{v}년 이후</option>)}
      </select></label>
    </div>
    {!props.mapView ? <>
      <div className="range-tabs">{LIST_TABS.map(v => <button key={v} className={range === v ? 'active' : ''} onClick={() => props.onRange(v)}>{v === 'all' ? '전체' : v === 'safe' ? bandLabels[v] : bandLabels[v] + '까지'}</button>)}</div>
      <div className="title-row results"><b>단지 {rows.length}곳</b><select aria-label="정렬" value={sort} onChange={e => props.onSort(e.target.value as Sort)}><option value="low">가격 낮은 순</option><option value="new">최근 거래 순</option></select></div>
      {rows.length ? rows.map(row => {
        const name = band(row.purchase_reference_price, bands)
        return <button className="mobile-card result-card" key={row.complex_id} onClick={() => props.onChoose(row)}>
          <div className="title-row"><h2>{row.apt_name}</h2><span className={'status ' + name}>{bandLabels[name]}</span></div>
          {bands && <BandBar bands={bands} price={row.purchase_reference_price} />}
          <Row label={`최근 실거래 · 전용 ${row.exclusive_area_m2}㎡`} value={money(row.purchase_reference_price)} />
          <Row label="이 집을 사면 매달 남는 돈" value={money(row.plan?.surplus)} />
          <PlanWarnings trade={row} />
        </button>
      }) : <div className="mobile-card empty">{emptyMessage}</div>}
    </> : <>
      <div className="map-range">
        <button className={range === 'all' ? 'active' : ''} onClick={() => props.onRange('all')}>전체</button>
        {MAP_TABS.map(v => <button key={v} className={range === v ? 'active' : ''} onClick={() => props.onRange(v)}>{bandLabels[v]}까지</button>)}
      </div>
      <NaverMap clientId={props.naverClientId} markers={visibleMarkers} onSelect={props.onMapSelect} />
      {props.mapError && <p className="hint">지도 좌표를 불러오지 못했습니다: {props.mapError}</p>}
      <div className="mobile-card">
        <h2>{(selected?.is_owned ? '내 주택 · ' : '') + (selected?.apt_name ?? buyer.sigungu)}</h2>
        {selected ? <>
          <Row label="최근 실거래" value={money(selected.purchase_reference_price)} />
          <button className="primary" onClick={() => selected.is_owned ? props.onOwnedHome() : props.onChoose(selected)}>{selected.is_owned ? '내 재무 정보 보기' : '단지 상세 보기'}</button>
        </> : <>
          <p>{inRange.length ? '지도 마커를 선택해 단지를 확인하세요.' : '선택한 구간에 단지가 없습니다. 내 주택 표식은 별도로 표시됩니다.'}</p>
          <button className="secondary" onClick={props.onListView}>목록</button>
        </>}
      </div>
    </>}
  </>
}
