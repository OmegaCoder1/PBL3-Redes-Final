const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');
const app = express();
const http = require('http');
const server = http.createServer(app);
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegInstaller = require('@ffmpeg-installer/ffmpeg');

app.use(express.json());
app.use(cors());

let isConnected = false;
const io = require('socket.io')(server, {
  cors: {
    origin: "*", 
    methods: ["GET", "POST"]
  }
});

const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: "sessions",
  }),
  puppeteer: {
    headless: false,
    executablePath: 'C://Program Files//Google//Chrome//Application//chrome.exe',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--no-first-run',
      '--no-zygote',
      '--disable-gpu',
      '--disable-extensions',
      '--disable-popup-blocking',
      '--disable-blink-features=AutomationControlled',
      '--window-size=1920,1080',
      '--start-maximized',
      '--disable-web-security',
      '--allow-running-insecure-content',
      '--disable-features=IsolateOrigins,site-per-process',
      '--disable-site-isolation-trials'
    ],
    defaultViewport: null,
    ignoreHTTPSErrors: true,
    timeout: 60000
  }
});

client.on('qr', (qr) => {
  isConnected = false;
  qrcode.generate(qr, { small: true });
  io.emit('qr', qr);
});

client.on('ready', () => {
  console.log('Client is ready!');
  isConnected = true;
  io.emit('ready');
});

// Configurar o caminho do FFmpeg
ffmpeg.setFfmpegPath(ffmpegInstaller.path);

// Configuração da pasta temp
const tempDir = path.join(__dirname, 'temp');

// Função para garantir que a pasta temp existe e tem permissões corretas
function ensureTempDir() {
  try {
    if (!fs.existsSync(tempDir)) {
      console.log('Criando pasta temp...');
      fs.mkdirSync(tempDir, { recursive: true, mode: 0o777 });
    }
    
    // Testa permissões de escrita
    const testFile = path.join(tempDir, 'test.txt');
    fs.writeFileSync(testFile, 'test');
    fs.unlinkSync(testFile);
    console.log('Permissões da pasta temp verificadas com sucesso');
  } catch (error) {
    console.error('Erro ao configurar pasta temp:', error.message);
    throw new Error(`Não foi possível configurar a pasta temp: ${error.message}`);
  }
}

// Chama a função de configuração ao iniciar
ensureTempDir();

// Função para converter áudio para WAV
async function convertToWav(inputPath, outputPath) {
  try {
    console.log('Caminho do FFmpeg:', ffmpegInstaller.path);
    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(inputPath)
        .inputFormat('ogg')
        .outputOptions([
          '-vn',
          '-acodec pcm_s16le',
          '-ar 16000',
          '-ac 1',
          '-f wav'
        ])
        .output(outputPath)
        .on('start', (commandLine) => {
          console.log('Comando FFmpeg:', commandLine);
        })
        .on('progress', (progress) => {
          console.log('Progresso:', progress);
        })
        .on('end', () => {
          const stats = fs.statSync(outputPath);
          if (stats.size === 0) {
            reject(new Error('Arquivo WAV está vazio'));
            return;
          }
          console.log('Conversão concluída com sucesso');
          resolve(outputPath);
        })
        .on('error', (err) => {
          console.error('Erro detalhado na conversão:', err);
          reject(err);
        })
        .run();
    });
  } catch (error) {
    console.error('Erro ao converter áudio:', error);
    throw error;
  }
}

