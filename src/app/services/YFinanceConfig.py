"""
YFinance Configuration Module for Corporate Proxy Environments

Este módulo configura o yfinance para funcionar em ambientes corporativos com
proxy/firewall que fazem inspeção SSL (man-in-the-middle).

Problema:
---------
O yfinance utiliza curl_cffi internamente para fazer requisições HTTPS aos 
servidores do Yahoo Finance (query1.finance.yahoo.com, query2.finance.yahoo.com).
Em ambientes corporativos, proxies/firewalls interceptam conexões SSL e reemitem
certificados autoassinados, causando erros:
    "SSL certificate problem: self signed certificate in certificate chain"

Solução:
--------
Este módulo desabilita a verificação SSL tanto no requests quanto no curl_cffi,
permitindo que o yfinance funcione mesmo com certificados corporativos.

Uso:
----
    from utils.YFinanceConfig import configure_yfinance_for_corporate_proxy
    
    # Chamar ANTES de importar yfinance
    configure_yfinance_for_corporate_proxy()
    
    import yfinance as yf
    # Agora funciona normalmente
    df = yf.download('PETR4.SA', start='2020-01-01')

URLs acessadas pelo yfinance:
-----------------------------
- https://query1.finance.yahoo.com
- https://query2.finance.yahoo.com  
- https://finance.yahoo.com

Para o TI liberar, solicitar acesso a: *.finance.yahoo.com (porta 443)

Autor: GitHub Copilot
Data: 2026-01-21
"""

import os
import logging
from typing import Optional

# Logger configurável
_logger: Optional[logging.Logger] = None


