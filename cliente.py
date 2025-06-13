CONTRACT_ADDRESS = "0xe78A0F7E598Cc8b0Bb87894B0F60dD2a88d6a8Ab"
from web3 import Web3
import json
import os
import time

def conectar():
    print("\n=== Debug: Iniciando conexão ===")
    # Usa a URL do Ganache da variável de ambiente
    ganache_url = os.getenv('GANACHE_URL', 'http://ganache:7545')
    print(f"URL do Ganache: {ganache_url}")
    
    # Tenta conectar várias vezes
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            print(f"\nTentativa {attempt + 1} de {max_attempts}...")
            web3 = Web3(Web3.HTTPProvider(ganache_url))
            if web3.is_connected():
                print("✅ Conectado ao Ganache")
                break
            else:
                print("❌ Falha na conexão, tentando novamente...")
                time.sleep(2)
        except Exception as e:
            print(f"❌ Erro na tentativa {attempt + 1}: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(2)
            else:
                raise Exception("Não foi possível conectar ao Ganache após várias tentativas")

    # Lê o arquivo contrato.json para obter o endereço do contrato
    print("\n=== Debug: Lendo contrato.json ===")
    contrato_paths = [
        "/app/contrato.json",
        "/shared/centrais_postos/contrato.json",
        "./contrato.json"
    ]
    
    contrato_info = None
    for path in contrato_paths:
        try:
            print(f"Tentando ler contrato.json de: {path}")
            with open(path) as f:
                contrato_info = json.load(f)
                print(f"✅ Contrato carregado de: {path}")
                break
        except Exception as e:
            print(f"❌ Erro ao ler {path}: {str(e)}")
    
    if not contrato_info:
        raise Exception("Não foi possível encontrar o arquivo contrato.json em nenhum dos locais esperados")
    
    contract_address = web3.to_checksum_address(contrato_info["contrato"])
    print(f"Contrato carregado: {contract_address}")

    # Lê o ABI do arquivo PostoReserva_abi.json
    print("\n=== Debug: Lendo PostoReserva_abi.json ===")
    abi_paths = [
        "/shared/centrais_postos/PostoReserva_abi.json",
        "/app/centrais_postos/PostoReserva_abi.json",
        "./centrais_postos/PostoReserva_abi.json"
    ]
    
    abi = None
    for path in abi_paths:
        try:
            print(f"Tentando ler PostoReserva_abi.json de: {path}")
            with open(path) as f:
                abi = json.load(f)  # O ABI já é um array, não precisa acessar ["abi"]
                print(f"✅ ABI carregado de: {path}")
                break
        except Exception as e:
            print(f"❌ Erro ao ler {path}: {str(e)}")
    
    if not abi:
        raise Exception("Não foi possível encontrar o arquivo PostoReserva_abi.json em nenhum dos locais esperados")
    
    print(f"ABI carregado com {len(abi)} funções/eventos")

    print("\n=== Debug: Verificando contrato ===")
    # Verifica se o contrato está implantado
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            print(f"\nTentativa {attempt + 1} de {max_attempts}...")
            code = web3.eth.get_code(contract_address)
            if len(code) > 0:
                print("✅ Contrato encontrado no endereço especificado")
                break
            else:
                print("❌ Contrato não encontrado, tentando novamente...")
                time.sleep(2)
        except Exception as e:
            print(f"❌ Erro na tentativa {attempt + 1}: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(2)
            else:
                raise Exception("Contrato não está implantado no endereço especificado")

    print("\n=== Debug: Instanciando contrato ===")
    contract = web3.eth.contract(address=contract_address, abi=abi)
    print("Contrato instanciado com sucesso!")
    
    # Verifica se o contrato tem as funções necessárias
    print("\n=== Debug: Verificando funções do contrato ===")
    required_functions = ['solicitarRegistro', 'getBloco', 'registrosLength']
    available_functions = [f.fn_name for f in contract.functions]
    print("Funções disponíveis:", available_functions)
    
    for func in required_functions:
        if func not in available_functions:
            print(f"❌ Função {func} não encontrada")
            raise Exception(f"Função {func} não encontrada no contrato")
        print(f"✅ Função {func} encontrada")
    
    # Verifica se o contrato tem os eventos necessários
    print("\n=== Debug: Verificando eventos do contrato ===")
    required_events = ['NovoBloco']
    available_events = [e.event_name for e in contract.events]
    print("Eventos disponíveis:", available_events)
    
    for event in required_events:
        if event not in available_events:
            print(f"❌ Evento {event} não encontrado")
            raise Exception(f"Evento {event} não encontrado no contrato")
        print(f"✅ Evento {event} encontrado")

    return web3, contract

def criar_nova_conta(web3):
    print("\n=== Debug: Criando nova conta ===")
    conta = web3.eth.account.create()
    print("🔐 Nova conta criada:")
    print(f"Endereço: {conta.address}")
    print(f"Chave privada: {conta.key.hex()}")

    # Enviar ETH da conta 0 (ganache) para a nova conta
    print("\n=== Debug: Enviando ETH para nova conta ===")
    conta_rica = web3.eth.accounts[0]
    print(f"Conta rica: {conta_rica}")
    print(f"Saldo da conta rica: {web3.from_wei(web3.eth.get_balance(conta_rica), 'ether')} ETH")
    
    tx_hash = web3.eth.send_transaction({
        "from": conta_rica,
        "to": conta.address,
        "value": web3.to_wei(100, "ether")
    })
    print(f"Transação enviada: {tx_hash.hex()}")
    
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transação confirmada: {'Sucesso' if receipt['status'] == 1 else 'Falha'}")
    print(f"Saldo da nova conta: {web3.from_wei(web3.eth.get_balance(conta.address), 'ether')} ETH")

    return conta

def solicitar_registro(contract, web3, conta, origemX, origemY, destinoX, destinoY, bateria):
    print("\n=== Debug: Informações da Transação ===")
    print(f"Conta: {conta.address}")
    print(f"Saldo da conta: {web3.from_wei(web3.eth.get_balance(conta.address), 'ether')} ETH")
    print(f"Contrato: {contract.address}")
    print(f"Origem: ({origemX}, {origemY})")
    print(f"Destino: ({destinoX}, {destinoY})")
    print(f"Bateria: {bateria}%")
    
    # Obtém o número total de registros antes da transação
    print("\n=== Debug: Estado inicial ===")
    total_antes = contract.functions.registrosLength().call()
    print(f"Total de registros antes: {total_antes}")
    
    print("\n=== Debug: Preparando transação ===")
    nonce = web3.eth.get_transaction_count(conta.address)
    print(f"Nonce: {nonce}")
    
    # Constrói a transação
    tx = contract.functions.solicitarRegistro(
        origemX,
        origemY,
        destinoX,
        destinoY,
        bateria
    ).build_transaction({
        "from": conta.address,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": web3.to_wei("1", "gwei")
    })
    print(f"Gas estimado: {tx['gas']}")
    print(f"Gas price: {web3.from_wei(tx['gasPrice'], 'gwei')} gwei")
    
    print("\n=== Debug: Assinando e enviando transação ===")
    assinado = web3.eth.account.sign_transaction(tx, private_key=conta.key)
    tx_hash = web3.eth.send_raw_transaction(assinado.raw_transaction)
    print(f"Tx Hash: {tx_hash.hex()}")
    
    # Espera a transação ser confirmada
    print("\n⏳ Aguardando confirmação da transação...")
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    print("\n=== Debug: Receipt da Transação ===")
    print(f"Status: {'Sucesso' if receipt['status'] == 1 else 'Falha'}")
    print(f"Block Number: {receipt['blockNumber']}")
    print(f"Gas Used: {receipt['gasUsed']}")
    print(f"Logs: {len(receipt['logs'])}")
    if receipt['logs']:
        print("Detalhes dos logs:")
        for log in receipt['logs']:
            print(f"- Address: {log['address']}")
            print(f"  Topics: {log['topics']}")
            print(f"  Data: {log['data']}")
    
    # Verifica se a transação foi bem sucedida
    if receipt['status'] != 1:
        raise Exception("Transação falhou")
    
    # Obtém o número total de registros depois da transação
    print("\n=== Debug: Estado final ===")
    total_depois = contract.functions.registrosLength().call()
    print(f"Total de registros depois: {total_depois}")
    
    if total_depois > total_antes:
        bloco_id = total_depois - 1
        print(f"\nNovo bloco criado com ID: {bloco_id}")
        
        # Tenta obter informações do bloco
        try:
            bloco = contract.functions.getBloco(bloco_id).call()
            print("\n=== Debug: Informações do Bloco ===")
            print(f"Cliente: {bloco[0]}")
            print(f"Origem: ({bloco[1]}, {bloco[2]})")
            print(f"Destino: ({bloco[3]}, {bloco[4]})")
            print(f"Bateria: {bloco[5]}%")
            print(f"Timestamp: {bloco[6]}")
        except Exception as e:
            print(f"❌ Erro ao obter informações do bloco: {str(e)}")
        
        print("✅ Solicitação registrada!")
        print("Tx Hash:", tx_hash.hex())
        return bloco_id
    else:
        raise Exception("Não foi possível confirmar a criação do novo bloco")

def exibir_bloco(contract, bloco_id):
    print("\n=== Debug: Exibindo bloco ===")
    print(f"Buscando bloco ID: {bloco_id}")
    try:
        bloco = contract.functions.getBloco(bloco_id).call()
        print("\n📍 Bloco ID:", bloco_id)
        print(f"Cliente: {bloco[0]}")
        print(f"Origem: ({bloco[1]}, {bloco[2]})")
        print(f"Destino: ({bloco[3]}, {bloco[4]})")
        print(f"Bateria: {bloco[5]}%")
        print(f"Timestamp: {bloco[6]}")
    except Exception as e:
        print(f"❌ Erro ao exibir bloco: {str(e)}")

def listar_todos_blocos(contract, bloco_id):
    print("\n=== Debug: Listando todos os blocos ===")
    try:
        total = contract.functions.registrosLength().call()
        print(f"Total de blocos: {total}")
        
        i = 0
        while True:
            try:
                bloco = contract.functions.getBloco(i).call()
                print(f"\nBloco ID: {i}")
                if bloco[0] != contract.functions.getBloco(bloco_id).call()[0]:
                    print(f"🔸 Cliente: {bloco[0]}\n📍 Origem: ({bloco[1]}, {bloco[2]}) -> Destino: ({bloco[3]}, {bloco[4]})\n⚡ Bateria: {bloco[5]}%")
                else:
                    print(f"🔹 Cliente: {bloco[0]}\n📍 Origem: ({bloco[1]}, {bloco[2]}) -> Destino: ({bloco[3]}, {bloco[4]})\n⚡ Bateria: {bloco[5]}%")
                i += 1
            except Exception as e:
                print(f"\nTotal de blocos encontrados: {i}")
                break
    except Exception as e:
        print(f"❌ Erro ao listar blocos: {str(e)}")

def listar_eventos(contract):
    print("\n=== Debug: Listando eventos ===")
    try:
        print("📦 Lendo eventos NovoBloco:")
        logs = contract.events.NovoBloco().get_logs(from_block=0)
        print(f"Total de eventos encontrados: {len(logs)}")
        for ev in logs:
            print(f"🔸 Cliente: {ev['args']['cliente']} | Bloco ID: {ev['args']['id']}")
    except Exception as e:
        print(f"❌ Erro ao buscar eventos: {str(e)}")

def main():
    print("\n=== Debug: Iniciando cliente ===")
    web3, contract = conectar()

    #Criando a conta Ethereum do usuário
    conta = criar_nova_conta(web3)
    bloco_id = None

    while True:
        print("\nMenu:")
        print("0 - Indicar rota")
        print("1 - Verificar se há reserva")
        print("2 - Exibir bloco da solicitação de reserva")
        print("3 - Listar todos os blocos")
        print("4 - Sair")

        escolha = input("Escolha uma opção: ")

        if escolha == "0":
            print("\nVocê escolheu: Indicar rota. Por favor informe sua localização atual...")
            try:
                xatual = int(input("X:"))
                yatual = int(input("Y:"))
                print("Informe a localização do destino:")
                xdestino = int(input("X:"))
                ydestino = int(input("Y:"))
            except:
                print("Entrada inválida!")
            bloco_id = solicitar_registro(contract, web3, conta, xatual, yatual, xdestino, ydestino, 100)

        elif escolha == "1":
            print("Você escolheu: Verificar se há reserva\n")
            if bloco_id != None:
                respostas = contract.functions.getRespostas(bloco_id).call()
                for r in respostas:
                    servidor = r[0]
                    sucesso = r[1]
                    motivo = r[2]
                    timestamp = r[3]
                    
                    print(f"📝 Resposta do servidor {servidor} | sucesso: {sucesso} | motivo: {motivo} | timestamp: {timestamp}")
            else:
                print("Você ainda não fez solicitação de reserva.")

        elif escolha == "2":
            print("Você escolheu: Exibir bloco da solicitação de reserva\n")
            if bloco_id != None:
                exibir_bloco(contract, bloco_id)
            else:
                print("Você ainda não fez solicitação de reserva.")

        elif escolha == "3":
            print("Você escolheu: Listar todos os blocos")
            listar_todos_blocos(contract, bloco_id)

        elif escolha == "4":
            print("Saindo...")
            break

        else:
            print("Opção inválida, tente novamente.")


if __name__ == "__main__":
    main()
