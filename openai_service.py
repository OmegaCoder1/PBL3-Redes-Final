import requests
import json
import math
import time
import logging
from typing import Dict, Optional, Any, Union
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from Controllers.baserow_controller import (
    fetch_user_data,
    get_all_user_data,
    update_user_data,
    create_new_user,
    create_new_transactionController,
    get_last_payment_idController,
    update_transaction_dataController,
    get_optionController
)
from Models.BaseRowModel import get_all_data_by_telegram_id, update_thread_id
from Services.zapster_send_message_serice import send_message_zapster
from Services.assistant_cache import AssistantCache
from Services.context_manager import ContextManager
from cache_manager import assistant_cache  # Importa a instância do cache
from datetime import datetime
import string

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes
OPENAI_API_URL = "https://api.openai.com/v1/threads"
ASSISTANT_ID = 'asst_oBEe94r9vQQbxj3CFTqiidMn'
TABLE_NAME = "Whatsapp_hot"
HEADERS = {
    'Authorization': 'Bearer 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',
    'Content-Type': 'application/json',
    'OpenAI-Beta': 'assistants=v2'
}

# Cache de usuários
@lru_cache(maxsize=1000)
def get_cached_user_data(telegram_id: str, table_name: str) -> Dict:
    """Obtém dados do usuário do cache ou do banco de dados"""
    print(f"\n[CACHE] ================================================")
    print(f"[CACHE] Buscando dados do usuário: {telegram_id}")
    print(f"[CACHE] Tabela: {table_name}")
    
    # Armazena o estado do cache antes da chamada
    cache_before = get_cached_user_data.cache_info()
    
    # Faz a chamada ao banco
    result = get_all_data_by_telegram_id(telegram_id, table_name)
    
    # Verifica o estado do cache após a chamada
    cache_after = get_cached_user_data.cache_info()
    
    # Se o número de hits aumentou, significa que veio do cache
    is_cached = cache_after.hits > cache_before.hits
    print(f"[CACHE] Resultado veio do cache? {'Sim' if is_cached else 'Não'}")
    
    if is_cached:
        print(f"[CACHE] Cache hit! Dados retornados do cache")
    else:
        print(f"[CACHE] Cache miss! Dados buscados do banco")
        print(f"[CACHE] Resultado encontrado: {result is not None}")
        if result:
            print(f"[CACHE] Quantidade de registros: {len(result)}")
    
    print(f"[CACHE] Cache info: {cache_after}")
    print(f"[CACHE] ================================================\n")
    return result

# Retry decorator para envio de mensagens
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_message_with_retry(number: str, message: str) -> bool:
    """Envia mensagem com retry automático em caso de falha"""
    print(f"\n[ENVIO] ================================================")
    print(f"[ENVIO] Tentando enviar mensagem para: {number}")
    print(f"[ENVIO] Mensagem: {message[:50]}...")  # Mostra apenas os primeiros 50 caracteres
    
    try:
        result = send_message_zapster(number, message)
        print(f"[ENVIO] Mensagem enviada com sucesso: {result}")
        return result
    except Exception as e:
        print(f"[ENVIO] Erro ao enviar mensagem: {str(e)}")
        raise  # Re-lança a exceção para o decorador @retry
    finally:
        print(f"[ENVIO] ================================================\n")

