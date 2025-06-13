import json
import os
import requests
import time
from web3 import Web3
import re

def wait_for_ganache():
    """Aguarda o Ganache estar disponível"""
    max_attempts = 30  # 30 tentativas * 2 segundos = 60 segundos máximo
    attempts = 0
    
    while attempts < max_attempts:
        try:
            print(f"Tentativa {attempts + 1} de {max_attempts}...")
            # Tenta acessar a API do Ganache
            response = requests.post('http://ganache:7545', 
                                  json={"jsonrpc":"2.0","method":"eth_accounts","params":[],"id":1})
            print(f"Status code: {response.status_code}")
            if response.status_code == 200:
                print("Conexão com Ganache estabelecida!")
                return True
        except Exception as e:
            print(f"Erro ao conectar: {str(e)}")
            time.sleep(2)
            attempts += 1
    
    raise Exception("Timeout: Ganache não iniciou após 60 segundos")

def get_ganache_accounts():
    """Obtém as contas do Ganache"""
    print("Conectando ao Ganache para obter contas...")
    w3 = Web3(Web3.HTTPProvider('http://ganache:7545'))
    
    if not w3.is_connected():
        raise Exception("Não foi possível conectar ao Ganache")
    
    print("Conexão estabelecida, obtendo contas...")
    accounts = w3.eth.accounts
    
    # Chaves privadas que o Ganache está gerando
    private_keys = [
        "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d",  # Conta 0
        "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1",  # Conta 1
        "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c",  # Conta 2
        "0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913",  # Conta 3
        "0xadd53f9a7e588d003326d1cbf9e4a43c061aadd9bc938c843a79e7b4fd2ad743",  # Conta 4
        "0x395df67f0c2d2d9fe1ad08d1bc8b6627011959b79c53d7dd6a3536a33ab8a4fd",  # Conta 5
        "0xe485d098507f54e7733a205420dfddbe58db035fa577fc294ebd14db90767a52",  # Conta 6
        "0xa453611d9419d0e56f499079478fd72c37b251a94bfde4d19872c44cf65386e3",  # Conta 7
        "0x829e924fdf021ba3dbbc4225edfece9aca04b929d6e75613329ca6f1d31c0bb4",  # Conta 8
        "0xb0057716d5917badaf911b193b12b910811c1497b5bada8d7711f758981c3773"   # Conta 9
    ]
    
    print(f"Encontradas {len(accounts)} contas")
    print("\nContas disponíveis:")
    for i, (account, private_key) in enumerate(zip(accounts, private_keys)):
        print(f"Conta {i}: {account}")
        print(f"Chave privada: {private_key}\n")
    
    # SALVAR as chaves privadas direto no volume compartilhado
    with open('/shared/private_keys.json', 'w') as f:
        json.dump({
            'accounts': accounts,
            'private_keys': private_keys
        }, f, indent=2)
    
    return accounts, private_keys

def update_hardhat_config(account):
    """Atualiza o arquivo hardhat.config.js com a primeira conta"""
    print("Atualizando hardhat.config.js...")
    with open('hardhat.config.js', 'r') as f:
        content = f.read()
    
    # Atualiza a chave privada
    new_content = content.replace(
        '"0xa17a18175aa1ce3feb02ac11632c27fb8012c48d00af2c6ff9403d50206feb87"',
        f'"{account}"'
    )
    
    with open('hardhat.config.js', 'w') as f:
        f.write(new_content)
    print("hardhat.config.js atualizado com sucesso!")

def update_central_files(accounts, private_keys):
    """Atualiza os arquivos das centrais com as chaves privadas"""
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
                print(f"✅ Arquivo lido com sucesso")
                print(f"Tamanho do arquivo: {len(content)} bytes")
            
            # Procura pela linha que define a chave privada
            pattern = r'PRIVATE_KEY = "0x[0-9a-f]+"'
            new_key = f'PRIVATE_KEY = "{private_keys[i+1]}"'
            
            # Verifica se encontrou a chave atual
            matches = re.findall(pattern, content)
            if matches:
                print(f"Chave atual encontrada: {matches[0]}")
            else:
                print("⚠️ Nenhuma chave atual encontrada no arquivo")
            
            # Substitui a linha que define a chave privada
            content = re.sub(pattern, new_key, content)
            
            with open(file, 'w') as f:
                f.write(content)
                print(f"✅ Arquivo atualizado com sucesso")
            
            # Verifica se a atualização foi bem sucedida
            with open(file, 'r') as f:
                new_content = f.read()
                if new_key in new_content:
                    print(f"✅ Nova chave verificada no arquivo")
                else:
                    raise Exception(f"❌ Nova chave não encontrada no arquivo após atualização")
                
        except Exception as e:
            print(f"❌ Erro ao processar {file}: {str(e)}")
            raise

def main():
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