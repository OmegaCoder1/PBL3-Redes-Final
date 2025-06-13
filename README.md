# 🚗 Sistema de Reserva de Postos de Combustível com Blockchain

Este projeto implementa um sistema distribuído de reserva de postos de combustível utilizando blockchain. O sistema é composto por três centrais de processamento que trabalham de forma coordenada para gerenciar reservas de postos de combustível.

## 🏗️ Arquitetura do Sistema

O sistema é composto pelos seguintes componentes:

1. **⛓️ Ganache**: Blockchain local para desenvolvimento e testes
2. **🏢 Centrais de Processamento**: 3 instâncias que gerenciam os postos de combustível
3. **👤 Cliente**: Interface para interação com o sistema
4. **🔍 Blockview**: Explorador de blocos para visualização da blockchain

## 📋 Pré-requisitos

- 🐳 Docker
- 🐳 Docker Compose
- 📦 Git

## 🚀 Instalação e Execução

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITÓRIO]
cd [NOME_DO_DIRETÓRIO]
```

2. Construa as imagens Docker:
```bash
docker-compose build
```

3. Execute o script de setup:
```bash
./setup.sh
```

## ⚙️ Processo de Inicialização

O script `setup.sh` executa a seguinte sequência:

1. **🚀 Inicialização do Ganache**:
   - Inicia o container do Ganache (blockchain local)
   - Aguarda 10 segundos para garantir que o Ganache esteja pronto

2. **🔑 Configuração das Chaves**:
   - Executa o script `setup_blockchain.py`
   - Obtém as contas do Ganache
   - Atualiza as chaves privadas nas centrais
   - Configura o Hardhat

3. **📝 Deploy do Contrato**:
   - Compila o contrato inteligente
   - Faz o deploy na rede Ganache

4. **⚡ Inicialização dos Serviços**:
   - Inicia as 3 centrais de processamento
   - Inicia o Blockview (explorador de blocos)
   - Inicia o cliente em modo interativo

## 🧩 Componentes do Sistema

### 🏢 Centrais de Processamento

Cada central é responsável por:
- 📍 Gerenciar um conjunto de postos de combustível
- 🔄 Processar solicitações de reserva
- 📡 Comunicar-se com outras centrais
- 👑 Participar do mecanismo de eleição de blocos

O mecanismo de eleição garante que cada bloco seja processado por apenas uma central:
```python
instancia_id = int(server_account.address, 16) % 1000
bloco_hash = int(bloco_info['hash'].hex(), 16)
eleito = (bloco_hash % 3) + 1
```

### 📄 Contrato Inteligente

O contrato inteligente gerencia:
- 📝 Registro de novos blocos de reserva
- ⚡ Processamento de reservas
- 📤 Registro de respostas das centrais

### 🔍 Blockview

Interface web para visualização:
- 📦 Blocos da blockchain
- 💸 Transações
- 📊 Eventos do contrato

Acessível em: `http://localhost:3456`

> ⚠️ **Importante**: Se o Blockview não estiver acessível, verifique o arquivo `blockview-local-explorer/src/lib/web3.ts` e substitua `localhost` pelo IP da máquina onde o sistema está rodando na configuração do Web3.

## 📁 Estrutura de Diretórios

```
.
├── 📂 centrais_postos/          # Código das centrais de processamento
├── 📂 blockview-local-explorer/ # Explorador de blocos
├── 📂 contracts/               # Contratos inteligentes
├── 📄 docker-compose.yml      # Configuração dos containers
├── 📄 setup.sh               # Script de inicialização
└── 📄 setup_blockchain.py    # Script de configuração do blockchain
```

## 🔌 Portas Utilizadas

- ⛓️ Ganache: 7545
- 🏢 Central 1: 5000
- 🏢 Central 2: 5001
- 🏢 Central 3: 5002
- 🔍 Blockview: 3456

## 👑 Mecanismo de Eleição

O sistema utiliza um mecanismo determinístico para eleger qual central processará cada bloco:

1. 🆔 Cada central tem um ID único baseado no endereço da sua conta
2. 🔄 O hash do bloco é usado para determinar a central eleita
3. 🎲 A distribuição é aleatória mas determinística (mesmo bloco sempre vai para mesma central)
4. ⚖️ A carga é distribuída igualmente entre as 3 centrais

### ⚠️ Considerações sobre Descentralização

O sistema foi projetado para ser descentralizado, onde cada bloco é processado por apenas uma central. Isso traz algumas considerações importantes:

1. 🔒 **Segurança**: A descentralização garante que não haja processamento duplicado de blocos
2. ⚡ **Performance**: A carga é distribuída igualmente entre as centrais
3. 🚫 **Limitação**: Se uma central ficar offline, os blocos que ela seria responsável por processar não serão atendidos
4. 🔄 **Solução**: Para garantir que todos os blocos sejam processados, existe uma versão alternativa do sistema:
   - 📄 `central_posto_total.py`: Processa todos os blocos, independente do hash
   - 💡 Útil para garantir que nenhuma solicitação seja perdida
   - ⚠️ Não deve ser usado em conjunto com as centrais normais para evitar processamento duplo

### 🔄 Processamento Total

Se você precisar garantir que todos os blocos sejam processados, mesmo que uma central fique offline:

1. Pare todas as centrais normais:
```bash
docker-compose down
```

2. Modifique o `docker-compose.yml` para usar o `central_posto_total.py`:
```yaml
central1:
  build: .
  command: python /shared/centrais_postos/central_posto_total.py
  # ... resto da configuração ...
```

3. Inicie o sistema:
```bash
docker-compose up
```

## 📊 Logs e Monitoramento

Cada componente gera logs detalhados que podem ser visualizados através do Docker:

```bash
# 📝 Logs do Ganache
docker logs pbl-redes-ganache

# 📝 Logs das centrais
docker logs pbl-redes-central1
docker logs pbl-redes-central2
docker logs pbl-redes-central3

# 📝 Logs do Blockview
docker logs pbl-redes-blockview
```

## 🔧 Troubleshooting

1. ⚠️ Se o Ganache não iniciar:
   - 🔍 Verifique se a porta 7545 está disponível
   - ⏳ Aguarde mais tempo antes de executar o setup

2. ⚠️ Se as centrais não se conectarem:
   - 🔍 Verifique se o Ganache está rodando
   - 🔑 Verifique se as chaves privadas foram atualizadas corretamente

3. ⚠️ Se o Blockview não estiver acessível:
   - 🔍 Verifique se a porta 3456 está disponível
   - ⏳ Aguarde alguns segundos após a inicialização
