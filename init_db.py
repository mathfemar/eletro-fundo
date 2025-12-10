"""
Script para inicializar o banco de dados
"""
import logging
import sys
from sqlalchemy import text

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Inicializar banco de dados"""
    logger.info("Iniciando setup do banco de dados...")
    
    try:
        # Importar connection para testar conexão
        from database.connection import engine, create_all_tables
        
        # Testar conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Conexão com PostgreSQL OK")
        
        # Criar tabelas
        create_all_tables()
        
        logger.info("✓ Setup do banco de dados concluído com sucesso!")
        print("\n✓ Setup do banco de dados concluído com sucesso!")
        return 0
        
    except Exception as e:
        logger.error(f"✗ Erro durante setup: {e}", exc_info=True)
        print(f"\n✗ Erro durante setup: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
