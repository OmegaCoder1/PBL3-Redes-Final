import logging
import time
import json
import requests
import random
import string
import math
import threading
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from threading import Lock, Condition
from flask_cors import CORS
from web3 import Web3

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do Flask
app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas

# CONFIGURACAO DAS URL LIGADAS AOS CONTAINERS EXATOS
CENTRAL1_URL = os.getenv('CENTRAL1_URL', 'http://localhost:5000')
CENTRAL2_URL = os.getenv('CENTRAL2_URL', 'http://localhost:5001')
CENTRAL3_URL = os.getenv('CENTRAL3_URL', 'http://localhost:5002')

# Chave privada que será atualizada pelo setup_blockchain.py
PRIVATE_KEY = "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1"

# Locks para controle de concorrência
lock = Lock()  # Lock principal
cond = Condition(lock)  # Condição para sincronização
leitores = 0  # Contador de leitores
escritor = False  # Flag indicando se há escritor ativo

# Constantes
BATERIA_INICIAL = 100  # Bateria inicial em porcentagem
BATERIA_MINIMA = 20    # Bateria mínima para solicitar reserva
UNIDADES_POR_PORCENTAGEM = 10  # Unidades que o carro pode percorrer por 1% de bateria
TEMPO_BATERIA_TOTAL = 3 * 60 * 60  # 3 horas em segundos

# Ranges de geração de postos para esta central
X_MIN = -3000
X_MAX = -1000
Y_MIN = -3000
Y_MAX = -1000
ESPACAMENTO_MINIMO = 100  # Espaçamento mínimo entre postos

# Dicionário global para armazenar os postos desta central
postos_central = {}

def adquirir_lock_leitura():
    """Adquire o lock para leitura."""
    global leitores
    with lock:
        while escritor:  # Espera se houver escritor ativo
            cond.wait()
        leitores += 1

def liberar_lock_leitura():
    """Libera o lock de leitura."""
    global leitores
    with lock:
        leitores -= 1
        if leitores == 0:
            cond.notify_all()  # Notifica escritores em espera

def adquirir_lock_escrita():
    """Adquire o lock para escrita."""
    global escritor
    with lock:
        while escritor or leitores > 0:  # Espera se houver escritor ou leitores
            cond.wait()
        escritor = True

def liberar_lock_escrita():
    """Libera o lock de escrita."""
    global escritor
    with lock:
        escritor = False
        cond.notify_all()  # Notifica todos os leitores e escritores em espera

