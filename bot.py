from flask import Flask, jsonify, send_file, render_template_string
from flask_socketio import SocketIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import qrcode
import time
import base64
from io import BytesIO
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Variável para controlar o estado da conexão
is_connected = False
current_qr = None
driver = None

# HTML template para a página
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>WhatsApp Bot</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background-color: #f0f2f5;
        }
        .container {
            text-align: center;
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .status {
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .connected {
            background-color: #dcf8c6;
            color: #075e54;
        }
        .disconnected {
            background-color: #ffebee;
            color: #c62828;
        }
        #qrcode {
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WhatsApp Bot</h1>
        <div id="status" class="status disconnected">
            Aguardando conexão...
        </div>
        <div id="qrcode"></div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/qrcode@1.4.4/build/qrcode.min.js"></script>
    <script>
        const socket = io();
        const statusDiv = document.getElementById('status');
        const qrcodeDiv = document.getElementById('qrcode');

        socket.on('qr', (qr) => {
            qrcodeDiv.innerHTML = '';
            QRCode.toCanvas(qrcodeDiv, qr, function (error) {
                if (error) console.error(error);
            });
            statusDiv.textContent = 'Escaneie o QR Code com seu WhatsApp';
            statusDiv.className = 'status disconnected';
        });

        socket.on('ready', () => {
            qrcodeDiv.innerHTML = '';
            statusDiv.textContent = 'Conectado!';
            statusDiv.className = 'status connected';
        });

        socket.on('disconnected', () => {
            statusDiv.textContent = 'Desconectado. Aguardando nova conexão...';
            statusDiv.className = 'status disconnected';
        });
    </script>
</body>
</html>
'''

def init_chrome():
    global driver
    try:
        print("Inicializando Chrome...")
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.binary_location = 'C://Program Files//Google//Chrome//Application//chrome.exe'

        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Chrome inicializado com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao inicializar Chrome: {str(e)}")
        return False

def connect_to_whatsapp():
    global is_connected, current_qr
    try:
        print("Iniciando conexão com WhatsApp Web...")
        driver.get('https://web.whatsapp.com')
        
        print("Aguardando QR code...")
        qr_element = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'canvas'))
        )
        
        qr_data = qr_element.get_attribute('data-ref')
        current_qr = qr_data
        
        socketio.emit('qr', qr_data)
        print("QR code gerado! Escaneie com seu WhatsApp")
        
        print("Aguardando conexão...")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]'))
        )
        
        is_connected = True
        socketio.emit('ready')
        print('Conectado com sucesso!')
        
    except Exception as e:
        print(f'Erro ao conectar: {str(e)}')
        is_connected = False
        socketio.emit('disconnected')

@app.route('/status')
def status():
    return jsonify({'isConnected': is_connected})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def check_new_messages():
    last_messages = set()
    
    while True:
        if is_connected and driver:
            try:
                messages = driver.find_elements(By.CSS_SELECTOR, '[data-testid="msg-container"]')
                
                for message in messages:
                    if not message.get_attribute('data-is-outgoing'):
                        text = message.find_element(By.CSS_SELECTOR, '[data-testid="msg-text"]').text
                        
                        try:
                            sender = message.find_element(By.CSS_SELECTOR, '[data-testid="msg-meta"]').text
                        except:
                            sender = "Desconhecido"
                            
                        message_id = f"{sender}_{text}"
                        
                        if message_id not in last_messages:
                            print(f"\nNova mensagem recebida:")
                            print(f"De: {sender}")
                            print(f"Mensagem: {text}")
                            print("-" * 50)
                            
                            last_messages.add(message_id)
                            
                            if len(last_messages) > 100:
                                last_messages.clear()
                
            except Exception as e:
                print(f'Erro ao verificar mensagens: {str(e)}')
        time.sleep(1)

def start_whatsapp():
    if init_chrome():
        connect_to_whatsapp()

if __name__ == '__main__':
    # Iniciar thread para verificar mensagens
    message_thread = threading.Thread(target=check_new_messages)
    message_thread.daemon = True
    message_thread.start()
    
    # Iniciar thread para WhatsApp
    whatsapp_thread = threading.Thread(target=start_whatsapp)
    whatsapp_thread.daemon = True
    whatsapp_thread.start()
    
    # Iniciar servidor Flask
    print("Iniciando servidor Flask...")
    socketio.run(app, host='0.0.0.0', port=3333, debug=False) 