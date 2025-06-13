
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getNetworkInfo, NetworkInfo } from '@/lib/web3';
import { Activity, Database, Zap } from 'lucide-react';

const NetworkStatus = () => {
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNetworkInfo = async () => {
      const info = await getNetworkInfo();
      setNetworkInfo(info);
      setLoading(false);
    };

    fetchNetworkInfo();
    const interval = setInterval(fetchNetworkInfo, 5000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-blue-50 to-indigo-100 border-blue-200">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-blue-200 rounded w-1/2"></div>
            <div className="h-8 bg-blue-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card className="bg-gradient-to-br from-green-50 to-emerald-100 border-green-200 hover:shadow-lg transition-all duration-300">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-green-800">Status da Rede</CardTitle>
          <Activity className="h-4 w-4 text-green-600" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Badge 
              variant={networkInfo?.isConnected ? "default" : "destructive"}
              className={networkInfo?.isConnected ? "bg-green-500 hover:bg-green-600" : ""}
            >
              {networkInfo?.isConnected ? "Conectado" : "Desconectado"}
            </Badge>
            <span className="text-2xl font-bold text-green-700">
              Chain ID: {networkInfo?.chainId || 'N/A'}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-blue-50 to-cyan-100 border-blue-200 hover:shadow-lg transition-all duration-300">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-blue-800">Último Bloco</CardTitle>
          <Database className="h-4 w-4 text-blue-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-blue-700">
            #{networkInfo?.blockNumber?.toLocaleString() || '0'}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-purple-50 to-violet-100 border-purple-200 hover:shadow-lg transition-all duration-300">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-purple-800">Gas Price</CardTitle>
          <Zap className="h-4 w-4 text-purple-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-purple-700">
            {networkInfo?.gasPrice ? `${(parseInt(networkInfo.gasPrice) / 1e9).toFixed(2)} Gwei` : 'N/A'}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default NetworkStatus;
