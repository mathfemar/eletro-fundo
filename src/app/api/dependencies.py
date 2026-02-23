from functools import lru_cache


@lru_cache()
def get_pricing_live_service():
    from app.services.precos.pricing_live_service import PricingLiveService
    return PricingLiveService()


@lru_cache()
def get_historico_service():
    from app.services.precos.historico_service import HistoricoService
    return HistoricoService()
