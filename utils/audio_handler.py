import os
from werkzeug.utils import secure_filename
import uuid
import time
import threading

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

def save_audio_file(file):
    """Salva o arquivo de áudio e retorna o nome do arquivo"""
    if not allowed_file(file.filename):
        raise ValueError("Tipo de arquivo não permitido")
        
    filename = f"{uuid.uuid4()}.wav"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filename

def get_audio_file(filename):
    """Retorna o caminho do arquivo de áudio"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return filepath
    raise FileNotFoundError(f"Arquivo {filename} não encontrado")

def delete_audio_file(filename):
    """Deleta o arquivo de áudio"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False 