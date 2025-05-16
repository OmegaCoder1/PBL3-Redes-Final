# Zapster API

API para integração com WhatsApp usando a biblioteca whatsapp-web.js.

## Descrição

Este projeto implementa uma API REST que permite:
- Receber mensagens do WhatsApp
- Enviar mensagens de texto, imagem e áudio
- Processar áudios usando Whisper
- Gerenciar pagamentos via PIX
- Integração com Baserow para armazenamento de dados

## Requisitos

- Python 3.8+
- Node.js 14+
- FFmpeg
- Chrome/Chromium

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/Zapster_api.git
cd Zapster_api
```

2. Instale as dependências Python:
```bash
pip install -r requirements.txt
```

3. Instale as dependências Node.js:
```bash
npm install
```

## Configuração

1. Configure as variáveis de ambiente no arquivo `.env`
2. Certifique-se que o Chrome/Chromium está instalado
3. Configure o FFmpeg no sistema

## Uso

1. Inicie o servidor:
```bash
python app.py
```

2. Acesse a API em `http://localhost:3333`

## Endpoints

- `POST /webhook`: Recebe mensagens do WhatsApp
- `POST /send-message`: Envia mensagens
- `POST /upload-audio`: Upload de áudios
- `GET /audio/{filename}`: Acessa áudios
- `POST /create_payment_pixup`: Cria pagamento PIX
- `POST /webhook/payment`: Webhook para pagamentos

## Licença

MIT 