"""
test_fundo_calculo.py — Verifica consistência entre PL, Cota e Cotista.

Uso: python tests/test_fundo_calculo.py
     (roda contra a API local — servidor deve estar rodando)
"""
import sys
import requests

BASE = "http://localhost:3003/api/sim"

def check_fundo_consistency(fundo_id: int):
    """Verifica que PL, Cota e Cotista convergem para o fundo dado."""
    # 1) Dashboard
    r = requests.get(f"{BASE}/fundos/dashboard", params={"fundo_id": fundo_id})
    r.raise_for_status()
    data = r.json()["data"]
    resumo = data["resumo"]
    pnl_items = data["pnl_fechamento"]["items"]
    cota_items = data["cotas"]["items"]
    cotistas = data["cotistas_posicao"]["items"]

    if not pnl_items or not cota_items:
        print(f"  ⚠ Fundo {fundo_id} sem dados de fechamento/cota — pulando.")
        return True

    # 2) PL do card KPI deve ser igual ao PL do último PNL_FECHAMENTO
    pl_ultimo_fechamento = float(pnl_items[-1]["VL_VALOR_MERCADO_TOTAL"] or 0)
    pl_ultimo_resumo = float(resumo.get("VL_PL_ULTIMO") or 0)

    print(f"\n  === Fundo {fundo_id} ===")
    print(f"  PL último fechamento (PNL_FECHAMENTO): {pl_ultimo_fechamento:,.2f}")
    print(f"  PL último resumo (dashboard):          {pl_ultimo_resumo:,.2f}")

    ok = True
    if abs(pl_ultimo_fechamento - pl_ultimo_resumo) > 0.01:
        print(f"  ❌ DIVERGÊNCIA: PL resumo ≠ PL fechamento")
        ok = False
    else:
        print(f"  ✅ PL resumo == PL fechamento")

    # 3) VL_PL da última cota deve ser ≈ PL do último fechamento
    last_cota = cota_items[-1]
    vl_pl_cota = float(last_cota.get("VL_PL") or 0)
    vl_cota = float(last_cota.get("VL_COTA") or 0)
    qt_cotas = float(last_cota.get("QT_COTAS") or 0)

    print(f"  VL_PL da cota diária:                  {vl_pl_cota:,.2f}")
    print(f"  Cota: {vl_cota:.6f}  |  QT_COTAS: {qt_cotas:,.6f}")
    print(f"  Cota × QT_COTAS = {vl_cota * qt_cotas:,.2f}")

    if abs(vl_pl_cota - pl_ultimo_fechamento) > 1.0:
        print(f"  ❌ VL_PL cota ({vl_pl_cota:,.2f}) ≠ PL fechamento ({pl_ultimo_fechamento:,.2f})")
        ok = False
    else:
        print(f"  ✅ VL_PL cota ≈ PL fechamento")

    if abs(vl_cota * qt_cotas - vl_pl_cota) > 1.0:
        print(f"  ❌ Cota × QT_COTAS ({vl_cota * qt_cotas:,.2f}) ≠ VL_PL ({vl_pl_cota:,.2f})")
        ok = False
    else:
        print(f"  ✅ Cota × QT_COTAS ≈ VL_PL")

    # 4) Soma PL cotistas ≈ PL do fundo
    if cotistas:
        soma_pl_cotistas = sum(float(c.get("VL_PL_COTISTA") or 0) for c in cotistas)
        print(f"  Soma PL cotistas:                      {soma_pl_cotistas:,.2f}")
        if abs(soma_pl_cotistas - vl_pl_cota) > 1.0:
            print(f"  ❌ Soma PL cotistas ({soma_pl_cotistas:,.2f}) ≠ PL fundo ({vl_pl_cota:,.2f})")
            ok = False
        else:
            print(f"  ✅ Soma PL cotistas ≈ PL fundo")

    # 5) Série PL do gráfico (pnl_fechamento) vs série PL das cotas
    # Para o último dia, devem convergir
    pnl_last_dt = pnl_items[-1]["DT_REFERENCIA"]
    cota_last_dt = cota_items[-1]["DT_REFERENCIA"]
    if pnl_last_dt == cota_last_dt:
        pl_grafico = float(pnl_items[-1]["VL_VALOR_MERCADO_TOTAL"] or 0)
        if abs(pl_grafico - vl_pl_cota) > 1.0:
            print(f"  ❌ PL gráfico ({pl_grafico:,.2f}) ≠ PL cota ({vl_pl_cota:,.2f})")
            ok = False
        else:
            print(f"  ✅ PL gráfico ≈ PL cota (mesma data)")

    return ok


def main():
    # Lista fundos ativos
    r = requests.get(f"{BASE}/fundos")
    r.raise_for_status()
    fundos = r.json()["data"].get("items", [])
    if not fundos:
        print("Nenhum fundo encontrado.")
        return

    print(f"Encontrados {len(fundos)} fundo(s). Verificando consistência...\n")
    all_ok = True
    for f in fundos:
        fundo_id = f["ID_FUNDO"]
        fundo_ok = check_fundo_consistency(fundo_id)
        if not fundo_ok:
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("✅ Todos os fundos CONSISTENTES!")
    else:
        print("❌ Há inconsistências. Revise os valores acima.")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
