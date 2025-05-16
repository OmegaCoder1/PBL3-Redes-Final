import os
from flask import send_from_directory
from werkzeug.utils import secure_filename
import uuid

class AudioFile:
    def __init__(self):
        self.upload_folder = 'temp_audio'
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

    def save_file(self, file):
        """Salva o arquivo de áudio e retorna o nome do arquivo"""
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(self.upload_folder, filename)
        file.save(filepath)
        return filename

    def get_file(self, filename):
        """Retorna o arquivo de áudio"""
        return send_from_directory(self.upload_folder, filename)

    def delete_file(self, filename):
        """Deleta o arquivo de áudio"""
        filepath = os.path.join(self.upload_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False 