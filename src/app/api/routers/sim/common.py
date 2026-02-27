"""
sim/common.py — Shim de compatibilidade.

DEPRECATED: Use os módulos diretamente:
  sim.models, sim.helpers, sim.caixa, sim.positions, sim.cotas, sim.pnl

Este arquivo apenas re-exporta para manter compatibilidade com imports antigos.
"""

# Re-exports: models
from app.api.routers.sim.models import (  # noqa: F401
    PortfolioInput, FundoInput, FundoSetupInput, FundoSetupCotistaInput,
    FundoCarteiraInput, FundoAlocacaoInput, TitularInput, CorretoraInput,
    TradeInput, FundoFluxoInput, AtivoLiquidezInput, RFTituloInput,
    ResgateSolicitacaoInput, ResgatePlanoInput, ResgatePlanoItemInput,
    ResgateExecucaoInput, ResgateOverrideInput,
)

# Re-exports: helpers
from app.api.routers.sim.helpers import (  # noqa: F401
    TZ_BR, _now_sp, _now_sp_str, _iso_date_sp,
    _get_or_create_legacy_entities, _entity_exists, _list_active_fundo_ids,
    _normalize_currency, _fx_pair_code, _resolve_fx_asset_ids, _get_fx_rate,
    _normalize_trade_payload,
)

# Re-exports: caixa
from app.api.routers.sim.caixa import (  # noqa: F401
    _saldo_carteira_caixa, _get_fundo_caixa_total_sync,
    _assert_portfolio_has_capital_for_trade,
)

# Re-exports: positions
from app.api.routers.sim.positions import (  # noqa: F401
    _build_positions_response, _get_fundo_positions_payload_sync,
    recompute_carteira_posicao_diaria_sync,
)

# Re-exports: cotas
from app.api.routers.sim.cotas import (  # noqa: F401
    recompute_fundo_cotas_sync, recompute_cotistas_posicao_diaria_sync,
    compute_retorno_serie_sync,
)

# Re-exports: pnl
from app.api.routers.sim.pnl import (  # noqa: F401
    capture_pnl_live_fundo_sync, close_pnl_day_fundo_sync,
    backfill_pnl_fechamento_fundo_sync, close_pnl_day_all_fundos_sync,
    catchup_fechamento_all_fundos_sync,
)
