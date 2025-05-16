from utils.audio_handler import save_audio_file, get_audio_file, delete_audio_file
from werkzeug.utils import secure_filename
import uuid




import traceback
import whisper
import tempfile
from pydub import AudioSegment
import io
import random
import requests
import json
import os
import base64
from flask import Flask, request, jsonify,send_from_directory,Blueprint
from Controllers.whatsapp_controller import generate_message
from Controllers.baserow_controller import get_all_data_by_telegram_id2, update_transaction_dataController
from Controllers.payment_pixup_controller import create_payment
from Services.zapster_send_message_serice import send_message_zapster
from Models.BaseRowModel import create_new_row_nome
import logging
from datetime import datetime
import time
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_client import Counter, Histogram, start_http_server
from tenacity import retry, stop_after_attempt, wait_exponential
from queue import Queue
import threading
from functools import lru_cache, wraps
import signal
from contextlib import contextmanager
import psutil
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

# Lista de elogios para fotos
ELOGIOS_FOTOS = [
    "Nossa, que homem gostoso! 😍",
    "Aff, eu caso com você viu! 💍",
    "Que delícia de foto! Meu tipo! 😘",
    "Caraca, você é muito gato! 🔥",
    "Nossa, que homem lindo! Me apaixonei! 💕",
    "Que gostoso! Meu tipo de homem! 😏",
    "Aff, você é muito lindo! Me conquistou! 💋",
    "Que homem maravilhoso! Meu coração disparou! ❤️",
    "Nossa, que gato! Meu tipo ideal! 😍",
    "Que homem gostoso! Me apaixonei! 💘"
]

# Caminho do arquivo de buffer
BUFFER_FILE = "/home/saladadefruta777/htdocs/www.saladadefruta777.online/buffermessage_buffer.json"

# Constantes
URLSend = "https://api.conta.ativopay.com/v1/transactions"
SECRET_KEY = "sk_live_cT84hUkBIj6oYpNWuax7IaXrHgzQif0fXsTB0TmpQf"

# Codificando a chave secreta no padrão Basic Access Authentication
auth_token = base64.b64encode(f"{SECRET_KEY}:x".encode()).decode()

# Cabeçalhos da requisição
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Basic {auth_token}"
}

# Informações do cliente
client = {
    "name": "AMANDA SILVA OLIVEIRA",
    "email": "cliente232@gmail.com",
    "document": {
        "number": "60501304347",
        "type": "cpf"
    },
    "phone": "11983541548"
}

# Item fixo para o pagamento
item = {
    "title": "Pagamento WhatsApp",
    "unitPrice": 2000,  # Valor padrão
    "quantity": 1,
    "tangible": True
}

app = Flask(__name__)
CORS(app)

# Configuração de logging
logging.basicConfig(
    filename='/var/log/telegram_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Métricas Prometheus
messages_received = Counter('messages_received_total', 'Total messages received')
processing_time = Histogram('message_processing_seconds', 'Time spent processing messages')
error_count = Counter('processing_errors_total', 'Total processing errors')

# Fila de mensagens para processamento
message_queue = Queue()
executor = ThreadPoolExecutor(max_workers=10)

# Cache de usuários
@lru_cache(maxsize=1000)
def get_cached_user_data(number_whatsapp, table_name):
    return get_all_data_by_telegram_id2(number_whatsapp, table_name)

# Retry decorator para envio de mensagens
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_message_with_retry(number, message):
    return send_message_zapster(number, message)

# Processamento assíncrono da fila
def process_message_queue():
    while True:
        try:
            data = message_queue.get()
            executor.submit(process_single_message, data)
            message_queue.task_done()
        except Exception as e:
            logging.error(f"Error processing message queue: {str(e)}")

# Inicia o processamento da fila em uma thread separada
threading.Thread(target=process_message_queue, daemon=True).start()

# Tenta iniciar o servidor de métricas em uma porta diferente
try:
    start_http_server(8001)  # Usando porta 8001
    logging.info("Servidor de métricas iniciado na porta 8001")
except OSError as e:
    logging.warning(f"Não foi possível iniciar o servidor de métricas: {str(e)}")
    logging.warning("As métricas não estarão disponíveis, mas o serviço continuará funcionando normalmente")

# Configuração do rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'queue_size': message_queue.qsize(),
        'active_threads': threading.active_count(),
        'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024  # MB
    })