class OpenAIService:
    def __init__(self):
        self.api_url = OPENAI_API_URL
        self.headers = HEADERS
        self.assistant_id = ASSISTANT_ID
        self.cache = assistant_cache
        self.context_manager = ContextManager()  # Instância do novo gerenciador de contexto
        print(f"\n[SERVIÇO] ================================================")
        print(f"[SERVIÇO] OpenAIService inicializado com sucesso!")
        print(f"[SERVIÇO] Cache de usuários: {get_cached_user_data.cache_info()}")
        print(f"[SERVIÇO] ================================================\n")
        logger.info("OpenAIService inicializado com sucesso!")

    def get_thread_id(self, telegram_id: str) -> Optional[str]:
        """Obtém o thread_id existente do banco de dados."""
        try:
            print(f"\n[THREAD] ================================================")
            print(f"[THREAD] Buscando thread_id para usuário: {telegram_id}")
            
            # Usa o cache para obter dados do usuário
            user_data = get_cached_user_data(telegram_id, TABLE_NAME)
            
            if user_data and len(user_data) > 0:
                thread_id = user_data[0]['thread_id']
                print(f"[THREAD] Thread ID encontrado: {thread_id}")
                print(f"[THREAD] ================================================\n")
                return thread_id
            
            print(f"[THREAD] Nenhum dado encontrado para usuário: {telegram_id}")
            print(f"[THREAD] ================================================\n")
            return None
            
        except Exception as e:
            print(f"[THREAD] Erro ao obter thread_id: {e}")
            print(f"[THREAD] ================================================\n")
            logger.error(f"Erro ao obter thread_id: {e}")
            return None

    def create_thread(self) -> Optional[str]:
        """Cria uma nova thread."""
        try:
            response = requests.post(self.api_url, headers=self.headers)
            if response.status_code == 200:
                thread_id = response.json()['id']
                logger.info(f"Thread ID criado: {thread_id}")
                return thread_id
            logger.error(f"Erro ao criar thread. Status: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Erro ao criar thread: {e}")
            return None

    def update_thread_id(self, telegram_id: str, thread_id: str) -> bool:
        """Atualiza o thread_id no banco de dados."""
        try:
            response = update_thread_id(telegram_id, thread_id, TABLE_NAME)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao atualizar thread_id: {e}")
            return False

    def get_runs(self, thread_id: str) -> Dict:
        """Obtém as runs de uma thread."""
        try:
            url = f"{self.api_url}/{thread_id}/runs?limit=1&order=desc"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Erro ao obter runs: {e}")
            return {}

    def create_user_message(self, thread_id: str, user_message: str) -> Optional[Dict]:
        """Cria uma mensagem do usuário na thread."""
        try:
            url = f"{self.api_url}/{thread_id}/messages"
            message_data = {
                "role": "user",
                "content": user_message
            }
            response = requests.post(url, headers=self.headers, json=message_data)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Erro ao criar mensagem: {e}")
            return None

    def create_run(self, thread_id: str) -> Optional[str]:
        """Cria um novo run para a thread."""
        try:
            url = f"{self.api_url}/{thread_id}/runs"
            run_data = {"assistant_id": self.assistant_id}
            response = requests.post(url, headers=self.headers, json=run_data)
            if response.status_code == 200:
                return response.json().get('run_id')
            return None
        except Exception as e:
            logger.error(f"Erro ao criar run: {e}")
            return None

    def get_run_status(self, thread_id: str) -> Dict:
        """Obtém o status atual do run."""
        try:
            url = f"{self.api_url}/{thread_id}/runs?limit=1&order=desc"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Erro ao obter status do run: {e}")
            return {}

    def get_messages(self, thread_id: str) -> Dict:
        """Obtém as mensagens de uma thread."""
        try:
            url = f"{self.api_url}/{thread_id}/messages?order=desc"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Erro ao obter mensagens: {e}")
            return {}

    def handle_pix_payment(self, telegram_id: str, valor: float) -> Dict:
        """Processa um pagamento PIX."""
        try:
            metade_valor = math.ceil(float(valor) / 2)
            
            # Simulando geração bem-sucedida do PIX
            pix_payment = {
                'transaction': {
                    'transactionId': '348230287987948',
                    'qrcode': '00020126580014BR.GOV.BCB.PIX0136123e4567-e89b-12d3-a456-426614174000520400005303986540510.005802BR5913Teste%20Loja%206008BRASILIA62070503***6304E2CA',
                    'amount': metade_valor
                }
            }
            
            # Código original comentado
            # url = f"https://www.riodejaneiropg.com/create_payment_pixup?price={metade_valor}"
            # response = requests.get(url)
            # if response.status_code == 200:
            #     pix_payment = response.json()
            # else:
            #     return None

            if not pix_payment:
                return {"success": False, "message": "Erro ao criar pagamento PIX"}

            transaction_id = pix_payment['transaction']['transactionId']
            price = pix_payment['transaction']['amount']
            option = 'eng.WEPINK'

            # Atualiza dados do usuário
            user_data = {
                "field_2809288": None,
                "field_2806412": telegram_id,
                "field_2806415": transaction_id,
                "field_2806416": None,
                "field_2806417": "NONE",
                "field_2806418": price,
                "field_2809452": option,
            }

            # Atualiza dados de pagamento
            new_data = {
                "payment_cod": pix_payment['transaction']['qrcode'],
            }
            update_user_data(telegram_id, new_data, TABLE_NAME)
            create_new_transactionController(user_data, TABLE_NAME)

            return {
                "success": True,
                "payment_data": pix_payment,
                "link": f"https://paymenthwepink.com/pagepayment/index.html?&ID={telegram_id}"
            }
        except Exception as e:
            logger.error(f"Erro ao processar pagamento PIX: {e}")
            return {"success": False, "message": str(e)}

    def create_pix_payment(self, valor: float) -> Optional[Dict]:
        """Cria um pagamento PIX."""
        try:
            url = f"https://www.riodejaneiropg.com/create_payment_pixup?price={valor}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Erro ao criar pagamento PIX: {e}")
            return None

    def handle_requires_action(self, run_status: Dict, thread_id: str, telegram_id: str) -> str:
        """Processa ações requeridas pelo assistente."""
        try:
            action_name = run_status['data'][0]['required_action']['submit_tool_outputs']['tool_calls'][0]['function']['name']
            
            if action_name == 'solicitar_info_pix':
                user_data = get_all_user_data(telegram_id, TABLE_NAME)
                result = self.handle_pix_payment(telegram_id, user_data['valor'])
                
                if result['success']:
                    self.send_payment_messages(telegram_id, result['link'])
                    self.submit_tool_outputs(thread_id, run_status, result['payment_data'])
                    return "Pagamento PIX gerado com sucesso!"
                return "Erro ao gerar pagamento PIX"

            elif action_name == 'consultar_pagamento':
                return get_last_payment_idController(telegram_id)

            elif action_name == 'request_data':
                user_data = get_all_user_data(telegram_id, TABLE_NAME)
                self.submit_tool_outputs(thread_id, run_status, user_data)
                return "Dados do usuário enviados com sucesso!"

            return "Ação não reconhecida"
        except Exception as e:
            logger.error(f"Erro ao processar ação requerida: {e}")
            return f"Erro ao processar ação: {str(e)}"

    def submit_tool_outputs(self, thread_id: str, run_status: Dict, data: Dict) -> bool:
        """Submete outputs de ferramentas para o assistente."""
        try:
            run_id = run_status['data'][0]['id']
            tool_call_id = run_status['data'][0]['required_action']['submit_tool_outputs']['tool_calls'][0]['id']
            
            url = f"{self.api_url}/{thread_id}/runs/{run_id}/submit_tool_outputs"
            body = {
                "tool_outputs": [{
                    "tool_call_id": tool_call_id,
                    "output": json.dumps(data)
                }]
            }
            
            response = requests.post(url, headers=self.headers, json=body)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao submeter outputs: {e}")
            return False

    def send_payment_messages(self, telegram_id: str, payment_link: str) -> None:
        """Envia mensagens relacionadas ao pagamento."""
        try:
            print(f"\n[PAGAMENTO] ================================================")
            print(f"[PAGAMENTO] Iniciando envio de mensagens de pagamento para: {telegram_id}")
            
            messages = [
                "Certo, so um momento que vou estar gerando o pagamento PIX. Caso tenha alguma duvida em como realizar o pagamento do Pix Copia e Cola so me avisar.",
                "Você pode também pagar via link, estou te enviandon tanto o link para facilitar quanto o pix Copia e Cola direto.",
                payment_link
            ]
            
            for i, message in enumerate(messages, 1):
                print(f"[PAGAMENTO] Enviando mensagem {i}/{len(messages)}")
                send_message_with_retry(telegram_id, message)
                if i < len(messages):  # Não espera após a última mensagem
                    time.sleep(5)
                    print(f"[PAGAMENTO] Aguardando 5 segundos antes da próxima mensagem")
            
            print(f"[PAGAMENTO] Todas as mensagens enviadas com sucesso")
            print(f"[PAGAMENTO] ================================================\n")
                
        except Exception as e:
            print(f"[PAGAMENTO] Erro ao enviar mensagens de pagamento: {e}")
            print(f"[PAGAMENTO] ================================================\n")
            logger.error(f"Erro ao enviar mensagens de pagamento: {e}")

    def preprocessar_mensagem(self, mensagem: Union[str, Dict]) -> str:
        """Pré-processa a mensagem do usuário"""
        if isinstance(mensagem, dict):
            mensagem = mensagem.get('text', '')
        
        # Converte para minúsculas
        mensagem = mensagem.lower()
        
        # Remove pontuação
        mensagem = mensagem.translate(str.maketrans('', '', string.punctuation))
        
        # Remove espaços extras
        mensagem = ' '.join(mensagem.split())
        
        return mensagem

    def verificar_resposta_cache(self, pergunta: str, resposta: str, contexto: Dict, score_similaridade: float) -> bool:
        """
        Verifica se uma resposta do cache é relevante usando um modelo híbrido.
        
        Args:
            pergunta: Pergunta atual do usuário
            resposta: Resposta do cache
            contexto: Contexto atual da conversa
            score_similaridade: Score de similaridade semântica (0-1)
            
        Returns:
            bool: True se a resposta for relevante, False caso contrário
        """
        try:
            print(f"\n[VERIFICAÇÃO CACHE] Iniciando verificação híbrida")
            print(f"[VERIFICAÇÃO CACHE] Score de similaridade semântica: {score_similaridade}")
            
            # 1. Verificação de palavras-chave (30% do peso)
            palavras_chave = set(pergunta.lower().split())
            palavras_resposta = set(resposta.lower().split())
            palavras_comuns = palavras_chave.intersection(palavras_resposta)
            
            # Calcula o percentual de palavras-chave em comum
            percentual_palavras = len(palavras_comuns) / len(palavras_chave) if palavras_chave else 0
            print(f"[VERIFICAÇÃO CACHE] Score de palavras-chave: {percentual_palavras}")
            
            # 2. Verificação de contexto (20% do peso)
            score_contexto = 0.0
            if contexto.get("product_info", {}).get("interests"):
                produto_interesse = contexto["product_info"]["interests"][0]
                if produto_interesse.lower() in resposta.lower():
                    score_contexto = 1.0
            print(f"[VERIFICAÇÃO CACHE] Score de contexto: {score_contexto}")
            
            # 3. Verificação de intenção (10% do peso)
            score_intencao = 0.0
            intencao_atual = contexto.get("conversation_state", {}).get("current_intent")
            if intencao_atual == "price_inquiry" and ("R$" in resposta or "valor" in resposta.lower()):
                score_intencao = 1.0
            print(f"[VERIFICAÇÃO CACHE] Score de intenção: {score_intencao}")
            
            # 4. Verificação de tópico (10% do peso)
            score_topico = 0.0
            ultimo_topico = contexto.get("conversation_state", {}).get("last_topic")
            if ultimo_topico and ultimo_topico.lower() in resposta.lower():
                score_topico = 1.0
            print(f"[VERIFICAÇÃO CACHE] Score de tópico: {score_topico}")
            
            # 5. Cálculo do score final ponderado
            score_final = (
                0.4 * score_similaridade +  # Similaridade semântica (40%)
                0.3 * percentual_palavras +  # Palavras-chave (30%)
                0.2 * score_contexto +      # Contexto (20%)
                0.1 * score_intencao +      # Intenção (10%)
                0.0 * score_topico          # Tópico (0% - apenas para debug)
            )
            
            print(f"[VERIFICAÇÃO CACHE] Score final ponderado: {score_final}")
            
            # 6. Verifica se o score final está acima do threshold
            if score_final >= 0.8:
                print(f"[VERIFICAÇÃO CACHE] Resposta aprovada com score {score_final:.2f}")
                return True
            else:
                print(f"[VERIFICAÇÃO CACHE] Resposta rejeitada com score {score_final:.2f}")
                return False
                
        except Exception as e:
            print(f"[VERIFICAÇÃO CACHE] Erro na verificação: {e}")
            return False

    def process_user_message(self, telegram_id: str, user_message: Union[str, Dict]) -> str:
        try:
            print(f"\n[DEBUG] Iniciando processamento da mensagem")
            print(f"[DEBUG] Mensagem original: {user_message}")
            
            # 1. Pré-processa a mensagem
            if isinstance(user_message, dict):
                print(f"[DEBUG] Mensagem é um dicionário")
                mensagem_processada = self.preprocessar_mensagem(user_message.get('text', ''))
            else:
                print(f"[DEBUG] Mensagem é uma string")
            mensagem_processada = self.preprocessar_mensagem(user_message)
            
            print(f"[DEBUG] Mensagem processada: {mensagem_processada}")
            
            # 2. Obtém o contexto do cache
            print(f"[DEBUG] Obtendo contexto do cache")
            try:
                contexto_cache = self.cache.preparar_contexto(pergunta=mensagem_processada)
                print(f"[DEBUG] Contexto obtido: {contexto_cache}")
            except Exception as e:
                print(f"[DEBUG] Erro ao obter contexto do cache: {e}")
                raise
            
            # 3. Obtém o contexto do usuário usando o novo gerenciador
            print(f"[DEBUG] Obtendo contexto do usuário")
            user_context = self.context_manager.get_user_context(telegram_id)
            print(f"[DEBUG] Contexto do usuário: {user_context}")
            
            # 4. Verifica se é primeira mensagem baseado no histórico
            is_first_message = user_context["user_info"]["total_interactions"] == 0
            print(f"[DEBUG] É primeira mensagem? {is_first_message}")
            
            # 5. Identifica intenção de compra
            print(f"[DEBUG] Identificando intenção de compra")
            purchase_intent = self.identify_purchase_intent(user_message, user_context)
            print(f"[DEBUG] Intenção de compra: {purchase_intent}")
            
            # 6. Verifica se temos todas as informações necessárias para gerar o PIX
            if purchase_intent["has_intent"] and purchase_intent["product_info"]:
                print(f"[DEBUG] Intenção de compra detectada, verificando informações do produto")
                product_info = purchase_intent["product_info"]
                if all(product_info.get(key) for key in ["nome", "preco", "quantidade"]):
                    print(f"[DEBUG] Todas as informações do produto disponíveis, gerando PIX")
                    return self.gerar_resposta_pix(product_info)
            
            # 7. Verifica se temos uma resposta em cache
            if contexto_cache and isinstance(contexto_cache, str) and len(contexto_cache.strip()) > 0:
                # Obtém o score de similaridade do cache
                score_similaridade = self.cache.calcular_similaridade(mensagem_processada, contexto_cache)
                print(f"[DEBUG] Score de similaridade do cache: {score_similaridade}")
                
                # Verifica se a resposta do cache é relevante
                if self.verificar_resposta_cache(mensagem_processada, contexto_cache, user_context, score_similaridade):
                    print(f"[DEBUG] Resposta do cache aprovada")
                    self.context_manager.update_user_context(telegram_id, mensagem_processada, contexto_cache)
                    return contexto_cache
                else:
                    print(f"[DEBUG] Resposta do cache não aprovada, continuando com o fluxo normal")
            
            # 8. Se não tiver resposta em cache ou a resposta não for relevante, continua com o fluxo normal da OpenAI
            print("[DEBUG] Iniciando processamento com OpenAI")
            try:
                resposta = self.gerar_resposta_assistente(
                    mensagem_processada,
                    contexto_cache,
                    user_context,
                    is_first_message
                )
                print(f"[DEBUG] Resposta gerada: {resposta}")
                
                # 9. Atualiza o contexto do usuário
                print(f"[DEBUG] Atualizando contexto do usuário")
                self.context_manager.update_user_context(
                    telegram_id,
                    mensagem_processada,
                    resposta
                )
                
                return resposta
                
            except Exception as e:
                print(f"[DEBUG] Erro ao gerar resposta: {e}")
                raise

        except Exception as e:
            print(f"[PROCESSAMENTO] Erro ao processar mensagem: {e}")
            return "Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."

    def prepare_context_prompt(self, user_context: Dict,contexto_cache ,current_message: str, is_first_message: bool) -> str:
        """Prepara o prompt com base no contexto da conversa."""
        print(f"\n[PROMPT] Preparando prompt com contexto")
        print(f"[PROMPT] É primeira mensagem? {is_first_message}")
        print(f"[PROMPT] Contexto atual: {user_context}")
        
        prompt_parts = []
        
        # Instruções sobre saudação
        if is_first_message:
            print("[PROMPT] Adicionando instruções para primeira mensagem")
            prompt_parts.append("Esta é a primeira mensagem do usuário. Dê as boas-vindas de forma amigável e apresente-se como Paula da Suplementos Power.")
        else:
            print("[PROMPT] Adicionando instruções para mensagens subsequentes22222222222222222222")
            prompt_parts.append("Continue a conversa de forma natural, mantendo o contexto anterior. Não inicie com saudação pois já foi dada anteriormente.")
        
        # Identifica intenção de compra
        purchase_intent = self.identify_purchase_intent(current_message, user_context)
        if purchase_intent["has_intent"]:
            print("[PROMPT] Intenção de compra identificada")
            product_info = purchase_intent["product_info"]
            
            if product_info["missing_info"]:
                print("[PROMPT] Faltam informações do produto")
                prompt_parts.append("O usuário demonstrou interesse em comprar um produto, mas precisamos confirmar algumas informações:")
                for info in product_info["missing_info"]:
                    if info == "marca":
                        prompt_parts.append("- Qual marca do produto você deseja?")
                    elif info == "tamanho":
                        prompt_parts.append("- Qual tamanho você quer?")
                    elif info == "valor":
                        prompt_parts.append("- Qual o valor do produto?")
            else:
                print("[PROMPT] Todas as informações do produto estão disponíveis")
                prompt_parts.append(f"O usuário quer comprar o seguinte produto: {product_info['marca']} {product_info['tamanho']} no valor de R$ {product_info['valor']:.2f}. Gere um PIX para este produto.")
        
        # Último tópico discutido
        if user_context["conversation_state"]["last_topic"]:
            print(f"[PROMPT] Adicionando último tópico: {user_context['conversation_state']['last_topic']}")
            prompt_parts.append(f"O último tópico discutido foi: {user_context['conversation_state']['last_topic']}")
        
        # Interesse em produto
        if user_context["product_info"]["interests"]:
            print(f"[PROMPT] Adicionando interesses em produtos: {user_context['product_info']['interests']}")
            prompt_parts.append(f"O usuário demonstrou interesse em: {', '.join(user_context['product_info']['interests'])}")
        print(f"CHEGOU ATE AQUI25151")
        # Fase da conversa
        if user_context["conversation_state"]["conversation_phase"]:
            print(f"[PROMPT] Adicionando fase da conversa: {user_context['conversation_state']['conversation_phase']}")
            print(f"CHEGOU ATE AQUI55")
            prompt_parts.append(f"A conversa está na fase: {user_context['conversation_state']['conversation_phase']}")
            print(f"CHEGOU ATE AQUI6")
        
        # Histórico recente
        if user_context["interaction_history"]["questions"] and user_context["interaction_history"]["answers"]:
            print(f"CHEGOU ATE AQUI4")
            print("[PROMPT] Adicionando histórico recente da conversa")
            prompt_parts.append("Histórico recente da conversa:")
            for q, a in zip(user_context["interaction_history"]["questions"][-2:], user_context["interaction_history"]["answers"][-2:]):
                prompt_parts.append(f"Usuário: {q}")
                prompt_parts.append(f"Assistente: {a}")
        print(f"CHEGOU ATE AQUI1")
        prompt_parts.append(contexto_cache)
        prompt_final = "\n".join(prompt_parts)
        print(f"CHEGOU ATE AQUI2")
        print(f"[PROMPT] Prompt final preparado: {prompt_final}")
        return prompt_final

    def extract_topic(self, message: Union[str, Dict]) -> str:
        """Extrai o tópico principal da mensagem"""
        # Se a mensagem for um dicionário, extrai o texto
        if isinstance(message, dict):
            message = message.get('text', '')
        
        message = message.lower()
        if "whey" in message:
            return "whey protein"
        elif "creatina" in message:
            return "creatina"
        elif "pré-treino" in message:
            return "pré-treino"
        elif "bcaa" in message:
            return "bcaa"
        elif "hipercalórico" in message or "hipercalorico" in message:
            return "hipercalórico"
        elif "crescer" in message or "massa" in message or "muscular" in message:
            return "ganho de massa"
        elif "emagrecer" in message or "perda de peso" in message:
            return "emagrecimento"
        return "geral"

    def extract_product_interest(self, message: Union[str, Dict]) -> str:
        """Extrai o interesse em produto da mensagem"""
        # Se a mensagem for um dicionário, extrai o texto
        if isinstance(message, dict):
            message = message.get('text', '')
        
        message = message.lower()
        if "whey" in message:
            return "whey protein"
        elif "creatina" in message:
            return "creatina"
        elif "pré-treino" in message:
            return "pré-treino"
        elif "bcaa" in message:
            return "bcaa"
        elif "hipercalórico" in message or "hipercalorico" in message:
            return "hipercalórico"
        return None

    def determine_conversation_phase(self, message: Union[str, Dict]) -> str:
        """Determina a fase da conversa"""
        # Se a mensagem for um dicionário, extrai o texto
        if isinstance(message, dict):
            message = message.get('text', '')
        
        message = message.lower()
        if "preço" in message or "quanto" in message or "valor" in message:
            return "price_inquiry"
        elif "comprar" in message or "pagamento" in message or "pix" in message:
            return "checkout"
        elif "crescer" in message or "massa" in message or "muscular" in message:
            return "product_inquiry"
        return "initial"

    def should_generate_pix(self, user_context: Dict, current_message: str, assistant_response: str) -> bool:
        """Verifica se devemos gerar um PIX baseado no contexto e mensagens"""
        try:
            # Se a mensagem atual contém palavras-chave de compra
            palavras_compra = ["quero", "vou pegar", "vou levar", "comprar", "pedir", "adquirir"]
            mensagem = current_message.lower()
            if any(palavra in mensagem for palavra in palavras_compra):
                # Verifica se já temos um produto de interesse no contexto
                if user_context.get("product_interest"):
                    # Verifica se a mensagem atual contém especificações do produto
                    produto_info = self.extract_product_info(current_message)
                    return not produto_info["duvidas"] and produto_info["valor"]
            return False
        except Exception as e:
            print(f"[PIX] Erro ao verificar geração de PIX: {e}")
            return False

    def has_sufficient_product_info(self, user_context: Dict, current_message: str) -> Dict:
        """Verifica se temos informações suficientes sobre o produto desejado.
        
        Args:
            user_context: Contexto atual da conversa
            current_message: Mensagem atual do usuário
            
        Returns:
            Dict com informações sobre o produto e se precisamos de mais dados
        """
        try:
            # Extrai informações do produto da mensagem
            produto_info = {
                "marca": None,
                "tamanho": None,
                "sabor": None,
                "valor": None,
                "duvidas": [],
                "produtos_similares": []
            }
            
            # Lista de marcas conhecidas
            marcas = ["growth", "integralmedica", "max titanium", "universal", "optimum"]
            
            # Lista de tamanhos comuns
            tamanhos = ["900g", "1kg", "2kg", "2.5kg", "5kg"]
            
            # Converte mensagem para minúsculas
            mensagem = current_message.lower()
            
            # Verifica marca
            for marca in marcas:
                if marca in mensagem:
                    produto_info["marca"] = marca
                    break
            if not produto_info["marca"]:
                produto_info["duvidas"].append("marca")
            
            # Verifica tamanho
            for tamanho in tamanhos:
                if tamanho in mensagem:
                    produto_info["tamanho"] = tamanho
                    break
            if not produto_info["tamanho"]:
                produto_info["duvidas"].append("tamanho")
            
            # Verifica se temos o valor no contexto anterior
            if user_context.get("last_answers"):
                for resposta in user_context["last_answers"]:
                    if "R$" in resposta:
                        # Extrai o valor da resposta
                        import re
                        valor_match = re.search(r'R\$\s*(\d+[,.]\d+)', resposta)
                        if valor_match:
                            produto_info["valor"] = float(valor_match.group(1).replace(',', '.'))
                        break
            
            if not produto_info["valor"]:
                produto_info["duvidas"].append("valor")
            
            # Se temos todas as informações necessárias
            if not produto_info["duvidas"]:
                return {
                    "sucesso": True,
                    "produto": produto_info
                }
            
            # Se faltam informações, busca produtos similares no banco
            if produto_info["marca"]:
                # Aqui você implementaria a busca no banco de dados
                # Por enquanto, vamos simular alguns produtos similares
                produto_info["produtos_similares"] = [
                    {"marca": produto_info["marca"], "tamanho": "900g", "valor": 99.90},
                    {"marca": produto_info["marca"], "tamanho": "2kg", "valor": 199.90}
                ]
            
            return {
                "sucesso": False,
                "produto": produto_info
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar informações do produto: {e}")
            return {
                "sucesso": False,
                "produto": None,
                "erro": str(e)
            }

    def get_product_value_from_db(self, marca: str, tamanho: str) -> Optional[float]:
        """Busca o valor correto do produto no banco de dados."""
        try:
            # Busca os dados do produto no cache usando a query formatada
            query = f"{marca} {tamanho}"
            print(f"entrou no get_produtct do open")
            produtos = self.cache.buscar_produtos_relevantes(query)
            print(f"{produtos}")
            
            # Se encontrou produtos, pega o primeiro (mais relevante)
            if produtos and len(produtos) > 0:
                produto = produtos[0]
                if 'valor' in produto:
                    return float(produto['valor'])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar valor do produto: {e}")
            return None

    def identify_purchase_intent(self, user_message: Union[str, Dict], user_context: Dict) -> Dict:
        """Identifica se há intenção de compra na mensagem e extrai informações relevantes."""
        try:
            # Se a mensagem for um dicionário, extrai o texto
            if isinstance(user_message, dict):
                user_message = user_message.get('text', '')
            
            # Converte mensagem para minúsculas
            mensagem = user_message.lower()
            
            # Extrai informações do produto
            product_info = {
                "marca": None,
                "tamanho": None,
                "sabor": None,
                "valor": None,
                "missing_info": []
            }
            
            # Lista de marcas conhecidas
            marcas = ["growth", "integralmedica", "max titanium", "universal", "optimum"]
            
            # Verifica se há intenção de compra
            has_purchase_intent = False
            
            # 1. Verifica palavras-chave explícitas de compra
            purchase_keywords = [
                "quero comprar", "vou comprar", "quero adquirir", "vou adquirir",
                "quero levar", "vou levar", "quero pegar", "vou pegar",
                "quero pedir", "vou pedir", "quero encomendar", "vou encomendar",
                "quero o", "vou levar o", "o de", "vou levar o de", "quero o de",
                "vou querer", "quero querer", "vou levar o", "quero levar o"
            ]
            
            has_purchase_intent = any(keyword in mensagem for keyword in purchase_keywords)
            
            # 2. Verifica se é uma resposta a uma pergunta sobre produto
            if not has_purchase_intent and user_context.get("last_answers"):
                last_answer = user_context["last_answers"][-1].lower()
                question_keywords = [
                    "qual dessas opções", "qual tamanho", "qual você prefere",
                    "qual você gostaria", "qual você quer", "qual você vai levar",
                    "qual você vai pegar", "qual você vai comprar", "qual deles"
                ]
                has_purchase_intent = any(keyword in last_answer for keyword in question_keywords)
            
            # 3. Verifica se há menção a números ou tamanhos na mensagem
            if not has_purchase_intent:
                import re
                # Procura por qualquer número seguido opcionalmente por unidade de medida
                if re.search(r'\d+\s*(?:k|kg|g|ml|l)?', mensagem):
                    has_purchase_intent = True
            
            if not has_purchase_intent:
                return {
                    "has_intent": False,
                    "product_info": None
                }
            
            # Extrai informações do produto da mensagem atual
            # Marca
            for marca in marcas:
                if marca in mensagem:
                    product_info["marca"] = marca
                    break
            
            # Tamanho - Lógica genérica
            import re
            
            # 1. Primeiro tenta encontrar um tamanho completo na mensagem
            # Padrão para capturar números seguidos de unidades de medida
            size_pattern = r'(\d+(?:[,.]\d+)?)\s*(k|kg|g|ml|l)'
            size_match = re.search(size_pattern, mensagem)
            if size_match:
                number, unit = size_match.groups()
                # Normaliza a unidade
                if unit in ['k', 'kg']:
                    unit = 'kg'
                elif unit in ['ml', 'l']:
                    unit = 'ml'
                product_info["tamanho"] = f"{number}{unit}"
            
            # Se não encontrou informações na mensagem atual, tenta extrair do contexto
            if not product_info["marca"] or not product_info["tamanho"]:
                if user_context.get("last_answers"):
                    for resposta in user_context["last_answers"]:
                        resposta = resposta.lower()
                        
                        # Extrai marca do contexto
                        if not product_info["marca"]:
                            for marca in marcas:
                                if marca in resposta:
                                    product_info["marca"] = marca
                                    break
                        
                        # Extrai tamanho do contexto
                        if not product_info["tamanho"]:
                            # Se a mensagem atual contém um número, procura por esse número no contexto
                            number_match = re.search(r'\d+(?:[,.]\d+)?', mensagem)
                            if number_match:
                                number = number_match.group()
                                # Procura por padrões como "5kg" ou "5 kg" no contexto
                                size_pattern = rf"{number}\s*(k|kg|g|ml|l)"
                                size_match = re.search(size_pattern, resposta)
                                if size_match:
                                    unit = size_match.group(1)
                                    # Normaliza a unidade
                                    if unit in ['k', 'kg']:
                                        unit = 'kg'
                                    elif unit in ['ml', 'l']:
                                        unit = 'ml'
                                    product_info["tamanho"] = f"{number}{unit}"
                            else:
                                # Se não tem número na mensagem atual, procura por qualquer tamanho no contexto
                                size_match = re.search(r'(\d+(?:[,.]\d+)?)\s*(k|kg|g|ml|l)', resposta)
                                if size_match:
                                    number, unit = size_match.groups()
                                    # Normaliza a unidade
                                    if unit in ['k', 'kg']:
                                        unit = 'kg'
                                    elif unit in ['ml', 'l']:
                                        unit = 'ml'
                                    product_info["tamanho"] = f"{number}{unit}"
                        
                        # Se encontrou ambas as informações, pode parar
                        if product_info["marca"] and product_info["tamanho"]:
                            break
            
            # Verifica se temos o valor no contexto anterior
            if user_context.get("last_answers"):
                for resposta in user_context["last_answers"]:
                    if "R$" in resposta:
                        import re
                        # Procura por padrões como "5kg: R$ 140,36" ou "5kg custa R$ 140,36"
                        if product_info["tamanho"]:
                            # Primeiro tenta encontrar o valor específico para o tamanho escolhido
                            valor_match = re.search(rf"{product_info['tamanho']}.*?R\$\s*(\d+[,.]\d+)", resposta)
                            if valor_match:
                                product_info["valor"] = float(valor_match.group(1).replace(',', '.'))
                                break
                        
                            # Se não encontrou, procura por qualquer valor na resposta
                            valor_match = re.search(r'R\$\s*(\d+[,.]\d+)', resposta)
                            if valor_match:
                                product_info["valor"] = float(valor_match.group(1).replace(',', '.'))
            
            # Se temos marca e tamanho, busca o valor correto no banco
            if product_info["marca"] and product_info["tamanho"]:
                valor_correto = self.get_product_value_from_db(product_info["marca"], product_info["tamanho"])
                if valor_correto:
                    product_info["valor"] = valor_correto
            
            # Verifica informações faltantes
            if not product_info["marca"]:
                product_info["missing_info"].append("marca")
            if not product_info["tamanho"]:
                product_info["missing_info"].append("tamanho")
            if not product_info["valor"]:
                product_info["missing_info"].append("valor")
            
            return {
                "has_intent": True,
                "product_info": product_info
            }
            
        except Exception as e:
            logger.error(f"Erro ao identificar intenção de compra: {e}")
            return {
                "has_intent": False,
                "product_info": None,
                "error": str(e)
            }

    def gerar_resposta_pix(self, product_info: Dict) -> str:
        """
        Gera resposta para pagamento PIX.
        
        Args:
            product_info: Informações do produto
            
        Returns:
            str: Resposta formatada
        """
        try:
            print(f"\n[PIX] Iniciando geração de PIX")
            print(f"[PIX] Produto: {product_info['nome']}")
            print(f"[PIX] Valor: R$ {product_info['preco']}")
            
            pix_payment = self.handle_pix_payment(product_info['telegram_id'], product_info['preco'])
            
            if pix_payment["success"]:
                # Envia mensagens de pagamento
                self.send_payment_messages(product_info['telegram_id'], pix_payment["link"])
                
                # Atualiza o contexto
                self.context_manager.update_user_context(
                    product_info['telegram_id'],
                    f"Gerar PIX para {product_info['nome']}",
                    f"PIX gerado para {product_info['nome']}"
                )
                
                return f"Pagamento PIX gerado com sucesso para {product_info['nome']} no valor de R$ {product_info['preco']:.2f}! Por favor, verifique suas mensagens para o QR Code do PIX."
            else:
                error_msg = "Desculpe, ocorreu um erro ao gerar o PIX. Por favor, tente novamente em alguns instantes."
                self.context_manager.update_user_context(
                    product_info['telegram_id'],
                    f"Gerar PIX para {product_info['nome']}",
                    error_msg
                )
                return error_msg
                
        except Exception as e:
            print(f"[PIX] Erro ao gerar PIX: {e}")
            return "Ocorreu um erro ao gerar o PIX. Por favor, tente novamente."

    def gerar_resposta_assistente(self, mensagem: str, contexto_cache: str, user_context: Dict, is_first_message: bool) -> str:
        """
        Gera resposta usando o assistente da OpenAI.
        
        Args:
            mensagem: Mensagem do usuário
            contexto_cache: Contexto do cache
            user_context: Contexto do usuário
            is_first_message: Se é primeira mensagem
            
        Returns:
            str: Resposta do assistente
        """
        try:
            print(f"\n[ASSISTENTE] Iniciando geração de resposta")
            
            # Prepara o prompt com contexto
            context_prompt = self.prepare_context_prompt(user_context,contexto_cache ,mensagem, is_first_message)
            
            # Combina o contexto do cache com o contexto da conversa
            mensagem_com_contexto = f"{context_prompt}\n\nMensagem do usuário: {mensagem}"
            
            # Obtém ou cria thread_id
            thread_id = self.get_thread_id(user_context['user_info']['telegram_id'])
            if not thread_id:
                thread_id = self.create_thread()
                if not thread_id:
                    raise Exception("Erro ao criar thread")
                self.update_thread_id(user_context['user_info']['telegram_id'], thread_id)
            
            # Verifica o status atual da run
            run_status = self.get_run_status(thread_id)
            print(f"[ASSISTENTE] Status atual da run: {run_status}")
            
            # Se não há run ou a run anterior está completa/expired, cria nova mensagem e run
            if not run_status or 'data' not in run_status or not run_status['data'] or run_status['data'][0]['status'] in ['completed', 'expired', 'failed']:
                message = self.create_user_message(thread_id, mensagem_com_contexto)
                if not message:
                    raise Exception("Erro ao criar mensagem")
                self.create_run(thread_id)
                time.sleep(2)
                run_status = self.get_run_status(thread_id)
            
            # Processa o status do run
            if not run_status or 'data' not in run_status or not run_status['data']:
                raise Exception("Erro ao processar mensagem")
            
            status = run_status['data'][0]['status']
            print(f"[ASSISTENTE] Status atual da run: {status}")
            
            if status == 'completed':
                messages = self.get_messages(thread_id)
                if messages and 'data' in messages and messages['data']:
                    return messages['data'][0]['content'][0]['text']['value']
                raise Exception("Erro ao obter resposta da mensagem")
            elif status == 'failed':
                return "Desculpa, não consegui identificar ao certo o que você quis dizer, pode tentar novamente?"
            elif status == 'expired':
                return "A sessão expirou. Por favor, tente novamente."
            elif status == 'queued' or status == 'in_progress':
                # Aguarda a resposta completa
                max_tentativas = 10
                tentativa = 0
                while tentativa < max_tentativas:
                    time.sleep(2)
                    run_status = self.get_run_status(thread_id)
                    if run_status and 'data' in run_status and run_status['data']:
                        status = run_status['data'][0]['status']
                        if status == 'completed':
                            messages = self.get_messages(thread_id)
                            if messages and 'data' in messages and messages['data']:
                                return messages['data'][0]['content'][0]['text']['value']
                        elif status in ['failed', 'expired']:
                            return "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."
                    tentativa += 1
                return "Desculpe, o processamento está demorando mais que o esperado. Por favor, tente novamente."
            else:
                print(f"[ASSISTENTE] Status desconhecido: {status}")
                return "Ocorreu um erro inesperado. Por favor, tente novamente."
                
        except Exception as e:
            print(f"[ASSISTENTE] Erro ao gerar resposta: {e}")
            raise

# Instância global do serviço
openai_service = OpenAIService()  # Usa a instância do cache_manager

# Função principal para uso externo
def process_user_message(telegram_id: str, user_message: str) -> str:
    return openai_service.process_user_message(telegram_id, user_message)