client.on('message', async (message) => {
  console.log('\n=== NOVA MENSAGEM RECEBIDA ===');
  console.log('Tipo da mensagem:', message.type);
  console.log('De:', message.from);
  console.log('ID:', message.id._serialized || message.id);
  
  try {
    const contact = await message.getContact();
    const profilePicUrl = await contact.getProfilePicUrl();
    
    let audioUrl = null;
    let fileSize = 0;  // Inicializa com valor padrão
    
    if (message.type === 'ptt') {
      console.log('\n=== PROCESSANDO ÁUDIO ===');
      try {
        console.log('1. Baixando áudio do WhatsApp...');
        
        // Usando o método oficial para baixar e descriptografar o áudio
        const media = await message.downloadMedia();
        if (!media) {
          throw new Error('Falha ao baixar áudio');
        }

        console.log('Tipo do áudio:', media.mimetype);
        console.log('Tamanho do áudio:', media.data.length, 'bytes');

        // Salva o áudio descriptografado
        const audioPath = path.join(tempDir, `${message.id.id}.ogg`);
        fs.writeFileSync(audioPath, media.data, 'base64');
        
        // Verifica se o arquivo foi salvo corretamente
        const stats = fs.statSync(audioPath);
        console.log('Tamanho do arquivo salvo:', stats.size, 'bytes');
        
        if (stats.size === 0) {
          throw new Error('Arquivo de áudio está vazio');
        }
        
        console.log('\n2. Convertendo para WAV...');
        const wavPath = path.join(path.dirname(audioPath), `${message.id.id}.wav`);
        await convertToWav(audioPath, wavPath);
        
        // Verifica se o arquivo WAV foi criado
        const wavStats = fs.statSync(wavPath);
        console.log('Tamanho do arquivo WAV:', wavStats.size, 'bytes');
        
        if (wavStats.size === 0) {
          throw new Error('Arquivo WAV está vazio');
        }
        
        console.log('Áudio convertido em:', wavPath);
        
        // Atualiza o tamanho do arquivo
        fileSize = wavStats.size;
        
        console.log('\n3. Enviando para servidor de upload...');
        const formData = new FormData();
        formData.append('audio', fs.createReadStream(wavPath));
        
        const uploadResponse = await axios.post('http://145.223.27.42:7025/upload-audio', formData, {
          headers: {
            ...formData.getHeaders()
          }
        });
        console.log('Resposta do upload:', uploadResponse.data);
        
        audioUrl = uploadResponse.data.url;
        console.log('URL do áudio convertido:', audioUrl);
        
        console.log('\n4. Limpando arquivos temporários...');
        fs.unlinkSync(audioPath);
        fs.unlinkSync(wavPath);
        console.log('Arquivos temporários removidos');
      } catch (error) {
        console.error('\nERRO NO PROCESSAMENTO DO ÁUDIO:');
        console.error('Mensagem:', error.message);
        if (error.response) {
          console.error('Resposta do servidor:', error.response.data);
        }
      }
    }
    
    console.log('\n=== FORMATANDO MENSAGEM ===');
    const formattedMessage = {
      id: message.id._serialized || message.id,
      data: {
        id: message.id.id || message.id._serialized,
        type: message.type === 'ptt' ? 'audio' : message.type,
        sender: {
          id: message.from.split('@')[0],
          name: contact.pushname || contact.name || 'Unknown',
          profile_picture: profilePicUrl || 'https://zapsterapi.s3.us-east-1.amazonaws.com/instances/i-lb6ds8vva2b81agg18tgr/profile-pictures/default.jpg'
        },
        content: message.type === 'ptt' ? {
          media: {
            url: audioUrl,
            metadata: {
              ptt: true,
              ptv: false,
              duration: parseInt(message.duration) || 0,
              mime_type: 'audio/wav',
              format: 'wav',
              size: fileSize
            }
          },
          view_once: false
        } : {
          text: message.body || ''
        },
        sent_at: new Date().toISOString(),
        recipient: {
          id: message.from.split('@')[0],
          name: contact.pushname || contact.name || 'Unknown',
          type: message.isGroupMsg ? 'group' : 'chat',
          profile_picture: profilePicUrl || 'https://zapsterapi.s3.us-east-1.amazonaws.com/instances/i-lb6ds8vva2b81agg18tgr/profile-pictures/default.jpg'
        }
      },
      type: 'message.received',
      created_at: new Date().toISOString()
    };

    console.log('\n=== ENVIANDO PARA API /buffer ===');
    try {
      const response = await axios.post('http://145.223.27.42:7025/buffer', formattedMessage);
      console.log('Status da resposta:', response.status);
      console.log('Resposta da API:', response.data);
    } catch (error) {
      console.error('\nERRO AO ENVIAR PARA API:');
      console.error('Mensagem:', error.message);
      if (error.response) {
        console.error('Resposta do servidor:', error.response.data);
      }
      console.error('Dados enviados:', JSON.stringify(formattedMessage, null, 2));
    }
  } catch (error) {
    console.error('\nERRO GERAL:');
    console.error('Mensagem:', error.message);
  }
});

client.on('disconnected', (reason) => {
  console.log('Cliente desconectado');
  isConnected = false;
  io.emit('disconnected');
});

client.initialize();

app.get('/status', (req, res) => {
  res.json({ isConnected: isConnected });
});

app.get('/', (req, res) => {
  res.sendFile('index.html', { root: __dirname });
});