# Função para carregar o buffer do arquivo
def load_buffer(BUFFER_FILEE):
    print('chamou a load_buffer:')
    print(BUFFER_FILEE)
    if os.path.exists(BUFFER_FILEE):
        try:
            with open(BUFFER_FILEE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"deu erro")
            return {}  # Retorna um buffer vazio se o JSON estiver corrompido
    return {}

# Função para salvar o buffer no arquivo
def save_buffer(buffer,BUFFER_FILEE):
    with open(BUFFER_FILEE, "w") as f:
        json.dump(buffer, f)

# Função para formatar o número de telefone
def format_phone_number(phone_number):
    # Verifica se o número começa com '55' (código do Brasil)
    if phone_number.startswith('55'):
        # Se o número tiver 10 dígitos (sem o 9), adiciona o 9 após o DDD
        if len(phone_number) == 12:  # 12 caracteres: 55 + 2 digitos do DDD + 8 dígitos do número
            phone_number = phone_number[:4] + '9' + phone_number[4:]
        # Se o número já tiver 11 dígitos, ele está correto
        elif len(phone_number) != 13:  # 13 caracteres: 55 + 2 digitos do DDD + 9 dígitos do número
            print(f"Erro: número com formato inválido: {phone_number}")
    return phone_number  # Retorna o número formatado (mesmo que inválido)

def async_task(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

async def process_image_message(number_whatsapp):
    """Processa mensagem de imagem de forma assíncrona"""
    try:
        # Espera 1 minuto antes de enviar o elogio
        await asyncio.sleep(60)
        
        # Escolhe um elogio aleatório
        elogio = random.choice(ELOGIOS_FOTOS)
        
        # Envia o elogio
        send_message_zapster(number_whatsapp, elogio)
        print(f"Elogio enviado: {elogio}")
        
    except Exception as e:
        print(f"Erro ao processar imagem: {str(e)}")
        raise e

def validate_message_data(received_data):
    """Valida os dados da mensagem recebida"""
    if not isinstance(received_data, dict):
        raise ValueError("Expected a dictionary as input")

    data = received_data.get("data", {})
    if not isinstance(data, dict):
        try:
            data = dict(data)
        except Exception as e:
            raise ValueError(str(e))
    
    return data

def format_message_ids(data):
    """Formata os IDs de sender e recipient"""
    if "sender" in data and "id" in data["sender"]:
        data["sender"]["id"] = format_phone_number(data["sender"]["id"])

    if "recipient" in data and "id" in data["recipient"]:
        data["recipient"]["id"] = format_phone_number(data["recipient"]["id"])
    
    return data

def update_buffer(sender_id, data, message_text, received_data):
    """Atualiza o buffer com a nova mensagem"""
    buffer = load_buffer(BUFFER_FILE)
    if isinstance(buffer, list):
        buffer = {}

    created_at = received_data.get("created_at", datetime.utcnow().isoformat())

    if sender_id in buffer:
        buffer[sender_id]["content"]["text"] += f" {message_text}"
    else:
        buffer[sender_id] = {
            "sender": data["sender"],
            "recipient": data["recipient"],
            "content": {"text": message_text},
            "created_at": created_at,
            "x-instance-id": received_data.get("x-instance-id", ""),
            "x-instance-phonenumber": received_data.get("x-instance-phonenumber", ""),
            "ID": received_data.get("id", "")
        }
    
    location_buffer = "/home/saladadefruta777/htdocs/www.saladadefruta777.online/buffermessage_buffer.json"
    save_buffer(buffer, location_buffer)

# Conjunto para armazenar IDs de mensagens já processadas
processed_messages = set()

# Função para processar uma única mensagem
def process_single_message(data):
    try:
        # Processa a mensagem
        message_create = generate_message(data)
        logging.info(f"Message processed successfully: {message_create}")
            
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")

@app.route('/webhook', methods=['POST'])
@limiter.limit("10 per second")
def webhook():
    messages_received.inc()
    with processing_time.time():
        print('ENTROU NO POST DO /WEBHOOK')
        try:
            # Recebe os dados do corpo da requisição
            data = request.get_json()

            if data:
                # Log dos dados recebidos
                logging.info(f"Data received: {json.dumps(data)}")

                # Adiciona à fila para processamento assíncrono
                message_queue.put(data)
                
                return jsonify({
                    'status': 'success',
                    'message': 'Message queued for processing'
                }), 202

            else:
                return jsonify({
                    'status': 'error',
                    'message': 'No JSON data received.'
                }), 400
        except Exception as e:
            error_count.inc()
            logging.error(f"Error receiving data: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to process the data.'
            }), 500

