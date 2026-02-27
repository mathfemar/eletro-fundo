import sys
import os
caminho_abs = os.path.abspath(os.curdir)
sys.path.insert(0, caminho_abs)

from src.app.utils.db_connection import query
from datetime import datetime

def get_data_last_cota(data):
    query_str = f"""
        select DT_DATA_LAST_COTA
        from DIM_CALENDARIO_BZ
        where DT_DATA = '{data}'
    """
    result = query(query_str).iloc[0]
    return result['DT_DATA_LAST_COTA']
    