"""
scripts/testar_precos.py — Testa as rotinas de preços sem precisar subir a API.

Execução (na raiz do projeto, com .venv ativado):
    python scripts/testar_precos.py
"""

import sys
import os

# ── Garante que src/ está no PYTHONPATH ──────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC  = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# ─────────────────────────────────────────────────────────────────────────────

from app.services.precos.db_setup import create_tables
from app.services.precos.pricing_live_service import PricingLiveService
from app.services.precos.historico_service import HistoricoService
from app.services.db_connection import list_tables, table_info, query


def sep(titulo: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {titulo}")
    print(f"{'─' * 60}")


# ── 1. Verificar / criar tabelas ─────────────────────────────────────────────
sep("1. CREATE TABLES")
create_tables()
tabelas = list_tables()
print("Tabelas no banco:", tabelas)

# ── 2. Inspecionar schema das novas tabelas ──────────────────────────────────
sep("2. SCHEMA — FAT_PRICING_LIVE")
print(table_info("FAT_PRICING_LIVE").to_string())

sep("2. SCHEMA — FAT_ATIVO_PRECO")
print(table_info("FAT_ATIVO_PRECO").to_string())

# ── 3. Verificar ativos mapeados (DIM_ATIVO_MAPPING com CD_YF) ───────────────
sep("3. ATIVOS MAPEADOS")
df_map = query("""
    SELECT da.CD_ATIVO, dam.CD_YF
    FROM DIM_ATIVO da
    JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = da.ID_ATIVO
    WHERE dam.CD_YF IS NOT NULL AND TRIM(dam.CD_YF) != ''
    LIMIT 20
""")
if df_map.empty:
    print("⚠  Nenhum ativo com CD_YF mapeado ainda.")
    print("   Rode primeiro o yfinance_mapping_service para mapear CUSIPs → Tickers.")
    sys.exit(0)
else:
    print(df_map.to_string(index=False))

# ── 4. Atualizar preços live ─────────────────────────────────────────────────
sep("4. FAT_PRICING_LIVE — atualizar_todos()")
live_svc = PricingLiveService()
resultado_live = live_svc.atualizar_todos(max_workers=3, delay_s=0.3)
print("Resultado:", resultado_live)

# ── 5. Ler snapshot live do banco ─────────────────────────────────────────────
sep("5. FAT_PRICING_LIVE — get_live()")
snapshot = live_svc.get_live()
if snapshot:
    import pandas as pd
    df_snap = pd.DataFrame(snapshot)
    print(df_snap[["CD_ATIVO", "VL_PRECO_ATUAL", "VL_VAR_DIA_PCT", "DT_HORA_CAPTURA"]].to_string(index=False))
else:
    print("Sem dados no snapshot.")

# ── 6. Carregar histórico (últimos 30 dias para agilizar o teste) ─────────────
sep("6. FAT_ATIVO_PRECO — carregar_historico()")
from datetime import date, timedelta
dt_inicio = (date.today() - timedelta(days=30)).isoformat()
hist_svc = HistoricoService()
resultado_hist = hist_svc.carregar_historico(dt_inicio=dt_inicio)
print("Resultado:", resultado_hist)

# ── 7. Resumo do histórico carregado ─────────────────────────────────────────
sep("7. FAT_ATIVO_PRECO — resumo()")
resumo = hist_svc.resumo()
if resumo:
    import pandas as pd
    print(pd.DataFrame(resumo).to_string(index=False))
else:
    print("Sem dados históricos no banco.")

# ── 8. Série de um ativo específico ──────────────────────────────────────────
if snapshot:
    primeiro_ativo = snapshot[0]["CD_ATIVO"]
    sep(f"8. FAT_ATIVO_PRECO — get_historico('{primeiro_ativo}')")
    serie = hist_svc.get_historico(cd_ativo=primeiro_ativo, dt_inicio=dt_inicio)
    if serie:
        import pandas as pd
        print(pd.DataFrame(serie)[["DT_REFERENCIA", "VL_FECHAMENTO", "VL_FECHAMENTO_AJ", "VL_VOLUME"]].to_string(index=False))
    else:
        print("Sem dados históricos para este ativo.")

print("\n✓ Testes concluídos.")
