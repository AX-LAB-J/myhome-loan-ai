export type Screen = 'home' | 'explore' | 'detail' | 'finance' | 'assumptions' | 'connections'

export const screenTitles: Record<Screen, string> = {
  home: '내 집 마련', explore: '지역·단지 찾기', detail: '단지 상세', finance: '내 재무 정보',
  assumptions: '계산 가정', connections: '데이터 연결 현황',
}
