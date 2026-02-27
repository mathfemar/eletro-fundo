"""Diagnose PM calculation."""
import sys
sys.path.insert(0, "src")
from app.services.db_connection import query, query_scalar

# FX asset
fx_id = query_scalar(
    "SELECT ID_ATIVO FROM DIM_ATIVO WHERE CD_ATIVO LIKE 'USD%BRL%' LIMIT 1"
)
print(f"FX asset ID: {fx_id}")

fx_rate_trade = query_scalar(
    """SELECT COALESCE(VL_FECHAMENTO_AJ, VL_FECHAMENTO)
    FROM FAT_ATIVO_PRECO
    WHERE ID_ATIVO = ? AND DT_REFERENCIA <= '2025-02-25'
    ORDER BY DT_REFERENCIA DESC LIMIT 1""",
    params=(fx_id,),
)
print(f"FX at trade date 2025-02-25: {fx_rate_trade}")

fx_live = query_scalar(
    "SELECT VL_PRECO_ATUAL FROM FAT_PRICING_LIVE WHERE ID_ATIVO = ?",
    params=(fx_id,),
)
print(f"FX live: {fx_live}")

# Fund for carteira 27
fundos = query("SELECT rfc.ID_FUNDO, rfc.ID_CARTEIRA FROM RL_FUNDO_CARTEIRA rfc WHERE rfc.ID_CARTEIRA = 27")
print(f"Fund for carteira 27: {fundos.to_dict('records')}")

# Current prices for those assets
for cd in ["AMZO34", "NFLX US", "NVDA US"]:
    row = query(
        """SELECT da.ID_ATIVO, da.CD_ATIVO,
               (SELECT COALESCE(VL_FECHAMENTO_AJ, VL_FECHAMENTO)
                FROM FAT_ATIVO_PRECO WHERE ID_ATIVO = da.ID_ATIVO
                ORDER BY DT_REFERENCIA DESC LIMIT 1) AS PRECO_HIST,
               fl.VL_PRECO_ATUAL AS PRECO_LIVE
        FROM DIM_ATIVO da
        LEFT JOIN FAT_PRICING_LIVE fl ON fl.ID_ATIVO = da.ID_ATIVO
        WHERE da.CD_ATIVO = ?""",
        params=(cd,),
    )
    if not row.empty:
        r = row.to_dict("records")[0]
        print(f"\n{cd}: ID={r['ID_ATIVO']}")
        print(f"  PRECO_HIST (local currency): {r['PRECO_HIST']}")
        print(f"  PRECO_LIVE (local currency): {r['PRECO_LIVE']}")

# Now manually compute what _build_positions_response would produce
print("\n=== Manual PM calculation ===")
trades = [
    ("AMZO34", "BUY", 50, 50.0),   # trade 51
    ("NFLX US", "BUY", 25, 100.0),  # trade 49
    ("NFLX US", "BUY", 50, 50.0),   # trade 50
    ("NVDA US", "BUY", 25, 100.0),  # trade 48
]

fx = float(fx_rate_trade) if fx_rate_trade else 1.0
fx_now = float(fx_live) if fx_live else fx
print(f"FX at trade: {fx}")
print(f"FX now: {fx_now}")

positions = {}
for cd, side, qty, pu in trades:
    pu_brl = pu * fx  # PU in BRL
    if cd not in positions:
        positions[cd] = {"qty": 0, "pm": 0}
    p = positions[cd]
    old_qty = p["qty"]
    old_pm = p["pm"]
    new_qty = old_qty + qty
    new_pm = pu_brl if old_qty == 0 else ((old_qty * old_pm) + (qty * pu_brl)) / new_qty
    p["qty"] = new_qty
    p["pm"] = new_pm

for cd, p in positions.items():
    print(f"  {cd}: qty={p['qty']}, PM(BRL)={p['pm']:.2f}")
