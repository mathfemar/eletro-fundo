"""
Serviço de Mapeamento CUSIP para Yahoo Finance (YF).
Realiza a leitura dos CUSIPs da tabela DIM_ATIVO_MAPPING e busca na API de search do Yahoo Finance.
Se encontrar, insere O Ticker de volta na respectiva linha e preenche a coluna CD_YF.
"""

import time
import logging
import urllib.parse
import requests
import sys
import os

# Adiciona a raiz do projeto (dois níveis acima de app/services) ao sys.path
_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from app.services.db_connection import query, execute_many
from app.services.YFinanceConfig import configure_yfinance_for_corporate_proxy

logger = logging.getLogger("app.services.yfinance_mapping")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def search_ticker_by_cusip(cusip: str) -> str | None:
    """Busca o Ticker correspondente a um CUSIP usando o endpoint de search do Yahoo Finance."""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(cusip)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0'
    }
    
    try:
        # verify=False e a configuração YFinanceConfig ajudam em redes corporativas
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.status_code == 200:
            data = response.json()
            quotes = data.get('quotes', [])
            if quotes:
                # Pega o symbol correspondente ao primeiro resultado encontrado
                return quotes[0].get('symbol')
    except Exception as e:
        logger.error(f"Erro ao buscar CUSIP {cusip}: {e}")
        
    return None

def update_yf_tickers_from_cusip():
    """
    Executa a query solicitada, busca os CUSIPs na API e faz update (CD_YF) em lote.
    """
    # 1. Configura ambiente corporativo e limpa avisos de SSL se necessário
    configure_yfinance_for_corporate_proxy()
    
    logger.info("Buscando ativos no banco de dados...")
    
    # 2. Select principal conforme solicitado (adicionamos WHERE CD_YF IS NULL para não remapear à toa)
    sql_select = """
        SELECT dam.CD_ATIVO, dam.CD_CUSIP 
        FROM DIM_ATIVO_MAPPING dam 
        LEFT JOIN DIM_ATIVO da ON dam.Id_Ativo = da.Id_Ativo 
        LEFT JOIN DIM_TIPO_ATIVO dta ON dta.Id_Tipo_Ativo = da.Id_Tipo_Ativo 
        WHERE dam.CD_CUSIP IS NOT NULL 
          AND (dam.CD_YF IS NULL OR dam.CD_YF = '')
    """
    
    df_ativos = query(sql_select)
    
    if df_ativos.empty:
        logger.info("Nenhum ativo com CUSIP pendente de atualização encontrado.")
        return

    registros = df_ativos.to_dict('records')
    logger.info(f"Encontrados {len(registros)} CUSIPs para buscar no Yahoo Finance.")
    
    updates = []
    
    # 3. Interage com a API YF para cada CUSIP
    for row in registros:
        cd_ativo = row['CD_ATIVO']
        cusip = str(row['CD_CUSIP']).strip()
        
        ticker_yf = search_ticker_by_cusip(cusip)
        
        if ticker_yf:
            logger.info(f"[ENCONTRADO] CUSIP: {cusip} -> Ticker: {ticker_yf} (CD_ATIVO: {cd_ativo})")
            # A tupla precisa seguir a ordem do UPDATE: SET CD_YF = ?, WHERE CD_ATIVO = ?
            updates.append((ticker_yf, cd_ativo))
        else:
            logger.warning(f"[NÃO ENCONTRADO] Ticker para CUSIP: {cusip} (CD_ATIVO: {cd_ativo})")
            
        # Rate limit simples de 300ms para evitar trigger de limites corporativos ou do YF
        time.sleep(0.3)
        
        # Faz o update parcial a cada 100 registros encontrados
        if len(updates) >= 100:
            sql_update = """
                UPDATE DIM_ATIVO_MAPPING 
                SET CD_YF = ? 
                WHERE CD_ATIVO = ?
            """
            execute_many(sql_update, updates)
            logger.info(f">>> Lote parcial de {len(updates)} registros salvo no banco de dados.")
            updates.clear()
        
    # 4. Atualiza os dados restantes no fim do loop
    if updates:
        sql_update = """
            UPDATE DIM_ATIVO_MAPPING 
            SET CD_YF = ? 
            WHERE CD_ATIVO = ?
        """
        execute_many(sql_update, updates)
        logger.info(f">>> Último lote de {len(updates)} registros salvo no banco de dados.")

    logger.info("Operação concluída com sucesso.")

if __name__ == "__main__":
    update_yf_tickers_from_cusip()
