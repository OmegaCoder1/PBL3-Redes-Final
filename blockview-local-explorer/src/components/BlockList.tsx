import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getLatestBlock, getBlock, BlockInfo, shortenAddress, getReservaInfo, ReservaInfo } from '@/lib/web3';
import { Clock, Hash, Zap, Users, ArrowRight, CheckCircle, XCircle } from 'lucide-react';

const BlockList = () => {
  const [blocks, setBlocks] = useState<BlockInfo[]>([]);
  const [reservas, setReservas] = useState<{ [key: number]: ReservaInfo }>({});
  const [loading, setLoading] = useState(true);
  const [newBlockIndex, setNewBlockIndex] = useState<number | null>(null);

  useEffect(() => {
    const fetchBlocks = async () => {
      try {
        const latestBlock = await getLatestBlock();
        if (latestBlock) {
          const blockPromises = [];
          const startBlock = Math.max(0, latestBlock.number - 9);
          
          for (let i = latestBlock.number; i >= startBlock; i--) {
            blockPromises.push(getBlock(i));
          }
          
          const fetchedBlocks = await Promise.all(blockPromises);
          const validBlocks = fetchedBlocks.filter(block => block !== null) as BlockInfo[];
          
          // Detectar novo bloco para animação
          if (blocks.length > 0 && validBlocks[0]?.number !== blocks[0]?.number) {
            setNewBlockIndex(0);
            setTimeout(() => setNewBlockIndex(null), 2000);
          }
          
          setBlocks(validBlocks);

          // Buscar informações de reserva para cada bloco
          const reservaPromises = validBlocks.map(block => getReservaInfo(block.number));
          const reservaResults = await Promise.all(reservaPromises);
          const newReservas = { ...reservas };
          validBlocks.forEach((block, index) => {
            if (reservaResults[index]) {
              newReservas[block.number] = reservaResults[index]!;
            }
          });
          setReservas(newReservas);
        }
        setLoading(false);
      } catch (error) {
        console.error('Error fetching blocks:', error);
        setLoading(false);
      }
    };

    fetchBlocks();
    const interval = setInterval(fetchBlocks, 10000);

    return () => clearInterval(interval);
  }, [blocks, reservas]);

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('pt-BR');
  };

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-slate-900 to-gray-900 border-slate-700 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-cyan-500/10 animate-pulse"></div>
        <CardHeader>
          <CardTitle className="text-white">Blocos da Rede Neural</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-32 bg-gradient-to-r from-slate-700/50 to-slate-600/50 rounded-lg border border-slate-600"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="relative">
      {/* Neural Network Background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <svg className="w-full h-full" style={{ filter: 'blur(0.5px)' }}>
          {blocks.slice(0, -1).map((_, index) => (
            <g key={index}>
              {/* Conexões animadas entre blocos */}
              <line
                x1="50%"
                y1={`${(index + 1) * 12 + 8}%`}
                x2="50%"
                y2={`${(index + 2) * 12 + 2}%`}
                stroke="url(#gradient)"
                strokeWidth="2"
                className="animate-pulse"
              >
                <animate
                  attributeName="stroke-dasharray"
                  values="0,100;50,50;100,0"
                  dur="3s"
                  repeatCount="indefinite"
                />
              </line>
              
              {/* Partículas fluindo */}
              <circle r="3" fill="#60a5fa" className="opacity-70">
                <animateMotion
                  dur="4s"
                  repeatCount="indefinite"
                  path={`M 50% ${(index + 1) * 12 + 8}% L 50% ${(index + 2) * 12 + 2}%`}
                />
                <animate
                  attributeName="opacity"
                  values="0;1;0"
                  dur="4s"
                  repeatCount="indefinite"
                />
              </circle>
            </g>
          ))}
          
          <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.8" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <Card className="bg-gradient-to-br from-slate-900/95 to-gray-900/95 border-slate-700 backdrop-blur-sm relative z-10">
        <CardHeader className="relative">
          <CardTitle className="flex items-center space-x-3 text-white">
            <div className="relative">
              <Hash className="h-6 w-6 text-blue-400" />
              <div className="absolute -inset-1 bg-blue-400/20 rounded-full animate-ping"></div>
            </div>
            <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Rede Neural de Blocos
            </span>
          </CardTitle>
          
          {/* Indicador de atividade da rede */}
          <div className="flex items-center space-x-2 mt-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-green-400 text-sm">Rede Ativa</span>
            <div className="flex space-x-1 ml-4">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="w-1 h-4 bg-blue-400 rounded-full animate-pulse"
                  style={{ animationDelay: `${i * 0.2}s` }}
                ></div>
              ))}
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="space-y-6 max-h-96 overflow-y-auto scrollbar-hide">
            {blocks.map((block, index) => {
              const reserva = reservas[block.number];
              return (
                <div
                  key={block.hash}
                  className={`
                    relative group transform transition-all duration-700 ease-out
                    ${newBlockIndex === index ? 'animate-bounce scale-105' : ''}
                    hover:scale-102 hover:z-20
                  `}
                  style={{
                    animationDelay: `${index * 0.1}s`,
                    animation: newBlockIndex === index ? 'slideInScale 0.8s ease-out' : undefined
                  }}
                >
                  {/* Halo de energia */}
                  <div className="absolute -inset-2 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-cyan-500/20 rounded-lg blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                  
                  {/* Bloco principal */}
                  <div className="relative bg-gradient-to-br from-slate-800/90 to-slate-700/90 rounded-lg p-6 border border-slate-600/50 backdrop-blur-sm overflow-hidden">
                    
                    {/* Efeito de circuito */}
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-400 to-transparent opacity-50"></div>
                    <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-400 to-transparent opacity-50"></div>
                    
                    {/* Conexão para o próximo bloco */}
                    {index < blocks.length - 1 && (
                      <div className="absolute -bottom-3 left-1/2 transform -translate-x-1/2 z-10">
                        <div className="w-6 h-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center animate-pulse">
                          <ArrowRight className="h-3 w-3 text-white" />
                        </div>
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <Badge 
                          variant="outline" 
                          className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-blue-300 border-blue-400/50 animate-shimmer"
                        >
                          <div className="w-2 h-2 bg-blue-400 rounded-full mr-2 animate-pulse"></div>
                          Bloco #{block.number}
                        </Badge>
                        <Badge 
                          variant="secondary" 
                          className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border-green-400/50"
                        >
                          <Zap className="h-3 w-3 mr-1" />
                          {block.transactions.length} tx
                        </Badge>
                      </div>
                      <div className="flex items-center space-x-2 text-sm text-slate-400">
                        <Clock className="h-3 w-3" />
                        <span>{formatTimestamp(block.timestamp)}</span>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2 group/item">
                          <Hash className="h-3 w-3 text-slate-400 group-hover/item:text-blue-400 transition-colors" />
                          <span className="text-slate-300">Hash:</span>
                          <code className="text-xs bg-slate-700/50 px-2 py-1 rounded border border-slate-600 font-mono text-blue-300 hover:bg-slate-600/50 transition-colors">
                            {shortenAddress(block.hash)}
                          </code>
                        </div>
                        <div className="flex items-center space-x-2 group/item">
                          <Users className="h-3 w-3 text-slate-400 group-hover/item:text-purple-400 transition-colors" />
                          <span className="text-slate-300">Minerador:</span>
                          <code className="text-xs bg-slate-700/50 px-2 py-1 rounded border border-slate-600 font-mono text-purple-300 hover:bg-slate-600/50 transition-colors">
                            {shortenAddress(block.miner)}
                          </code>
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-300">Gas Usado:</span>
                          <div className="flex items-center space-x-2">
                            <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-gradient-to-r from-yellow-400 to-orange-400 rounded-full transition-all duration-1000"
                                style={{ width: `${(block.gasUsed / block.gasLimit) * 100}%` }}
                              ></div>
                            </div>
                            <span className="font-mono text-xs text-yellow-300">
                              {((block.gasUsed / block.gasLimit) * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-300">Tamanho:</span>
                          <span className="font-mono text-xs text-cyan-300">
                            {(block.size / 1024).toFixed(2)} KB
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Efeito de partículas no hover */}
                    <div className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                      {[...Array(6)].map((_, i) => (
                        <div
                          key={i}
                          className="absolute w-1 h-1 bg-blue-400 rounded-full animate-float"
                          style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            animationDelay: `${i * 0.2}s`,
                            animationDuration: `${2 + Math.random() * 2}s`
                          }}
                        ></div>
                      ))}
                    </div>

                    {/* Informações de Reserva */}
                    {reserva && (
                      <div className="mt-4 p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-lg border border-blue-400/20">
                        <div className="flex items-center justify-between mb-2">
                          <Badge 
                            variant="outline" 
                            className={`${
                              reserva.status === 'Sucesso' 
                                ? 'bg-green-500/20 text-green-300 border-green-400/50'
                                : 'bg-red-500/20 text-red-300 border-red-400/50'
                            }`}
                          >
                            {reserva.status === 'Sucesso' ? (
                              <CheckCircle className="h-3 w-3 mr-1" />
                            ) : (
                              <XCircle className="h-3 w-3 mr-1" />
                            )}
                            {reserva.status}
                          </Badge>
                          <span className="text-sm text-blue-300">
                            Cliente: {shortenAddress(reserva.cliente_id)}
                          </span>
                        </div>
                        
                        <div className="text-sm text-blue-200 mb-2">
                          {reserva.mensagem}
                        </div>
                        
                        {reserva.postos_reservados.length > 0 && (
                          <div className="mt-2">
                            <div className="text-sm text-blue-300 mb-1">Postos Reservados:</div>
                            <div className="flex flex-wrap gap-2">
                              {reserva.postos_reservados.map((posto, i) => (
                                <Badge 
                                  key={i}
                                  variant="secondary"
                                  className="bg-blue-500/20 text-blue-300 border-blue-400/50"
                                >
                                  {shortenAddress(posto)}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
      
      <style>{`
        @keyframes slideInScale {
          0% {
            transform: translateY(-50px) scale(0.8);
            opacity: 0;
          }
          50% {
            transform: translateY(-10px) scale(1.1);
          }
          100% {
            transform: translateY(0) scale(1);
            opacity: 1;
          }
        }
        
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(180deg); }
        }
        
        .animate-shimmer {
          background-size: 200% 100%;
          animation: shimmer 3s linear infinite;
        }
        
        .animate-float {
          animation: float 3s ease-in-out infinite;
        }
        
        .scrollbar-hide {
          scrollbar-width: none;
          -ms-overflow-style: none;
        }
        
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
};

export default BlockList;
