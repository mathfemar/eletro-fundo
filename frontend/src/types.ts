export type Asset = {
  id_ativo: number
  cd_ativo: string
  cd_yf?: string | null
  preco_online: boolean
  moeda: string
  fator_preco: number
  last_close?: number | null
  last_adj_close?: number | null
}

export type AssetHistoryPoint = {
  price_date: string
  close_price: number
  adj_close_price: number
  daily_return?: number | null
}

export type LivePricePoint = {
  collected_at: string
  price: number
}

export type Fund = {
  id: number
  name: string
  inception_date: string
  base_currency: string
}

export type Investor = {
  id: number
  name: string
}

export type CapitalEventType = 'INITIAL' | 'CONTRIBUTION' | 'REDEMPTION'

export type TradeSide = 'BUY' | 'SELL'

export type FundSnapshot = {
  ref_date: string
  cash_balance: number
  invested_value: number
  nav: number
  unit_count: number
  unit_value: number
}

export type InvestorSnapshot = {
  investor_id: number
  investor_name: string
  unit_count: number
  position_value: number
  ownership_percent: number
  average_unit_cost: number
  pnl: number
}

export type FundPosition = {
  asset_id: number
  asset_code: string
  currency: string
  quantity: number
  average_cost_brl: number
  current_price_local: number
  fx_rate: number
  market_value_brl: number
  allocation_percent: number
  pnl_brl: number
}

export type FundDetail = {
  fund: Fund
  snapshot: FundSnapshot | null
  investors: InvestorSnapshot[]
  positions: FundPosition[]
}

export type TimelinePoint = {
  ref_date: string
  nav: number
  unit_value: number
  cash_balance: number
  invested_value: number
}

export type AssetCreatePayload = {
  cd_ativo: string
  cd_yf?: string | null
  preco_online: boolean
  moeda: string
  fator_preco: number
}

export type FundCreatePayload = {
  name: string
  inception_date: string
  base_currency: string
}

export type InvestorCreatePayload = {
  name: string
}

export type CapitalEventCreatePayload = {
  investor_id: number
  event_type: CapitalEventType
  event_date: string
  amount: number
  notes?: string
}

export type TradeCreatePayload = {
  asset_id: number
  trade_date: string
  side: TradeSide
  quantity: number
  unit_price: number
  fees: number
  notes?: string
}

export type TradePreview = {
  fund_id: number
  asset_id: number
  asset_code: string
  asset_currency: string
  trade_date: string
  fx_asset_code?: string | null
  fx_rate: number
  quantity: number
  unit_price: number
  gross_value_local: number
  fees_local: number
  gross_value_brl: number
  fees_brl: number
  total_value_brl: number
  cash_before_trade_brl: number
}
