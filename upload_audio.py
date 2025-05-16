from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = 'temp_audio'
ALLOWED_EXTENSIONS = {'wav'}
MAX_FILE_AGE = 3600  # 1 hora em segundos

# Criar pasta de upload se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Remove arquivos mais antigos que MAX_FILE_AGE"""
    while True:
        current_time = time.time()
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.getmtime(filepath) < current_time - MAX_FILE_AGE:
                try:
                    os.remove(filepath)
                    print(f"Arquivo removido: {filename}")
                except Exception as e:
                    print(f"Erro ao remover arquivo {filename}: {str(e)}")
        time.sleep(300)  # Verifica a cada 5 minutos

# Iniciar thread de limpeza
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400
    
    try:
        # Gerar nome único para o arquivo
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salvar arquivo
        file.save(filepath)
        
        # Gerar URL para o arquivo
        file_url = f"http://145.223.27.42:7025/audio/{filename}"
        
        return jsonify({
            "status": "success",
            "url": file_url,
            "message": "Arquivo de áudio enviado com sucesso"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Erro ao processar arquivo: {str(e)}"
        }), 500

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({
            "error": f"Erro ao recuperar arquivo: {str(e)}"
        }), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7025) 