@app.route("/buffer", methods=["POST"])
def receive_messages():
    try:
        # Dados recebidos no corpo da requisição
        received_data = request.get_json()
        print(f"valor do: received_data {received_data}")
        
        # Verifica se é uma mensagem duplicada
        message_id = received_data.get("id")
        if message_id:
            if message_id in processed_messages:
                print(f"Mensagem duplicada ignorada: {message_id}")
                return jsonify({"status": "success", "message": "Duplicate message ignored"}), 200
            processed_messages.add(message_id)
            if len(processed_messages) > 1000:
                processed_messages.clear()
        
        print(f"buffer foi chamado")

        # Validação inicial dos dados
        data = validate_message_data(received_data)

        # Verifica se é mensagem de grupo
        recipient = data.get("recipient", {})
        if recipient.get("type") == "group":
            print("Mensagem de grupo ignorada")
            return jsonify({"status": "success", "message": "Group message ignored"}), 200

        # Verificar o tipo da mensagem
        message_type = data.get("type")
        
        if message_type == "sticker":
            print("Mensagem de sticker ignorada")
            return jsonify({"status": "success", "message": "sticker message ignored"}), 200
        
        # Processamento de imagem de forma assíncrona
        if message_type == "image":
            try:
                print("Processando mensagem de imagem...")
                number_whatsapp = format_phone_number(data.get("sender", {}).get("id", ""))
                
                # Inicia o processamento assíncrono
                executor.submit(asyncio.run, process_image_message(number_whatsapp))
                
                return jsonify({"status": "success", "message": "Image processing started"}), 200
                
            except Exception as e:
                print(f"Erro ao processar imagem: {str(e)}")
                return jsonify({"status": "error", "message": f"Erro ao processar imagem: {str(e)}"}), 400

        # Processamento de áudio
        if message_type == "audio":
            try:
                print("Processando mensagem de áudio com Whisper...")
                print("Obtendo URL do áudio...")
                audio_url = data["content"]["media"]["url"]
                print(f"URL do áudio: {audio_url}")
                
                # Baixa o áudio
                print("Baixando áudio...")
                audio_response = requests.get(audio_url)
                if audio_response.status_code != 200:
                    raise Exception(f"Falha ao baixar áudio. Status code: {audio_response.status_code}")
                print("Áudio baixado com sucesso")
                
                # Converte o áudio usando pydub
                print("Convertendo áudio...")
                try:
                    audio_bytes = io.BytesIO(audio_response.content)
                    audio = AudioSegment.from_file(audio_bytes)
                    print("Áudio convertido com sucesso")
                except Exception as e:
                    raise Exception(f"Erro ao converter áudio: {str(e)}")
                
                # Normaliza o áudio para melhor qualidade
                print("Normalizando áudio...")
                audio = audio.normalize()
                print(f"Nível de áudio após normalização: {audio.dBFS}dB")
                
                # Ajusta o volume se necessário
                if audio.dBFS < -20:
                    print("Ajustando volume do áudio...")
                    audio = audio + 10  # Aumenta o volume em 10dB
                    print(f"Novo nível de áudio: {audio.dBFS}dB")
                
                # Cria arquivo temporário WAV com configurações otimizadas
                print("Criando arquivo WAV temporário...")
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                    audio.export(
                        temp_wav.name,
                        format='wav',
                        parameters=["-ar", "16000", "-ac", "1"]  # 16kHz, mono
                    )
                    temp_wav_path = temp_wav.name
                    print(f"Arquivo WAV criado em: {temp_wav_path}")
                
                try:
                    # Carrega o modelo Whisper
                    print("Carregando modelo Whisper...")
                    model = whisper.load_model("base")  # Usando base para teste
                    print("Modelo Whisper carregado com sucesso")
                    
                    # Configurações otimizadas para transcrição
                    print("Configurando parâmetros de transcrição...")
                    options = {
                        "language": "pt",
                        "task": "transcribe",
                        "temperature": 0.2,
                        "best_of": 5,
                        "beam_size": 5,
                        "patience": 2.0,
                        "condition_on_previous_text": True,
                        "initial_prompt": "Transcrição de áudio em português brasileiro. Foco em suplementos e produtos de academia."
                    }
                    
                    # Transcreve o áudio
                    print("Iniciando transcrição...")
                    result = model.transcribe(temp_wav_path, **options)
                    transcribed_text = result["text"].strip()
                    print(f"Transcrição concluída: {transcribed_text}")
                    
                    # Pós-processamento do texto
                    print("Aplicando pós-processamento...")
                    transcribed_text = transcribed_text.replace("grofe", "growth")
                    transcribed_text = transcribed_text.replace("whey", "whey")
                    transcribed_text = transcribed_text.replace("proteína", "proteína")
                    print(f"Texto após pós-processamento: {transcribed_text}")
                    
                    if transcribed_text:
                        # Atualiza o data com o texto transcrito
                        data["type"] = "text"
                        data["content"] = {"text": transcribed_text}
                        print(f"Áudio transcrito com sucesso: {transcribed_text}")
                    else:
                        raise Exception("Texto transcrito vazio")
                        
                except Exception as e:
                    print(f"Erro durante a transcrição: {str(e)}")
                    raise
                    
                finally:
                    # Limpa o arquivo temporário
                    print("Limpando arquivo temporário...")
                    try:
                        os.unlink(temp_wav_path)
                        print("Arquivo temporário removido com sucesso")
                    except Exception as e:
                        print(f"Erro ao remover arquivo temporário: {str(e)}")
                    
            except Exception as e:
                print(f"Erro ao processar áudio: {str(e)}")
                print(f"Traceback completo: {traceback.format_exc()}")
                number_whatsapp = format_phone_number(data.get("sender", {}).get("id", ""))
                send_message_zapster(number_whatsapp, "Desculpe, não consegui processar o áudio. Pode enviar em texto?")
                return jsonify({"status": "error", "message": f"Erro ao processar áudio: {str(e)}"}), 400

        # Formata IDs e valida campos necessários
        data = format_message_ids(data)

        if "sender" not in data or "content" not in data or "text" not in data["content"]:
            return jsonify({"status": "error", "message": "NAO ENCONTROU NENHUM TEXT NA MENSAGEM'"}), 400

        # Atualiza o buffer
        sender_id = data["sender"]["id"]
        message_text = data["content"]["text"]
        update_buffer(sender_id, data, message_text, received_data)

        return jsonify({"status": "success", "message": "Message added to buffer"}), 200

    except Exception as e:
        print(f"Erro geral na rota: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500 

@app.route('/create_payment_pixup', methods=['GET'])
def create_payment_route2():
    try:
        price = request.args.get('price', type=float)  # Obter o preço da query string
        if price is None:
            return jsonify({'message': 'Preço não fornecido.'}), 400

        # Atualiza o preço do item
        item = {'unitPrice': 0}  # Exemplo de item (substitua pela sua lógica real)
        item['unitPrice'] = int(price * 1)  # Converte para centavos

        # Criação do pagamento
        payment_data = create_payment(item['unitPrice'])

        return jsonify({'message': 'Transação criada com sucesso!', 'transaction': payment_data}), 200

    except ValueError as e:
        # Caso ocorra um erro na criação do pagamento, retorna a mensagem do erro
        return jsonify({'message': f'Erro ao criar transação: {str(e)}'}), 400

    except Exception as e:
        # Captura erros inesperados
        return jsonify({'message': f'Erro inesperado: {str(e)}'}), 500

@app.route('/createitem', methods=['POST'])
def createitem():
    try:
        data = request.get_json()
        table_name = data.get('table_name')
        item_data = data.get('data')

        if not table_name or not item_data:
            return jsonify({'message': 'Faltam parâmetros obrigatórios: table_name ou data'}), 400

        response = create_new_row_nome(item_data, table_name)

        # Se houver erro, retornar código 400 ou 500
        if "error" in response:
            return jsonify(response), 500 if response.get("status_code") == 500 else 400

        return jsonify(response), 200

    except Exception as e:
        print(f"❌ ERRO: {e}")
        return jsonify({'error': str(e)}), 500

#RETONRAR ALGUM DADO DO BD:
@app.route('/consult_item_baserow_all', methods=['GET'])
def consult_item_baserow_all():
    try:
        table_name = request.args.get('table_name')
        transaction_id = request.args.get('id')

        response = get_all_data_by_telegram_id2(transaction_id, table_name)

        # Se houver erro, retornar código 400 ou 500
        if "error" in response:
            return jsonify(response), 500 if response.get("status_code") == 500 else 400

        return jsonify(response), 200

    except Exception as e:
        print(f"❌ ERRO: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/payment', methods=['POST'])
def payment_webhook():
    try:
        webhook_data = request.get_json()
        logging.info(f"Webhook recebido: {webhook_data}")
        
        # Verifica se o pagamento foi confirmado
        if webhook_data['requestBody']['status'] != 'PAID':
            logging.warning(f"Pagamento não confirmado: {webhook_data['requestBody']}")
            return jsonify({
                'status': 'ignored',
                'message': 'Pagamento não confirmado'
            }), 200
            
        transaction_id = webhook_data['requestBody']['transactionId']
        table_name = "payments_good_pix"
        
        response = update_transaction_dataController(transaction_id, table_name)
        logging.info(f"Pagamento confirmado e processado: {transaction_id}")

        return jsonify({
            'status': 'success',
            'message': 'Webhook processado com sucesso',
            'data': response
        }), 200
        
    except Exception as e:
        logging.error(f"Erro ao processar webhook: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
        
        
        
############################### UPLOAD DE AUDIO ###############################        
        
# Rotas de áudio
@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    try:
        # Usa a função do audio_handler para salvar o arquivo
        filename = save_audio_file(file)
        print(f"Arquivo salvo com nome: {filename}")
        
        # Gera a URL para o arquivo
        file_url = f"http://145.223.27.42:7025/audio/{filename}"
        
        return jsonify({
            "status": "success",
            "url": file_url,
            "message": "Arquivo de áudio enviado com sucesso"
        }), 200
        
    except Exception as e:
        print(f"Erro ao processar arquivo: {str(e)}")
        return jsonify({"error": f"Erro ao processar arquivo: {str(e)}"}), 500

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    try:
        print(f"Tentando acessar arquivo: {filename}")
        
        # Caminho absoluto na VPS
        temp_dir = '/home/saladadefruta777/htdocs/www.saladadefruta777.online/temp_audio'
        filepath = os.path.join(temp_dir, filename)
        
        print(f"Diretório temp: {temp_dir}")
        print(f"Caminho completo do arquivo: {filepath}")
        
        # Verifica se o arquivo existe
        if not os.path.exists(filepath):
            print(f"Arquivo não encontrado em: {filepath}")
            return jsonify({"error": "Arquivo não encontrado"}), 404
            
        # Verifica se é um arquivo
        if not os.path.isfile(filepath):
            print(f"Caminho não é um arquivo: {filepath}")
            return jsonify({"error": "Caminho inválido"}), 400
            
        # Envia o arquivo usando o caminho absoluto
        return send_from_directory(
            directory=temp_dir,
            path=filename,
            as_attachment=False
        )
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {filename}")
        return jsonify({"error": "Arquivo não encontrado"}), 404
    except Exception as e:
        print(f"Erro ao servir arquivo de áudio: {str(e)}")
        print(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({"error": "Erro ao processar arquivo"}), 500
        
        
        
        

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7025, debug=False)
