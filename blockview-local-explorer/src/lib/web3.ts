import Web3 from 'web3';

const RPC_URL = 'http://localhost:7545';

export const web3 = new Web3(RPC_URL);

export interface BlockInfo {
  number: number;
  hash: string;
  timestamp: number;
  transactions: string[];
  gasUsed: number;
  gasLimit: number;
  miner: string;
  parentHash: string;
  size: number;
}

export interface TransactionInfo {
  hash: string;
  from: string;
  to: string;
  value: string;
  gas: number;
  gasPrice: string;
  blockNumber: number;
  blockHash: string;
  transactionIndex: number;
}

export interface NetworkInfo {
  chainId: number;
  blockNumber: number;
  gasPrice: string;
  isConnected: boolean;
  nodeInfo?: string;
}

export interface ReservaInfo {
  cliente_id: string;
  postos_reservados: string[];
  status: string;
  mensagem: string;
  timestamp: number;
}

export const getLatestBlock = async (): Promise<BlockInfo | null> => {
  try {
    const block = await web3.eth.getBlock('latest', true);
    return {
      number: Number(block.number),
      hash: block.hash || '',
      timestamp: Number(block.timestamp),
      transactions: block.transactions?.map(tx => typeof tx === 'string' ? tx : tx.hash) || [],
      gasUsed: Number(block.gasUsed),
      gasLimit: Number(block.gasLimit),
      miner: block.miner || '',
      parentHash: block.parentHash || '',
      size: Number(block.size)
    };
  } catch (error) {
    console.error('Error fetching latest block:', error);
    return null;
  }
};

export const getBlock = async (blockNumber: number): Promise<BlockInfo | null> => {
  try {
    const block = await web3.eth.getBlock(blockNumber, true);
    return {
      number: Number(block.number),
      hash: block.hash || '',
      timestamp: Number(block.timestamp),
      transactions: block.transactions?.map(tx => typeof tx === 'string' ? tx : tx.hash) || [],
      gasUsed: Number(block.gasUsed),
      gasLimit: Number(block.gasLimit),
      miner: block.miner || '',
      parentHash: block.parentHash || '',
      size: Number(block.size)
    };
  } catch (error) {
    console.error('Error fetching block:', error);
    return null;
  }
};

export const getTransaction = async (txHash: string): Promise<TransactionInfo | null> => {
  try {
    const tx = await web3.eth.getTransaction(txHash);
    return {
      hash: tx.hash,
      from: tx.from,
      to: tx.to || '',
      value: tx.value.toString(),
      gas: Number(tx.gas),
      gasPrice: tx.gasPrice?.toString() || '0',
      blockNumber: Number(tx.blockNumber),
      blockHash: tx.blockHash || '',
      transactionIndex: Number(tx.transactionIndex)
    };
  } catch (error) {
    console.error('Error fetching transaction:', error);
    return null;
  }
};

export const getNetworkInfo = async (): Promise<NetworkInfo> => {
  try {
    const [chainId, blockNumber, gasPrice] = await Promise.all([
      web3.eth.getChainId(),
      web3.eth.getBlockNumber(),
      web3.eth.getGasPrice()
    ]);

    return {
      chainId: Number(chainId),
      blockNumber: Number(blockNumber),
      gasPrice: gasPrice.toString(),
      isConnected: true
    };
  } catch (error) {
    console.error('Error fetching network info:', error);
    return {
      chainId: 0,
      blockNumber: 0,
      gasPrice: '0',
      isConnected: false
    };
  }
};

export const formatEther = (value: string): string => {
  return web3.utils.fromWei(value, 'ether');
};

export const formatGwei = (value: string): string => {
  return web3.utils.fromWei(value, 'gwei');
};

export const shortenAddress = (address: string): string => {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

export const getReservaInfo = async (blockNumber: number): Promise<ReservaInfo | null> => {
  try {
    const block = await web3.eth.getBlock(blockNumber, true);
    if (!block || !block.transactions) return null;

    // Busca eventos de resposta no bloco
    const events = await web3.eth.getPastLogs({
      fromBlock: blockNumber,
      toBlock: blockNumber,
      topics: [web3.utils.sha3('RespostaRegistrada(string,string[],bool,string)')]
    });

    if (events.length === 0) return null;

    // Decodifica os dados do evento
    const event = events[0];
    const decodedData = web3.eth.abi.decodeParameters(
      ['string', 'string[]', 'bool', 'string'],
      '0x' + event.data.slice(2)
    );

    return {
      cliente_id: decodedData[0],
      postos_reservados: decodedData[1],
      status: decodedData[2] ? 'Sucesso' : 'Falha',
      mensagem: decodedData[3],
      timestamp: Number(block.timestamp)
    };
  } catch (error) {
    console.error('Error fetching reserva info:', error);
    return null;
  }
};
