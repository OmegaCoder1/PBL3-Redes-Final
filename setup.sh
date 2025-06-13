#!/bin/bash

echo "Iniciando Ganache..."
docker-compose up -d ganache

# Aguarda o Ganache iniciar e configura as chaves
echo "Configurando blockchain e chaves privadas..."
docker-compose run --rm setup python /app/setup_blockchain.py

echo "Build e deploy do contrato..."
if ! docker-compose run --rm build-contract sh -c "cd /app && node ./node_modules/hardhat/internal/cli/cli.js compile && node ./node_modules/hardhat/internal/cli/cli.js run scripts/deploy.js --network ganache"; then
    echo "❌ Erro durante o build ou deploy do contrato"
    exit 1
fi

echo "Atualizando endereço do contrato nos arquivos..."
docker-compose run --rm setup python /app/setup_blockchain.py --update-endereco

echo "Iniciando os containers..."
docker-compose up -d central1 central2 central3 blockview

echo "Iniciando o cliente em modo interativo..."
docker-compose run --rm cliente

echo "Setup concluído!" 