def calcular_distancia(x1, y1, x2, y2):
    """Calcula a distância Euclidiana entre dois pontos."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def calcular_tempo_viagem(distancia, bateria_gasta):
    """Calcula o tempo de viagem baseado na distância e bateria gasta."""
    # Velocidade média do veículo (unidades por segundo)
    VELOCIDADE_MEDIA = 10  # unidades por segundo
    
    # Tempo baseado na distância e velocidade
    tempo_segundos = distancia / VELOCIDADE_MEDIA
    
    # Adiciona tempo de carregamento (5 minutos = 300 segundos)
    tempo_segundos += 300
    
    return tempo_segundos

def calcular_horario_chegada(horario_saida, tempo_viagem):
    """Calcula o horário de chegada baseado no horário de saída e tempo de viagem."""
    horario_chegada = horario_saida + timedelta(seconds=tempo_viagem)
    return horario_chegada

def calcular_tempo_espera(posto):
    """Calcula o tempo de espera baseado nas reservas existentes."""
    if not posto['reservas']:
        return 0  # Sem reservas, sem espera
        
    # Ordena as reservas por horário
    reservas_ordenadas = sorted(posto['reservas'], key=lambda x: x['horario'])
    
    # Encontra o primeiro horário disponível após a última reserva
    ultima_reserva = reservas_ordenadas[-1]
    horario_reserva = datetime.strptime(ultima_reserva['horario'], "%Y-%m-%d %H:%M:%S")
    tempo_espera = (horario_reserva - datetime.now()).total_seconds()
    
    return max(0, tempo_espera)  # Retorna 0 se o tempo de espera for negativo

def encontrar_posto_mais_proximo(x, y, postos_disponiveis, bateria_atual):
    """
    Encontra o posto mais próximo baseado no tempo de espera e distância.
    Retorna o nome do posto e seus dados.
    """
    posto_mais_proximo = None
    menor_tempo = float('inf')
    
    # Usa apenas a bateria mínima (20%) para calcular a distância máxima
    distancia_maxima = BATERIA_MINIMA * UNIDADES_POR_PORCENTAGEM
    
    logger.info(f"Procurando posto mais próximo de ({x}, {y}) com distância máxima de {distancia_maxima:.2f} unidades")
    
    # Lista para armazenar postos candidatos
    postos_candidatos = []
    
    for nome_posto, dados_posto in postos_disponiveis.items():
        tempo_espera = calcular_tempo_espera(dados_posto)
        distancia = calcular_distancia(x, y, dados_posto["x"], dados_posto["y"])
        
        # Verifica se o posto está dentro do alcance da bateria
        if distancia <= distancia_maxima:
            tempo_total = tempo_espera + distancia
            
            logger.info(f"""
            Analisando posto {nome_posto}:
            - Posição: ({dados_posto['x']}, {dados_posto['y']})
            - Distância até o posto: {distancia:.2f} unidades
            - Bateria necessária: {distancia/UNIDADES_POR_PORCENTAGEM:.2f}%
            - Tempo de espera: {tempo_espera:.2f} segundos
            - Tempo total: {tempo_total:.2f} segundos
            """)
            
            # Adiciona o posto à lista de candidatos
            postos_candidatos.append({
                "nome": nome_posto,
                "dados": dados_posto,
                "distancia": distancia,
                "tempo_total": tempo_total
            })
    
    # Ordena os candidatos por distância
    postos_candidatos.sort(key=lambda x: x["distancia"])
    
    # Escolhe o melhor posto (mais próximo)
    if postos_candidatos:
        melhor_posto = postos_candidatos[0]  # Pega o mais próximo
        posto_mais_proximo = (melhor_posto["nome"], melhor_posto["dados"])
        logger.info(f"Posto escolhido: {melhor_posto['nome']} com tempo total de {melhor_posto['tempo_total']:.2f} segundos")
    else:
        logger.info("Nenhum posto adequado encontrado dentro do alcance")
    
    return posto_mais_proximo

def calcular_ponto_parada(x_inicial, y_inicial, x_destino, y_destino, bateria_atual):
    """
    Calcula o ponto onde o carro estará quando atingir a bateria mínima.
    Retorna as coordenadas (x, y) do ponto de parada.
    """
    distancia_total = calcular_distancia(x_inicial, y_inicial, x_destino, y_destino)
    distancia_percorrida = (bateria_atual - BATERIA_MINIMA) * UNIDADES_POR_PORCENTAGEM
    
    logger.info(f"""
    ===== Cálculo do Ponto de Parada =====
    Posição Inicial: ({x_inicial}, {y_inicial})
    Destino Final: ({x_destino}, {y_destino})
    Distância Total: {distancia_total:.2f} unidades
    Bateria Atual: {bateria_atual}%
    Distância que pode percorrer: {distancia_percorrida:.2f} unidades
    """)
    
    if distancia_percorrida >= distancia_total:
        logger.info("Pode chegar ao destino sem parar!")
        return x_destino, y_destino
    
    # Calcula a proporção da distância percorrida
    proporcao = distancia_percorrida / distancia_total
    
    # Calcula o ponto de parada mantendo a mesma direção
    x_parada = x_inicial + (x_destino - x_inicial) * proporcao
    y_parada = y_inicial + (y_destino - y_inicial) * proporcao
    
    # Verifica se a distância real não excede o máximo permitido
    distancia_real = calcular_distancia(x_inicial, y_inicial, x_parada, y_parada)
    
    logger.info(f"""
    Ponto de Parada Calculado:
    Coordenadas: ({x_parada:.2f}, {y_parada:.2f})
    Distância Real Percorrida: {distancia_real:.2f} unidades
    Proporção da Distância: {proporcao:.2f}
    """)
    
    if distancia_real > distancia_percorrida:
        # Ajusta o ponto para garantir que não exceda a distância máxima
        fator_ajuste = distancia_percorrida / distancia_real
        x_parada = x_inicial + (x_parada - x_inicial) * fator_ajuste
        y_parada = y_inicial + (y_parada - y_inicial) * fator_ajuste
        
        distancia_real = calcular_distancia(x_inicial, y_inicial, x_parada, y_parada)
        logger.info(f"""
        Ponto de Parada Ajustado:
        Coordenadas: ({x_parada:.2f}, {y_parada:.2f})
        Distância Real Ajustada: {distancia_real:.2f} unidades
        Fator de Ajuste: {fator_ajuste:.2f}
        """)
    
    return x_parada, y_parada

def gerar_codigo_aleatorio(tamanho=6):
    """Gera um código aleatório de tamanho especificado."""
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(tamanho))

def gerar_coordenadas_sequenciais(num_postos):
    """Gera coordenadas para os postos com distribuição mais uniforme."""
    coordenadas = []
    
    # Calcula o número de linhas e colunas para uma distribuição mais uniforme
    num_linhas = int(math.sqrt(num_postos))
    num_colunas = int(num_postos / num_linhas)
    
    # Calcula o espaçamento entre postos em cada eixo
    espaco_x = (X_MAX - X_MIN) / (num_colunas + 1)
    espaco_y = (Y_MAX - Y_MIN) / (num_linhas + 1)
    
    # Gera coordenadas em uma grade mais uniforme
    for i in range(num_linhas):
        for j in range(num_colunas):
            # Adiciona uma pequena variação aleatória para evitar alinhamento perfeito
            variacao_x = random.uniform(-espaco_x * 0.2, espaco_x * 0.2)
            variacao_y = random.uniform(-espaco_y * 0.2, espaco_y * 0.2)
            
            x = X_MIN + (j + 1) * espaco_x + variacao_x
            y = Y_MIN + (i + 1) * espaco_y + variacao_y
            
            # Garante que as coordenadas estão dentro dos limites
            x = max(X_MIN, min(X_MAX, x))
            y = max(Y_MIN, min(Y_MAX, y))
            
            coordenadas.append((x, y))
    
    # Se ainda faltarem postos, adiciona aleatoriamente
    while len(coordenadas) < num_postos:
        x = random.uniform(X_MIN, X_MAX)
        y = random.uniform(Y_MIN, Y_MAX)
        
        # Verifica se o novo posto está longe o suficiente dos existentes
        muito_proximo = False
        for cx, cy in coordenadas:
            if calcular_distancia(x, y, cx, cy) < ESPACAMENTO_MINIMO:
                muito_proximo = True
                break
        
        if not muito_proximo:
            coordenadas.append((x, y))
    
    return coordenadas

def inicializar_postos_ficticios(num_postos=500):
    """Inicializa o dicionário com postos fictícios distribuídos sequencialmente."""
    global postos_central
    
    # Limpa o dicionário se já existir
    postos_central = {}
    
    # Gera coordenadas sequenciais
    coordenadas = gerar_coordenadas_sequenciais(num_postos)
    
    # Cria os postos com as coordenadas geradas
    for i, (x, y) in enumerate(coordenadas):
        # Gera nome do posto
        timestamp = int(time.time())
        random_code = gerar_codigo_aleatorio()
        nome_posto = f"Posto_Central1_{timestamp}_{random_code}"
        
        # Adiciona o posto ao dicionário
        postos_central[nome_posto] = {
            "x": round(x, 2),
            "y": round(y, 2),
            "ocupado": False,
            "id": None,
            "reservas": []
        }
        
        logger.info(f"""
        ===== Novo Posto Criado =====
        Nome: {nome_posto}
        Posição: ({x}, {y})
        Status: Disponível
        ===========================
        """)
    
    logger.info(f"""
    ===== Postos da Central 1 =====
    Total de postos: {len(postos_central)}
    Range X: {X_MIN} a {X_MAX}
    Range Y: {Y_MIN} a {Y_MAX}
    Espaçamento mínimo: {ESPACAMENTO_MINIMO}
    Postos disponíveis:
    {json.dumps(postos_central, indent=2)}
    ===========================
    """)
    return postos_central

# Rota Flask para retornar o dicionário de postos
@app.route('/postos', methods=['GET'])
def get_postos():
    """Rota para consultar os postos disponíveis."""
    try:
        adquirir_lock_leitura()
        try:
            return jsonify(postos_central)
        finally:
            liberar_lock_leitura()
    except Exception as e:
        logger.error(f"Erro ao consultar postos: {e}")
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro ao consultar postos: {str(e)}"
        }), 500

# Rota Flask para reservar um posto
@app.route('/reservar', methods=['POST'])
def reservar_posto():
    """Rota para reservar um posto."""
    try:

        dados = request.get_json()
        nome_posto = dados.get('nome_posto')
        cliente_id = dados.get('cliente_id')
        horario_reserva = dados.get('horario_reserva')
        
        if not nome_posto or not cliente_id or not horario_reserva:
            return jsonify({
                "status": "erro",
                "mensagem": "Parâmetros 'nome_posto', 'cliente_id' e 'horario_reserva' são obrigatórios"
            }), 400
            
        adquirir_lock_escrita()
        try:
            logger.info(f"Iniciando reserva para o posto {nome_posto} - Cliente {cliente_id}")
            
            # Simula um processamento demorado (5 segundos)
            logger.info("Processando reserva...")
            time.sleep(2)
            
            if nome_posto not in postos_central:
                logger.info(f"Posto {nome_posto} não encontrado")
                logger.info(f"Postos disponíveis: {postos_central}")
                return jsonify({
                    "status": "erro",
                    "mensagem": f"Posto {nome_posto} não encontrado"
                }), 404
                
            # Verifica se o posto está disponível no horário solicitado
            horario_solicitado = datetime.strptime(horario_reserva, "%Y-%m-%d %H:%M:%S")
            
            for reserva in postos_central[nome_posto]["reservas"]:
                horario_reserva_existente = datetime.strptime(reserva["horario"], "%Y-%m-%d %H:%M:%S")
                
                # Calcula o intervalo de tempo (10 minutos antes e depois)
                intervalo_minutos = 10
                inicio_intervalo = horario_reserva_existente - timedelta(minutes=intervalo_minutos)
                fim_intervalo = horario_reserva_existente + timedelta(minutes=intervalo_minutos)
                
                # Verifica se o horário solicitado está dentro do intervalo
                if inicio_intervalo <= horario_solicitado <= fim_intervalo:
                    return jsonify({
                        "status": "erro",
                        "mensagem": f"Posto {nome_posto} já está reservado no horário {reserva['horario']}. " +
                                  f"O posto está indisponível no intervalo de {inicio_intervalo.strftime('%H:%M')} " +
                                  f"até {fim_intervalo.strftime('%H:%M')}. " +
                                  f"Você está tentando reservar para {horario_solicitado.strftime('%H:%M')}, " +
                                  f"que está dentro deste intervalo."
                    }), 409
                
            # Adiciona a reserva
            postos_central[nome_posto]["reservas"].append({
                "cliente_id": cliente_id,
                "horario": horario_reserva
            })
            
            # Se for a primeira reserva, marca como ocupado
            if len(postos_central[nome_posto]["reservas"]) == 1:
                postos_central[nome_posto]["ocupado"] = True
                postos_central[nome_posto]["id"] = cliente_id
            
            logger.info(f"Posto {nome_posto} reservado para o cliente {cliente_id} no horário {horario_reserva}")
            
            return jsonify({
                "status": "sucesso",
                "mensagem": f"Posto {nome_posto} reservado com sucesso para o horário {horario_reserva}",
                "postos": postos_central
            })
        finally:
            liberar_lock_escrita()
            
    except Exception as e:
        logger.error(f"Erro ao processar requisição: {e}")
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro ao processar requisição: {str(e)}"
        }), 500

# Rota Flask para cancelar a reserva de um posto
@app.route('/cancelar', methods=['POST'])
def cancelar_reserva():
    """Rota para cancelar uma reserva."""
    try:
        dados = request.get_json()
        nome_posto = dados.get('nome_posto')
        cliente_id = dados.get('cliente_id')
        horario_reserva = dados.get('horario_reserva')
        
        if not nome_posto or not cliente_id or not horario_reserva:
            return jsonify({
                "status": "erro",
                "mensagem": "Parâmetros 'nome_posto', 'cliente_id' e 'horario_reserva' são obrigatórios"
            }), 400
            
        adquirir_lock_escrita()
        try:
            if nome_posto not in postos_central:
                return jsonify({
                    "status": "erro",
                    "mensagem": f"Posto {nome_posto} não encontrado"
                }), 404
                
            # Procura a reserva específica
            reserva_encontrada = False
            for reserva in postos_central[nome_posto]["reservas"]:
                if reserva["cliente_id"] == cliente_id and reserva["horario"] == horario_reserva:
                    postos_central[nome_posto]["reservas"].remove(reserva)
                    reserva_encontrada = True
                    break
            
            if not reserva_encontrada:
                return jsonify({
                    "status": "erro",
                    "mensagem": f"Reserva não encontrada para o cliente {cliente_id} no horário {horario_reserva}"
                }), 404
                
            # Se não houver mais reservas, marca como desocupado
            if len(postos_central[nome_posto]["reservas"]) == 0:
                postos_central[nome_posto]["ocupado"] = False
                postos_central[nome_posto]["id"] = None
            
            logger.info(f"Reserva do posto {nome_posto} cancelada para o cliente {cliente_id} no horário {horario_reserva}")
            
            return jsonify({
                "status": "sucesso",
                "mensagem": f"Reserva do posto {nome_posto} cancelada com sucesso",
                "postos": postos_central
            })
        finally:
            liberar_lock_escrita()
            
    except Exception as e:
        logger.error(f"Erro ao processar requisição: {e}")
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro ao processar requisição: {str(e)}"
        }), 500

# Rota Flask para adicionar um posto manualmente
@app.route('/adicionar_posto', methods=['POST'])
def adicionar_posto():
    """Rota para adicionar um posto manualmente."""
    try:
        dados = request.get_json()
        
        # Validação dos dados obrigatórios
        if not all(key in dados for key in ['x', 'y']):
            return jsonify({
                "status": "erro",
                "mensagem": "Parâmetros 'x' e 'y' são obrigatórios"
            }), 400
            
        adquirir_lock_escrita()
        try:
            # Gera nome do posto
            timestamp = int(time.time())
            random_code = gerar_codigo_aleatorio()
            nome_posto = f"Posto_Central1_{timestamp}_{random_code}"
            
            # Adiciona o posto ao dicionário mantendo o padrão existente
            postos_central[nome_posto] = {
                "x": float(dados['x']),
                "y": float(dados['y']),
                "ocupado": False,
                "id": None,
                "reservas": []
            }
            
            logger.info(f"""
            ===== Novo Posto Adicionado Manualmente =====
            Nome: {nome_posto}
            Posição: ({dados['x']}, {dados['y']})
            Status: Disponível
            =========================================
            """)
            
            return jsonify({
                "status": "sucesso",
                "mensagem": f"Posto {nome_posto} adicionado com sucesso",
                "posto": postos_central[nome_posto]
            })
            
        finally:
            liberar_lock_escrita()
            
    except Exception as e:
        logger.error(f"Erro ao adicionar posto: {e}")
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro ao adicionar posto: {str(e)}"
        }), 500

def escutar_eventos(contract, web3, server_account, private_key):
    logger.info("🟢 Iniciando escuta de eventos NovoBloco...")
    
    # Verifica se o contrato tem o evento
    logger.info("Verificando eventos disponíveis no contrato...")
    logger.info(f"Eventos disponíveis: {contract.events._events}")
    
    # Inicia do bloco atual
    ultimo_bloco = web3.eth.block_number
    logger.info(f"Iniciando escuta a partir do bloco {ultimo_bloco}")

    while True:
        try:
            # Verifica se há novos blocos
            bloco_atual = web3.eth.block_number
            if bloco_atual > ultimo_bloco:
                logger.info(f"Novo bloco detectado! Bloco atual: {bloco_atual}")
                
                # Debug: Mostra informações do bloco
                bloco_info = web3.eth.get_block(bloco_atual)
                logger.info(f"Informações do bloco {bloco_atual}:")
                logger.info(f"Hash: {bloco_info['hash'].hex()}")
                logger.info(f"Transações: {len(bloco_info['transactions'])}")
                
                # Debug: Mostra detalhes da transação
                if len(bloco_info['transactions']) > 0:
                    tx_hash = bloco_info['transactions'][0]
                    tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
                    logger.info(f"Detalhes da transação:")
                    logger.info(f"Hash: {tx_receipt['transactionHash'].hex()}")
                    logger.info(f"Status: {'Sucesso' if tx_receipt['status'] == 1 else 'Falha'}")
                    logger.info(f"Logs: {len(tx_receipt['logs'])}")
                    for log in tx_receipt['logs']:
                        logger.info(f"Log: {log}")
                        logger.info(f"Log Address: {log['address']}")
                        logger.info(f"Log Topics: {log['topics']}")
                        logger.info(f"Log Data: {log['data']}")
                        
                        # Verifica se é um evento NovoBloco
                        if log['address'].lower() == contract.address.lower():
                            logger.info("Evento do contrato detectado!")
                            # Decodifica o evento
                            try:
                                evento = contract.events.NovoBloco().process_log(log)
                                logger.info(f"Evento decodificado: {evento}")
                                bloco_id = evento['args']['id']
                                logger.info(f"Evento NovoBloco detectado! ID: {bloco_id}")

                                # Removida a condição de eleição - agora processa todos os blocos
                                logger.info("Reserva sendo calculada pelo Servidor 1")
                                # Busca bloco completo
                                bloco = contract.functions.getBloco(bloco_id).call()

                                logger.info(f"""
                                🔔 Nova solicitação de reserva detectada!
                                🔸 ID do bloco: {bloco_id}
                                👤 Cliente: {bloco[0]}
                                📍 Origem: ({bloco[1]}, {bloco[2]})
                                📍 Destino: ({bloco[3]}, {bloco[4]})
                                ⚡ Bateria: {bloco[5]}%
                                🕒 Timestamp: {bloco[6]}
                                """)

                                cliente_id = bloco[0]
                                x_inicial = float(bloco[1])
                                y_inicial = float(bloco[2])
                                x_destino = float(bloco[3])
                                y_destino = float(bloco[4])
                                bateria_atual = float(bloco[5])

                                # Horário de saída
                                horario_saida = datetime.now()

                                # Dicionário para armazenar todos os postos disponíveis
                                todos_postos = {}
                                
                                # Adiciona os postos desta central
                                todos_postos.update(postos_central)
                                logger.info(f"""
                                ===== Postos Disponíveis =====
                                Postos desta central: {len(postos_central)}
                                Detalhes dos postos:
                                {json.dumps(postos_central, indent=2)}
                                ===========================
                                """)

                                try:
                                    # Requisição para o servidor 2
                                    response1 = requests.get(f"{CENTRAL2_URL}/postos", timeout=15)
                                    if response1.status_code == 200:
                                        postos_servidor1 = response1.json()
                                        todos_postos.update(postos_servidor1)
                                        logger.info(f"""
                                        ===== Postos do Servidor 1 =====
                                        Total: {len(postos_servidor1)}
                                        Detalhes:
                                        {json.dumps(postos_servidor1, indent=2)}
                                        ===========================
                                        """)

                                except requests.exceptions.Timeout:
                                    logger.error("Timeout ao tentar acessar o servidor")
                                except requests.exceptions.RequestException as e:
                                    logger.error(f"Erro ao fazer requisição para outros servidores: {e}")

                                try:
                                    # Requisição para o servidor 3
                                    response2 = requests.get(f"{CENTRAL3_URL}/postos", timeout=15)
                                    if response2.status_code == 200:
                                        postos_servidor2 = response2.json()
                                        todos_postos.update(postos_servidor2)
                                        logger.info(f"""
                                        ===== Postos do Servidor 2 =====
                                        Total: {len(postos_servidor2)}
                                        Detalhes:
                                        {json.dumps(postos_servidor2, indent=2)}
                                        ===========================
                                        """)
                                    
                                except requests.exceptions.Timeout:
                                    logger.error("Timeout ao tentar acessar o servidor")
                                except requests.exceptions.RequestException as e:
                                    logger.error(f"Erro ao fazer requisição para outros servidores: {e}")

                                logger.info(f"""
                                ===== Resumo dos Postos =====
                                Total de postos disponíveis: {len(todos_postos)}
                                Detalhes de todos os postos:
                                {json.dumps(todos_postos, indent=2)}
                                ===========================
                                """)
                                
                                if len(todos_postos) == 0:
                                    logger.error("Nenhum posto disponível para cálculo da rota")
                                    resposta = {
                                        "cliente_id": cliente_id,
                                        "postos_reservados": [],
                                        "status": "erro",
                                        "mensagem": "Nenhum posto disponível para cálculo da rota",
                                        "timestamp": time.time()
                                    }

                                    # Transação de publicação da resposta
                                    tx = contract.functions.registrarResposta(
                                        bloco_id,
                                        False,
                                        "Nenhum posto disponível para cálculo da rota"
                                    ).build_transaction({
                                        "from": server_account.address,
                                        "nonce": web3.eth.get_transaction_count(server_account.address),
                                        "gas": 300000,
                                        "gasPrice": web3.to_wei("1", "gwei")
                                    })

                                    # Assinar e enviar
                                    assinado = web3.eth.account.sign_transaction(tx, private_key)
                                    tx_hash = web3.eth.send_raw_transaction(assinado.raw_transaction)
                                    print(f"Conta usada: {web3.eth.accounts[0]}")
                                    print(f"Saldo: {web3.eth.get_balance(web3.eth.accounts[0])}")
                                    return
                                
                                # Lista para armazenar os postos que serão reservados
                                postos_reservados = []
                                detalhes_rota = []
                                
                                # Ponto atual do carro
                                x_atual = x_inicial
                                y_atual = y_inicial
                                bateria_atual = BATERIA_INICIAL
                                horario_atual = horario_saida
                                
                                while True:
                                    # Calcula a distância até o destino
                                    distancia_restante = calcular_distancia(x_atual, y_atual, x_destino, y_destino)
                                    logger.info(f"Distância restante até o destino: {distancia_restante:.2f} unidades")
                                    logger.info(f"Bateria atual: {bateria_atual}%")
                                    
                                    # Verifica se pode chegar ao destino com a bateria atual
                                    distancia_maxima = (bateria_atual - BATERIA_MINIMA) * UNIDADES_POR_PORCENTAGEM
                                    logger.info(f"Distância máxima possível com bateria atual: {distancia_maxima:.2f} unidades")
                                    
                                    if distancia_restante <= distancia_maxima:
                                        logger.info("Pode chegar ao destino sem paradas!")
                                        tempo_viagem_final = calcular_tempo_viagem(distancia_restante, distancia_restante/UNIDADES_POR_PORCENTAGEM)
                                        horario_chegada_final = calcular_horario_chegada(horario_atual, tempo_viagem_final)
                                        detalhes_rota.append({
                                            "tipo": "destino",
                                            "x": x_destino,
                                            "y": y_destino,
                                            "bateria_restante": bateria_atual - (distancia_restante / UNIDADES_POR_PORCENTAGEM),
                                            "horario_chegada": horario_chegada_final.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                                        break
                                    
                                    # Calcula o ponto onde o carro estará com 20% de bateria
                                    x_parada, y_parada = calcular_ponto_parada(x_atual, y_atual, x_destino, y_destino, bateria_atual)
                                    logger.info(f"Ponto de parada calculado: ({x_parada:.2f}, {y_parada:.2f})")
                                    
                                    # Encontra o posto mais próximo desse ponto que esteja dentro do alcance
                                    posto_mais_proximo = encontrar_posto_mais_proximo(x_parada, y_parada, todos_postos, bateria_atual)
                                    
                                    if posto_mais_proximo is None:
                                        logger.error("Não foi possível encontrar um posto adequado para completar a rota")
                                        resposta = {
                                            "cliente_id": cliente_id,
                                            "postos_reservados": [],
                                            "status": "erro",
                                            "mensagem": "Não foi possível encontrar um posto adequado para completar a rota",
                                            "timestamp": time.time()
                                        }

                                        # Transação de publicação da resposta
                                        tx = contract.functions.registrarResposta(
                                            bloco_id,
                                            False,
                                            "Não foi possível encontrar um posto adequado para completar a rota"
                                        ).build_transaction({
                                            "from": server_account.address,
                                            "nonce": web3.eth.get_transaction_count(server_account.address),
                                            "gas": 300000,
                                            "gasPrice": web3.to_wei("1", "gwei")
                                        })

                                        # Assinar e enviar
                                        assinado = web3.eth.account.sign_transaction(tx, private_key)
                                        tx_hash = web3.eth.send_raw_transaction(assinado.raw_transaction)
                                        return
                                    
                                    nome_posto, dados_posto = posto_mais_proximo
                                    distancia_posto = calcular_distancia(x_atual, y_atual, dados_posto["x"], dados_posto["y"])
                                    logger.info(f"Posto mais próximo encontrado: {nome_posto} em ({dados_posto['x']}, {dados_posto['y']})")
                                    logger.info(f"Distância até o posto: {distancia_posto:.2f} unidades")
                                    
                                    # Calcula o tempo de viagem até este posto
                                    tempo_viagem = calcular_tempo_viagem(distancia_posto, distancia_posto/UNIDADES_POR_PORCENTAGEM)
                                    horario_chegada = calcular_horario_chegada(horario_atual, tempo_viagem)
                                    
                                    postos_reservados.append(nome_posto)
                                    detalhes_rota.append({
                                        "tipo": "posto",
                                        "nome": nome_posto,
                                        "x": dados_posto["x"],
                                        "y": dados_posto["y"],
                                        "bateria_chegada": BATERIA_MINIMA,
                                        "horario_chegada": horario_chegada.strftime("%Y-%m-%d %H:%M:%S")
                                    })
                                    
                                    # Atualiza a posição atual e o horário para o próximo cálculo
                                    x_atual = dados_posto["x"]
                                    y_atual = dados_posto["y"]
                                    bateria_atual = 100  # Bateria recarregada
                                    horario_atual = horario_chegada
                                
                                # Tenta reservar todos os postos necessários
                                for i, nome_posto in enumerate(postos_reservados):
                                    try:
                                        # Determina qual servidor possui o posto
                                        if nome_posto.startswith("Posto_Central1"):
                                            url = f"{CENTRAL1_URL}/reservar"
                                        elif nome_posto.startswith("Posto_Central2"):
                                            url = f"{CENTRAL2_URL}/reservar"
                                        else:
                                            url = f"{CENTRAL3_URL}/reservar"
                                            
                                        # Obtém o horário de chegada deste posto
                                        horario_chegada = detalhes_rota[i]["horario_chegada"]
                                        
                                        # Faz a requisição para reservar o posto
                                        response = requests.post(url, json={
                                            "nome_posto": nome_posto,
                                            "cliente_id": cliente_id,
                                            "horario_reserva": horario_chegada
                                        }, timeout=15)
                                        
                                        if response.status_code == 200:
                                            logger.info(f"Posto {nome_posto} reservado com sucesso para o horário {horario_chegada}")
                                        else:
                                            logger.error(f"Falha ao reservar posto {nome_posto}")
                                            # Cancela todas as reservas anteriores
                                            for j in range(i):
                                                try:
                                                    nome_posto_anterior = postos_reservados[j]
                                                    if nome_posto_anterior.startswith("Posto_Central1"):
                                                        url = f"{CENTRAL1_URL}/cancelar"
                                                    elif nome_posto_anterior.startswith("Posto_Central2"):
                                                        url = f"{CENTRAL2_URL}/cancelar"
                                                    else:
                                                        url = f"{CENTRAL3_URL}/cancelar"
                                                    
                                                    requests.post(url, json={
                                                        "nome_posto": nome_posto_anterior,
                                                        "cliente_id": cliente_id,
                                                        "horario_reserva": detalhes_rota[j]["horario_chegada"]
                                                    }, timeout=15)
                                                except:
                                                    pass
                                        
                                        resposta = {
                                            "cliente_id": cliente_id,
                                            "postos_reservados": [],
                                            "status": "erro",
                                            "mensagem": f"Falha ao reservar posto {nome_posto}, motivo: {response.text} status: {response.status_code}",
                                            "timestamp": time.time()
                                        }

                                        # Transação de publicação da resposta
                                        tx = contract.functions.registrarResposta(
                                            bloco_id,
                                            False,
                                            f"Falha ao reservar posto {nome_posto}, motivo: {response.text} status: {response.status_code}"
                                        ).build_transaction({
                                            "from": server_account.address,
                                            "nonce": web3.eth.get_transaction_count(server_account.address),
                                            "gas": 300000,
                                            "gasPrice": web3.to_wei("1", "gwei")
                                        })

                                        # Assinar e enviar
                                        assinado = web3.eth.account.sign_transaction(tx, private_key)
                                        tx_hash = web3.eth.send_raw_transaction(assinado.raw_transaction)
                                        return
                                        
                                    except requests.exceptions.RequestException as e:
                                        logger.error(f"Erro ao reservar posto {nome_posto}: {e}")
                                        # Cancela todas as reservas anteriores
                                        for j in range(i):
                                            try:
                                                nome_posto_anterior = postos_reservados[j]
                                                if nome_posto_anterior.startswith("Posto_Central1"):
                                                    url = f"{CENTRAL1_URL}/cancelar"
                                                elif nome_posto_anterior.startswith("Posto_Central2"):
                                                    url = f"{CENTRAL2_URL}/cancelar"
                                                else:
                                                    url = f"{CENTRAL3_URL}/cancelar"
                                                
                                                requests.post(url, json={
                                                    "nome_posto": nome_posto_anterior,
                                                    "cliente_id": cliente_id,
                                                    "horario_reserva": detalhes_rota[j]["horario_chegada"]
                                                }, timeout=15)
                                            except:
                                                pass
                                
                                resposta = {
                                    "cliente_id": cliente_id,
                                    "postos_reservados": postos_reservados,
                                    "status": "sucesso",
                                    "mensagem": "Todos os postos necessários foram reservados com sucesso",
                                    "detalhes_rota": detalhes_rota,
                                    "timestamp": time.time()
                                }
                                
                                logger.info(f"""
                                ===== Tentando Publicar Resposta =====
                                Resposta: {json.dumps(resposta, indent=2)}
                                ===================================
                                """)
                                
                                try:
                                    # Transação de publicação da resposta
                                    tx = contract.functions.registrarResposta(
                                        bloco_id,
                                        True,
                                        "Todos os postos necessários foram reservados com sucesso"
                                    ).build_transaction({
                                        "from": server_account.address,
                                        "nonce": web3.eth.get_transaction_count(server_account.address),
                                        "gas": 300000,
                                        "gasPrice": web3.to_wei("1", "gwei")
                                    })

                                    # Assinar e enviar
                                    assinado = web3.eth.account.sign_transaction(tx, private_key)
                                    tx_hash = web3.eth.send_raw_transaction(assinado.raw_transaction)

                                    logger.info("Mensagem publicada com sucesso")
                                except Exception as e:
                                    logger.error(f"Erro ao publicar mensagem: {e}")
                                
                                logger.info(f"Resposta publicada: {resposta}")

                            except Exception as e:
                                logger.error(f"Erro ao decodificar evento: {e}")

                ultimo_bloco = bloco_atual

            time.sleep(1)  # Pequena pausa para não sobrecarregar

        except Exception as e:
            logger.error(f"Erro ao escutar eventos: {str(e)}")
            logger.error("Stack trace:", exc_info=True)  # Adiciona stack trace para debug
            time.sleep(5)  # Pausa maior em caso de erro

def conectar():
    # Usa a URL do Ganache da variável de ambiente ou o hostname interno do Docker
    ganache_url = os.getenv('GANACHE_URL', 'http://ganache:7545')
    logger.info(f"Tentando conectar ao Ganache em: {ganache_url}")
    
    web3 = Web3(Web3.HTTPProvider(ganache_url))
    
    # Verifica a conexão
    if web3.is_connected():
        logger.info("✅ Conexão com Ganache estabelecida!")
        logger.info(f"Versão do Ganache: {web3.client_version}")
        logger.info(f"Último bloco: {web3.eth.block_number}")
    else:
        logger.error("❌ Falha ao conectar com Ganache!")
        raise Exception("Não foi possível conectar ao Ganache")

    # Lê o arquivo contrato.json para obter o endereço do contrato
    logger.info("Lendo arquivo contrato.json...")
    with open("/shared/centrais_postos/contrato.json") as f:
        contrato_info = json.load(f)
        contract_address = web3.to_checksum_address(contrato_info["contrato"])
        logger.info(f"Endereço do contrato: {contract_address}")

    # Lê o ABI do arquivo
    logger.info("Lendo arquivo PostoReserva_abi.json...")
    with open("/shared/centrais_postos/PostoReserva_abi.json") as f:
        abi = json.load(f)  # O ABI já é um array, não precisa acessar ["abi"]
        logger.info(f"ABI carregado com {len(abi)} funções")

    contract = web3.eth.contract(address=contract_address, abi=abi)
    logger.info("Contrato instanciado com sucesso!")

    return web3, contract

# Inicializa os postos fictícios
inicializar_postos_ficticios()

if __name__ == '__main__':
    try:
        logger.info("Iniciando Central 1...")
        logger.info("Tentando conectar ao Ganache...")
        web3, contract = conectar()
        logger.info("Conexão com Ganache estabelecida com sucesso!")

        # Conta do servidor de posto
        logger.info("Configurando conta do servidor...")
        private_key = PRIVATE_KEY
        logger.info(f"Chave privada lida: {private_key}")
        logger.info(f"Tamanho da chave privada: {len(private_key)} bytes")
        logger.info(f"Tipo da chave privada: {type(private_key)}")
        
        # Verifica se a chave privada está no formato correto
        if not private_key.startswith("0x"):
            logger.error("Chave privada não começa com 0x")
            raise ValueError("Chave privada inválida: deve começar com 0x")
        
        if len(private_key) != 66:  # 0x + 64 caracteres hexadecimais
            logger.error(f"Chave privada com tamanho incorreto: {len(private_key)} bytes")
            raise ValueError(f"Chave privada inválida: deve ter 66 caracteres (0x + 64 hex), mas tem {len(private_key)}")
        
        # Verifica se a conta existe no Ganache
        server_account = web3.eth.account.from_key(private_key)
        logger.info(f"Conta do servidor configurada: {server_account.address}")
        
        # Verifica se a conta tem saldo
        balance = web3.eth.get_balance(server_account.address)
        logger.info(f"Saldo da conta: {web3.from_wei(balance, 'ether')} ETH")
        
        if balance == 0:
            logger.warning("A conta não tem saldo! Isso pode causar problemas nas transações.")
        
        # Lista todas as contas do Ganache para debug
        accounts = web3.eth.accounts
        logger.info("Contas disponíveis no Ganache:")
        for i, account in enumerate(accounts):
            balance = web3.eth.get_balance(account)
            logger.info(f"Conta {i}: {account} - Saldo: {web3.from_wei(balance, 'ether')} ETH")

        logger.info("Iniciando thread de escuta de eventos...")
        thread = threading.Thread(target=escutar_eventos, args=(contract, web3, server_account, private_key))
        thread.start()
        logger.info("Thread de escuta de eventos iniciada com sucesso!")
        
        # Iniciando o servidor Flask
        logger.info(f"""
        ============================================
        Servidor Central 1 Iniciado com Sucesso!
        - Flask rodando na porta 5000
        - Conectado ao Ganache
        - Thread de eventos ativa
        - Conta do servidor: {server_account.address}
        - Saldo: {web3.from_wei(balance, 'ether')} ETH
        ============================================
        """)
        app.run(host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        logger.info("Servidor Central 1 encerrado pelo usuário.")
    except Exception as e:
        logger.error(f"Erro ao iniciar o servidor: {e}")
        logger.error("Stack trace:", exc_info=True)