app.get('/socket.io/socket.io.js', (req, res) => {
  res.sendFile(require.resolve('socket.io-client/dist/socket.io.js'));
});

// Endpoint para enviar mensagens
app.post('/send-message', async (req, res) => {
    try {
        const { number, message, type = 'text' } = req.body;
        
        if (!number || !message) {
            return res.status(400).json({
                status: 'error',
                message: 'Número e mensagem são obrigatórios'
            });
        }

        // Formata o número para o padrão internacional do WhatsApp
        let formattedNumber = number.replace(/\D/g, ''); // Remove caracteres não numéricos
        
        // Se o número não começar com 55 (código do Brasil), adiciona
        if (!formattedNumber.startsWith('55')) {
            formattedNumber = '55' + formattedNumber;
        }
        
        // Adiciona o sufixo @c.us se não existir
        formattedNumber = formattedNumber.includes('@c.us') ? formattedNumber : `${formattedNumber}@c.us`;
        
        console.log('\n=== ENVIANDO MENSAGEM ===');
        console.log('Número original:', number);
        console.log('Número formatado:', formattedNumber);
        console.log('Tipo:', type);
        console.log('Mensagem:', message);

        let response;
        
        switch (type) {
            case 'text':
                response = await client.sendMessage(formattedNumber, message);
                break;
                
            case 'image':
                try {
                    console.log('Baixando imagem...');
                    const imageResponse = await axios.get(message, {
                        responseType: 'arraybuffer'
                    });
                    
                    // Determina o tipo MIME baseado no conteúdo
                    const mimeType = imageResponse.headers['content-type'] || 'image/jpeg';
                    console.log('Tipo MIME detectado:', mimeType);
                    
                    // Cria o MessageMedia com o buffer da imagem
                    const media = new MessageMedia(
                        mimeType,
                        Buffer.from(imageResponse.data).toString('base64'),
                        'image.jpg'
                    );
                    
                    console.log('Enviando imagem...');
                    response = await client.sendMessage(formattedNumber, media, {
                        caption: req.body.caption || ''
                    });
                    console.log('Imagem enviada com sucesso');
                } catch (error) {
                    console.error('Erro completo ao processar imagem:', error);
                    return res.status(500).json({
                        status: 'error',
                        message: `Erro ao processar imagem: ${error.message}`
                    });
                }
                break;
                
            case 'audio':
                try {
                    console.log('Baixando áudio...');
                    const audioResponse = await axios.get(message, {
                        responseType: 'arraybuffer'
                    });
                    
                    // Determina o tipo MIME baseado no conteúdo
                    const mimeType = audioResponse.headers['content-type'] || 'audio/wav';
                    console.log('Tipo MIME detectado:', mimeType);
                    
                    // Cria o MessageMedia com o buffer do áudio
                    const media = new MessageMedia(
                        mimeType,
                        Buffer.from(audioResponse.data).toString('base64'),
                        'audio.wav'
                    );
                    
                    console.log('Enviando áudio...');
                    response = await client.sendMessage(formattedNumber, media, {
                        sendAudioAsVoice: true
                    });
                    console.log('Áudio enviado com sucesso');
                } catch (error) {
                    console.error('Erro completo ao processar áudio:', error);
                    return res.status(500).json({
                        status: 'error',
                        message: `Erro ao processar áudio: ${error.message}`
                    });
                }
                break;
                
            default:
                return res.status(400).json({
                    status: 'error',
                    message: 'Tipo de mensagem não suportado'
                });
        }

        console.log('Mensagem enviada com sucesso');
        console.log('ID da mensagem:', response.id._serialized);

        return res.json({
            status: 'success',
            message: 'Mensagem enviada com sucesso',
            messageId: response.id._serialized
        });

    } catch (error) {
        console.error('\nERRO AO ENVIAR MENSAGEM:');
        console.error('Erro completo:', error);
        
        // Verifica se é um erro de número inválido
        if (error.message.includes('invalid wid')) {
            return res.status(400).json({
                status: 'error',
                message: 'Número de WhatsApp inválido'
            });
        }
        
        return res.status(500).json({
            status: 'error',
            message: `Erro ao enviar mensagem: ${error.message}`
        });
    }
});

// Rota para servir a imagem de teste
app.get('/test-image.png', (req, res) => {
    res.sendFile(path.join(__dirname, 'IMG_8234.png'));
});

server.listen(3333, () => {
  console.log('Servidor rodando na porta 3333');
});