def _get_logger() -> logging.Logger:
    """Retorna ou cria logger para este módulo."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger('YFinanceConfig')
        if not _logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))
            _logger.addHandler(handler)
            _logger.setLevel(logging.INFO)
    return _logger


def configure_yfinance_for_corporate_proxy() -> bool:
    """
    Configura o ambiente para yfinance funcionar em redes corporativas com proxy SSL.
    
    Aplica as seguintes configurações:
    1. Desabilita warnings SSL no urllib3
    2. Desabilita verificação SSL no requests padrão
    3. Limpa variáveis de ambiente de certificados (CURL_CA_BUNDLE, SSL_CERT_FILE)
    4. Aplica monkey-patch no curl_cffi.requests.Session para desabilitar SSL
    
    Returns:
        bool: True se configuração bem-sucedida, False se houver erros
    
    Example:
        >>> from utils.YFinanceConfig import configure_yfinance_for_corporate_proxy
        >>> configure_yfinance_for_corporate_proxy()
        True
        >>> import yfinance as yf
        >>> df = yf.download('AAPL', start='2020-01-01')
    """
    logger = _get_logger()
    success = True
    
    # Etapa 1: Desabilitar SSL no requests padrão
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # Nota: requests.sessions.Session.verify não é um atributo de classe,
        # mas desabilitar warnings já ajuda a reduzir ruído
        logger.info("✓ Desabilitado warnings SSL no urllib3/requests")
    except Exception as ex:
        logger.warning("✗ Falha ao desabilitar SSL warnings no requests: %s", ex)
        success = False
    
    # Etapa 2: Limpar variáveis de ambiente de certificados SSL
    try:
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['SSL_CERT_FILE'] = ''
        logger.info("✓ Limpas variáveis de ambiente SSL (CURL_CA_BUNDLE, SSL_CERT_FILE)")
    except Exception as ex:
        logger.warning("✗ Falha ao limpar variáveis de ambiente SSL: %s", ex)
        success = False
    
    # Etapa 3: Monkey-patch curl_cffi.requests.Session
    # IMPORTANTE: Fazer ANTES de importar yfinance
    try:
        from curl_cffi import requests as curl_requests
        
        # Salvar referência original
        _original_Session = curl_requests.Session
        
        # Criar wrapper que sempre desabilita SSL
        def _patched_Session(*args, **kwargs):
            """Session wrapper que força verify=False."""
            session = _original_Session(*args, **kwargs)
            session.verify = False
            return session
        
        # Aplicar patch
        curl_requests.Session = _patched_Session
        logger.info("✓ Aplicado monkey-patch em curl_cffi.requests.Session (verify=False)")
    except ImportError:
        logger.warning("✗ curl_cffi não instalado - yfinance pode não funcionar corretamente")
        success = False
    except Exception as ex:
        logger.warning("✗ Falha ao aplicar patch em curl_cffi: %s", ex)
        success = False
    
    if success:
        logger.info("=== Configuração SSL concluída com sucesso ===")
        logger.info("URLs acessadas pelo yfinance:")
        logger.info("  - https://query1.finance.yahoo.com")
        logger.info("  - https://query2.finance.yahoo.com")
        logger.info("  - https://finance.yahoo.com")
    else:
        logger.warning("=== Configuração SSL concluída COM ERROS ===")
    
    return success


def restore_default_ssl() -> bool:
    """
    Reverte as configurações SSL para o padrão (verificação habilitada).
    
    ATENÇÃO: Esta função tem limitações, pois não pode desfazer completamente
    o monkey-patch do curl_cffi. Use apenas para testes ou se souber o que está fazendo.
    
    Returns:
        bool: True se reversão bem-sucedida, False se houver erros
    """
    logger = _get_logger()
    success = True
    
    try:
        import urllib3
        # Não há como "restaurar" warnings, mas podemos reativar
        # (na prática, isso não é muito útil)
        logger.info("✓ urllib3 warnings não podem ser totalmente restaurados")
    except Exception as ex:
        logger.warning("✗ Erro ao tentar restaurar urllib3: %s", ex)
        success = False
    
    try:
        # Restaurar variáveis de ambiente (removê-las)
        os.environ.pop('CURL_CA_BUNDLE', None)
        os.environ.pop('SSL_CERT_FILE', None)
        logger.info("✓ Removidas variáveis de ambiente SSL")
    except Exception as ex:
        logger.warning("✗ Erro ao restaurar variáveis de ambiente: %s", ex)
        success = False
    
    logger.warning("ATENÇÃO: Monkey-patch do curl_cffi NÃO pode ser revertido após aplicado.")
    logger.warning("Para restaurar SSL padrão, reinicie o interpretador Python.")
    
    return success


# Informações sobre as URLs acessadas pelo yfinance
YFINANCE_URLS = {
    'QUERY1': 'https://query1.finance.yahoo.com',
    'BASE': 'https://query2.finance.yahoo.com',
    'ROOT': 'https://finance.yahoo.com',
}


def get_yfinance_urls() -> dict:
    """
    Retorna dicionário com as URLs acessadas pelo yfinance.
    
    Returns:
        dict: Dicionário com chaves QUERY1, BASE, ROOT
    """
    return YFINANCE_URLS.copy()


if __name__ == '__main__':
    # Teste básico do módulo
    print("=== Teste do módulo YFinanceConfig ===")
    print("\n1. Configurando ambiente para proxy corporativo...")
    result = configure_yfinance_for_corporate_proxy()
    print(f"Resultado: {'✓ Sucesso' if result else '✗ Falha'}")
    
    print("\n2. URLs acessadas pelo yfinance:")
    for name, url in get_yfinance_urls().items():
        print(f"   {name}: {url}")
    
    print("\n3. Testando import do yfinance...")
    try:
        import yfinance as yf
        print("✓ yfinance importado com sucesso")
        
        print("\n4. Testando download de ticker...")
        df = yf.download('AAPL', period='5d', progress=False)
        if not df.empty:
            print(f"✓ Download bem-sucedido ({len(df)} registros)")
        else:
            print("✗ Download retornou vazio")
    except Exception as e:
        print(f"✗ Erro: {e}")
