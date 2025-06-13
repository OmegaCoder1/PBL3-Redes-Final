const { ethers } = require("hardhat");
const fs = require('fs');
const path = require('path');
const { artifacts } = require("hardhat");

async function main() {
    console.log("Iniciando deploy do contrato...");
    
    // Verifica a conexão com o Ganache
    const provider = ethers.provider;
    const network = await provider.getNetwork();
    console.log("Rede conectada:", network);
    
    // Obtém a conta que será usada para o deploy
    const [deployer] = await ethers.getSigners();
    console.log("Conta do deployer:", deployer.address);
    console.log("Saldo do deployer:", ethers.formatEther(await provider.getBalance(deployer.address)), "ETH");
    
    // Compila e obtém o contrato
    console.log("Obtendo factory do contrato...");
    const PostoReserva = await ethers.getContractFactory("PostoReserva");
    
    // Faz o deploy
    console.log("Iniciando deploy...");
    const contrato = await PostoReserva.deploy();
    console.log("Aguardando confirmação do deploy...");
    await contrato.waitForDeployment();
    
    const endereco = await contrato.getAddress();
    console.log("Contrato implantado em:", endereco);
    
    // Verifica se o contrato está implantado
    const code = await provider.getCode(endereco);
    if (code === "0x") {
        throw new Error("Contrato não foi implantado corretamente - código vazio");
    }
    console.log("Código do contrato verificado:", code.slice(0, 66) + "...");

    // Obter o ABI do contrato
    console.log("Obtendo ABI do contrato...");
    const artifact = await artifacts.readArtifact("PostoReserva");
    
    // Preparar o objeto com todas as informações necessárias
    const contractData = {
        contrato: endereco,
        abi: artifact.abi
    };
    
    // Garantir que o diretório existe
    const dir = '/shared/centrais_postos';
    console.log("Criando diretório:", dir);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
    
    // Salvar o arquivo contrato.json
    const filePath = path.join(dir, 'contrato.json');
    console.log("Salvando contrato.json em:", filePath);
    fs.writeFileSync(filePath, JSON.stringify(contractData, null, 2));
    
    // Salvar o arquivo PostoReserva_abi.json
    const abiFilePath = path.join(dir, 'PostoReserva_abi.json');
    console.log("Salvando PostoReserva_abi.json em:", abiFilePath);
    fs.writeFileSync(abiFilePath, JSON.stringify(artifact.abi, null, 2));
    
    console.log("Arquivos criados com sucesso!");
    console.log("Conteúdo do contrato.json:", JSON.stringify(contractData, null, 2));
}

main().catch((error) => {
    console.error("Erro durante o deploy:", error);
    process.exitCode = 1;
});
  