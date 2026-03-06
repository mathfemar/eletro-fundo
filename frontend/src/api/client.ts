import axios from 'axios'
import type {
  Asset,
  AssetCreatePayload,
  AssetHistoryPoint,
  CapitalEventCreatePayload,
  Fund,
  FundCreatePayload,
  FundDetail,
  Investor,
  InvestorCreatePayload,
  LivePricePoint,
  TimelinePoint,
  TradeCreatePayload,
  TradePreview,
} from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000',
})

export async function fetchAssets(onlyOnline = false, onlyMapped = false): Promise<Asset[]> {
  const { data } = await api.get<Asset[]>('/assets', { params: { only_online: onlyOnline, only_mapped: onlyMapped } })
  return data
}

export async function createAsset(payload: AssetCreatePayload): Promise<Asset> {
  const { data } = await api.post<Asset>('/assets', payload)
  return data
}

export async function updateAsset(assetId: number, payload: AssetCreatePayload): Promise<Asset> {
  const { data } = await api.put<Asset>(`/assets/${assetId}`, payload)
  return data
}

export async function fetchAssetHistory(assetId: number, days?: number): Promise<AssetHistoryPoint[]> {
  const params = days === undefined ? {} : { days }
  const { data } = await api.get<AssetHistoryPoint[]>(`/assets/${assetId}/history`, { params })
  return data
}

export async function fetchAssetLive(assetId: number): Promise<LivePricePoint[]> {
  const { data } = await api.get<LivePricePoint[]>(`/assets/${assetId}/live`)
  return data
}

export async function fetchFunds(): Promise<Fund[]> {
  const { data } = await api.get<Fund[]>('/funds')
  return data
}

export async function createFund(payload: FundCreatePayload): Promise<Fund> {
  const { data } = await api.post<Fund>('/funds', payload)
  return data
}

export async function fetchInvestors(): Promise<Investor[]> {
  const { data } = await api.get<Investor[]>('/investors')
  return data
}

export async function createInvestor(payload: InvestorCreatePayload): Promise<Investor> {
  const { data } = await api.post<Investor>('/investors', payload)
  return data
}

export async function fetchFundDetail(fundId: number): Promise<FundDetail> {
  const { data } = await api.get<FundDetail>(`/funds/${fundId}`)
  return data
}

export async function fetchFundTimeline(fundId: number): Promise<TimelinePoint[]> {
  const { data } = await api.get<TimelinePoint[]>(`/funds/${fundId}/timeline`)
  return data
}

export async function syncHistory(): Promise<void> {
  await api.post('/pricing/sync/history')
}

export async function syncLive(): Promise<void> {
  await api.post('/pricing/sync/live')
}

export async function syncDividends(): Promise<void> {
  await api.post('/pricing/sync/dividends')
}

export async function createCapitalEvent(fundId: number, payload: CapitalEventCreatePayload): Promise<void> {
  await api.post(`/funds/${fundId}/capital-events`, payload)
}

export async function createTrade(fundId: number, payload: TradeCreatePayload): Promise<void> {
  await api.post(`/funds/${fundId}/trades`, payload)
}

export async function recalculateFund(fundId: number): Promise<void> {
  await api.post(`/funds/${fundId}/recalculate`)
}

export async function fetchTradePreview(fundId: number, assetId: number, tradeDate: string, quantity: number, unitPrice: number, fees: number): Promise<TradePreview> {
  const { data } = await api.get<TradePreview>(`/assets/${assetId}/trade-preview`, {
    params: {
      fund_id: fundId,
      trade_date: tradeDate,
      quantity,
      unit_price: unitPrice,
      fees,
    },
  })
  return data
}
