import { useState, useEffect } from 'react';
import NetworkStatus from '@/components/NetworkStatus';
import BlockList from '@/components/BlockList';
import TransactionList from '@/components/TransactionList';
import NeuralNetwork from '@/components/NeuralNetwork';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Blocks, Globe, Zap, Activity, Brain, Network } from 'lucide-react';
import { getNetworkInfo } from '@/lib/web3';

const Index = () => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [blockCount, setBlockCount] = useState(0);
  const [showNeuralView, setShowNeuralView] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const fetchBlockCount = async () => {
      const networkInfo = await getNetworkInfo();
      setBlockCount(networkInfo.blockNumber);
    };

    fetchBlockCount();
    const interval = setInterval(fetchBlockCount, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 relative overflow-hidden">
      {/* Efeitos de fundo animados */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }}></div>
      </div>

      {/* Partículas flutuantes */}
      <div className="absolute inset-0 pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-blue-400 rounded-full opacity-30 animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${5 + Math.random() * 10}s`
            }}
          ></div>
        ))}
      </div>

      {/* Header */}
      <header className="bg-black/20 backdrop-blur-xl border-b border-white/10 relative z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-3 rounded-xl relative">
                  <Blocks className="h-8 w-8 text-white" />
                  <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl blur opacity-30 animate-pulse"></div>
                </div>
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
                  Neural Blockchain Explorer
                </h1>
                <p className="text-blue-200 text-sm flex items-center space-x-2">
                  <Network className="h-4 w-4" />
                  <span>Rede Ganache - localhost:3333</span>
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowNeuralView(!showNeuralView)}
                className="flex items-center space-x-2 bg-gradient-to-r from-purple-500/20 to-blue-500/20 hover:from-purple-500/30 hover:to-blue-500/30 text-white px-4 py-2 rounded-lg border border-purple-400/30 transition-all duration-300 hover:scale-105"
              >
                <Brain className="h-4 w-4" />
                <span>{showNeuralView ? 'Lista de Blocos' : 'Visão Neural'}</span>
              </button>
              
              <Badge variant="outline" className="bg-green-500/20 text-green-300 border-green-400 animate-pulse">
                <Activity className="h-3 w-3 mr-1" />
                Ao Vivo
              </Badge>
              
              <div className="text-white text-sm font-mono bg-black/20 px-3 py-1 rounded">
                {currentTime.toLocaleTimeString('pt-BR')}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8 relative z-10">
        <div className="space-y-8">
          {/* Welcome Card com efeitos especiais */}
          <Card className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 backdrop-blur-xl border-white/10 text-white relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-cyan-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400"></div>
            
            <CardHeader className="relative">
              <CardTitle className="flex items-center space-x-3 text-xl">
                <div className="relative">
                  <Globe className="h-6 w-6 text-blue-400" />
                  <div className="absolute -inset-1 bg-blue-400/30 rounded-full animate-ping"></div>
                </div>
                <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  Bem-vindo ao Explorer Neural da Blockchain
                </span>
              </CardTitle>
            </CardHeader>
            
            <CardContent className="relative">
              <p className="text-blue-100 leading-relaxed mb-4">
                Monitore sua rede Ethereum local em tempo real com visualização neural avançada. 
                Visualize blocos, transações, status da rede e conexões neurais entre os componentes. 
                Esta interface conecta diretamente com sua instância do Ganache rodando em localhost:3333.
              </p>
              
              <div className="flex items-center space-x-4">
                <Badge variant="outline" className="bg-blue-500/20 text-blue-300 border-blue-400 hover:bg-blue-500/30 transition-colors">
                  <Zap className="h-3 w-3 mr-1" />
                  Tempo Real
                </Badge>
                <Badge variant="outline" className="bg-purple-500/20 text-purple-300 border-purple-400 hover:bg-purple-500/30 transition-colors">
                  <Brain className="h-3 w-3 mr-1" />
                  IA Neural
                </Badge>
                <Badge variant="outline" className="bg-green-500/20 text-green-300 border-green-400 hover:bg-green-500/30 transition-colors">
                  <Network className="h-3 w-3 mr-1" />
                  Web3 Conectado
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Network Status */}
          <NetworkStatus />

          {/* Visão Neural ou Lista de Blocos */}
          {showNeuralView ? (
            <Card className="bg-gradient-to-br from-slate-900/95 to-gray-900/95 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="flex items-center space-x-3 text-white">
                  <Brain className="h-6 w-6 text-purple-400" />
                  <span className="bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
                    Visualização Neural da Rede
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-96">
                  <NeuralNetwork blocks={blockCount} className="w-full h-full" />
                </div>
              </CardContent>
            </Card>
          ) : (
            /* Content Grid */
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <BlockList />
              <TransactionList />
            </div>
          )}
        </div>
      </main>

      {/* Footer com efeitos */}
      <footer className="bg-black/20 backdrop-blur-xl border-t border-white/10 mt-16 relative z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between text-sm text-blue-200">
            <p className="flex items-center space-x-2">
              <span>© 2024 Neural Blockchain Explorer</span>
              <span className="text-purple-400">•</span>
              <span>Powered by Web3.js & AI</span>
            </p>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <p>Conectado à rede Ethereum local</p>
            </div>
          </div>
        </div>
      </footer>

      <style>{`
        @keyframes float {
          0%, 100% { 
            transform: translateY(0px) rotate(0deg); 
            opacity: 0.3;
          }
          25% { 
            transform: translateY(-20px) rotate(90deg); 
            opacity: 0.7;
          }
          50% { 
            transform: translateY(-10px) rotate(180deg); 
            opacity: 1;
          }
          75% { 
            transform: translateY(-30px) rotate(270deg); 
            opacity: 0.5;
          }
        }
        
        .animate-float {
          animation: float ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default Index;
