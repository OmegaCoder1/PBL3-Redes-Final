import requests
import json
from datetime import datetime

# Configurações
API_URL = "http://localhost:3333/send-message"
TEST_NUMBER = "557581755486"  # Número com código do Brasil (55)

def print_response(response):
    """Função para imprimir a resposta de forma organizada"""
    print("\n=== RESPOSTA ===")
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print("Body:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print("=" * 50)

def test_text_message():
    """Testa envio de mensagem de texto"""
    print("\n=== TESTANDO MENSAGEM DE TEXTO ===")
    
    payload = {
        "number": TEST_NUMBER,
        "message": f"Teste de mensagem de texto - {datetime.now().strftime('%H:%M:%S')}",
        "type": "text"
    }
    
    print("Enviando payload:", json.dumps(payload, indent=2, ensure_ascii=False))
    response = requests.post(API_URL, json=payload)
    print_response(response)

def test_image_message():
    """Testa envio de mensagem com imagem"""
    print("\n=== TESTANDO MENSAGEM COM IMAGEM ===")
    
    payload = {
        "number": TEST_NUMBER,
        "message": "http://localhost:3333/test-image.png",  # URL local da imagem
        "type": "image",
        "caption": f"Teste de imagem - {datetime.now().strftime('%H:%M:%S')}"
    }
    
    print("Enviando payload:", json.dumps(payload, indent=2, ensure_ascii=False))
    response = requests.post(API_URL, json=payload)
    print_response(response)

def test_audio_message():
    """Testa envio de mensagem com áudio"""
    print("\n=== TESTANDO MENSAGEM COM ÁUDIO ===")
    
    payload = {
        "number": TEST_NUMBER,
        "message": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",  # URL de áudio mais confiável
        "type": "audio"
    }
    
    print("Enviando payload:", json.dumps(payload, indent=2, ensure_ascii=False))
    response = requests.post(API_URL, json=payload)
    print_response(response)

def test_invalid_number():
    """Testa envio com número inválido"""
    print("\n=== TESTANDO NÚMERO INVÁLIDO ===")
    
    payload = {
        "number": "123",  # Número inválido
        "message": "Teste de número inválido",
        "type": "text"
    }
    
    print("Enviando payload:", json.dumps(payload, indent=2, ensure_ascii=False))
    response = requests.post(API_URL, json=payload)
    print_response(response)

def test_invalid_type():
    """Testa envio com tipo inválido"""
    print("\n=== TESTANDO TIPO INVÁLIDO ===")
    
    payload = {
        "number": TEST_NUMBER,
        "message": "Teste de tipo inválido",
        "type": "invalid_type"
    }
    
    print("Enviando payload:", json.dumps(payload, indent=2, ensure_ascii=False))
    response = requests.post(API_URL, json=payload)
    print_response(response)

def main():
    """Função principal que executa todos os testes"""
    print("=== INICIANDO TESTES DE ENVIO DE MENSAGENS ===")
    print(f"API URL: {API_URL}")
    print(f"Número de teste: {TEST_NUMBER}")
    print("=" * 50)
    
    try:
        # Testa mensagem de texto
        test_text_message()
        
        # Testa mensagem com imagem
        test_image_message()
        
        # Testa mensagem com áudio
        test_audio_message()
        
        # Testa número inválido
        test_invalid_number()
        
        # Testa tipo inválido
        test_invalid_type()
        
    except requests.exceptions.ConnectionError:
        print("\nERRO: Não foi possível conectar ao servidor.")
        print("Verifique se o bot.js está rodando na porta 3333.")
    except Exception as e:
        print(f"\nERRO: {str(e)}")

if __name__ == "__main__":
    main() 