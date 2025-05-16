import asyncio
from Controllers.webhook_controller import app
import threading
import logging
#from cache_manager import assistant_cache  # Importa o cache já inicializado

# Configure o logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def start_webhook():
    """Inicia o servidor Flask para o webhook."""
    logging.debug("Iniciando o servidor Flask para o webhook...")
    app.run(host="0.0.0.0", port=7025, debug=False)  # Defina debug=False aqui

if __name__ == "__main__":
    print("Iniciando o arquivo main.py")
    import time
    # Inicia o servidor Flask
    start_webhook()
 