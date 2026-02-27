import sqlite3
import sys
try:
    c = sqlite3.connect('src/infra/database/fundinho.db').cursor()
    c.execute("SELECT DT_REFERENCIA, VL_COTA, CD_METODO FROM FAT_FUNDO_COTA_DIARIA WHERE ID_FUNDO=18 ORDER BY DT_REFERENCIA ASC LIMIT 3")
    print(c.fetchall())
except Exception as e:
    print(e)
