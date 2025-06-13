import json
import os
import requests
import time
import sys
from web3 import Web3
import re

def wait_for_ganache():
    """Aguarda o Ganache estar disponível"""
    max_attempts = 30
    attempts = 0
    while attempts < max_attempts:
        try:
            print(f"Tentativa {attempts + 1} de {max_attempts}...")
            response = requests.post('http://ganache:7545',
                                    json={"jsonrpc":"2.0","method":"eth_accounts","params":[],"id":1})
            if response.status_code == 200:
                print("Conexão com Ganache estabelecida!")
                return True
        except Exception as e:
            print(f"Erro ao conectar: {str(e)}")
        time.sleep(2)
        attempts += 1
    raise Exception("Timeout: Ganache não iniciou após 60 segundos")

def get_ganache_accounts():
    print("Conectando ao Ganache para obter contas...")
    w3 = Web3(Web3.HTTPProvider('http://ganache:7545'))
    if not w3.is_connected():
        raise Exception("Não foi possível conectar ao Ganache")
    accounts = w3.eth.accounts
    private_keys = [
        "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d",
        "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1",
        "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c",
        "0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913",
        "0xadd53f9a7e588d003326d1cbf9e4a43c061aadd9bc938c843a79e7b4fd2ad743",
        "0x395df67f0c2d2d9fe1ad08d1bc8b6627011959b79c53d7dd6a3536a33ab8a4fd",
        "0xe485d098507f54e7733a205420dfddbe58db035fa577fc294ebd14db90767a52",
        "0xa453611d9419d0e56f499079478fd72c37b251a94bfde4d19872c44cf65386e3",
        "0x829e924fdf021ba3dbbc4225edfece9aca04b929d6e75613329ca6f1d31c0bb4",
        "0xb0057716d5917badaf911b193b12b910811c1497b5bada8d7711f758981c3773"
    ]
    with open('/shared/private_keys.json', 'w') as f:
        json.dump({'accounts': accounts, 'private_keys': private_keys}, f, indent=2)
    return accounts, private_keys

def update_hardhat_config(account):
    print("Atualizando hardhat.config.js...")
    config_path = '/app/hardhat.config.js'
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Procura por qualquer chave privada no formato correto
    pattern = r'accounts:\s*\[\s*"0x[a-fA-F0-9]+"\s*\]'
    new_content = re.sub(pattern, f'accounts: ["{account}"]', content)
    
    with open(config_path, 'w') as f:
        f.write(new_content)
    print("hardhat.config.js atualizado com sucesso!")

def update_central_files(accounts, private_keys):
    central_files = [
        '/shared/centrais_postos/central_posto1.py',
        '/shared/centrais_postos/central_posto2.py',
        '/shared/centrais_postos/central_posto3.py'
    ]
    print("\n=== Atualizando arquivos das centrais ===")
    for i, file in enumerate(central_files):
        print(f"\nProcessando {file}:")
        print(f"Usando chave privada da conta {i+1}: {private_keys[i+1]}")
        try:
            with open(file, 'r') as f:
                content = f.read()
            pattern = r'PRIVATE_KEY = "0x[0-9a-f]+"'
            new_key = f'PRIVATE_KEY = "{private_keys[i+1]}"'
            content = re.sub(pattern, new_key, content)
            with open(file, 'w') as f:
                f.write(content)
            print(f"✅ Arquivo atualizado com sucesso")
        except Exception as e:
            print(f"❌ Erro ao processar {file}: {str(e)}")
            raise

def update_contract_address():
    """
    Atualiza o endereço do contrato nos arquivos das centrais e cliente.
    Espera encontrar o endereço em /shared/centrais_postos/contrato.json
    """
    print("\n=== Atualizando endereço do contrato nos arquivos das centrais e cliente ===")
    # Tenta ler o endereço do contrato do arquivo JSON gerado pelo Hardhat
    abi_path = '/shared/centrais_postos/contrato.json'
    if not os.path.exists(abi_path):
        print(f"❌ Arquivo {abi_path} não encontrado. O deploy já foi executado?")
        sys.exit(1)
    with open(abi_path, 'r') as f:
        data = json.load(f)
    contract_address = data.get('contrato')
    if not contract_address:
        print("❌ Endereço do contrato não encontrado no arquivo.")
        sys.exit(1)
    print(f"Endereço do contrato encontrado: {contract_address}")

    # Atualiza nos arquivos das centrais
    central_files = [
        '/shared/centrais_postos/central_posto1.py',
        '/shared/centrais_postos/central_posto2.py',
        '/shared/centrais_postos/central_posto3.py'
    ]
    for file in central_files:
        try:
            with open(file, 'r') as f:
                content = f.read()
            pattern = r'CONTRACT_ADDRESS = "0x[0-9a-fA-F]+"'
            new_line = f'CONTRACT_ADDRESS = "{contract_address}"'
            if re.search(pattern, content):
                content = re.sub(pattern, new_line, content)
            else:
                # Se não existir, adiciona no início do arquivo
                content = new_line + "\n" + content
            with open(file, 'w') as f:
                f.write(content)
            print(f"✅ Endereço do contrato atualizado em {file}")
        except Exception as e:
            print(f"❌ Erro ao atualizar {file}: {str(e)}")

    # Atualiza no cliente.py
    cliente_files = ['/shared/cliente.py', '/app/cliente.py', './cliente.py', 'cliente.py']
    cliente_atualizado = False
    for cliente_file in cliente_files:
        if os.path.exists(cliente_file):
            try:
                with open(cliente_file, 'r') as f:
                    content = f.read()
                
                # Atualiza o endereço do contrato
                pattern = r'CONTRACT_ADDRESS = "0x[0-9a-fA-F]+"'
                new_line = f'CONTRACT_ADDRESS = "{contract_address}"'
                if re.search(pattern, content):
                    content = re.sub(pattern, new_line, content)
                else:
                    content = new_line + "\n" + content
                
                with open(cliente_file, 'w') as f:
                    f.write(content)
                print(f"✅ Endereço do contrato atualizado em {cliente_file}")
                cliente_atualizado = True
                break
            except Exception as e:
                print(f"❌ Erro ao atualizar {cliente_file}: {str(e)}")
    
    if not cliente_atualizado:
        print(f"⚠️ Arquivo cliente.py não encontrado em nenhum dos locais esperados.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--update-endereco":
        update_contract_address()
        return
    try:
        print("\n=== Iniciando configuração do blockchain ===")
        print("\n1. Aguardando Ganache iniciar...")
        wait_for_ganache()
        print("\n2. Obtendo contas do Ganache...")
        accounts, private_keys = get_ganache_accounts()
        print("\n3. Atualizando hardhat.config.js...")
        update_hardhat_config(private_keys[0])
        print("\n4. Atualizando arquivos das centrais...")
        update_central_files(accounts, private_keys)
        print("\n=== Configuração concluída com sucesso! ===")
        print("\nResumo das contas configuradas:")
        for i, (account, private_key) in enumerate(zip(accounts, private_keys)):
            print(f"\nConta {i}:")
            print(f"Endereço: {account}")
            print(f"Chave privada: {private_key}")
    except Exception as e:
        print(f"\n❌ Erro durante a configuração: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 