
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getLatestBlock, getTransaction, TransactionInfo, formatEther, shortenAddress } from '@/lib/web3';
import { ArrowRight, Coins, Hash, Zap } from 'lucide-react';

const TransactionList = () => {
  const [transactions, setTransactions] = useState<TransactionInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const latestBlock = await getLatestBlock();
        if (latestBlock && latestBlock.transactions.length > 0) {
          const txPromises = latestBlock.transactions.slice(0, 10).map(txHash => 
            getTransaction(txHash)
          );
          
          const fetchedTxs = await Promise.all(txPromises);
          setTransactions(fetchedTxs.filter(tx => tx !== null) as TransactionInfo[]);
        }
        setLoading(false);
      } catch (error) {
        console.error('Error fetching transactions:', error);
        setLoading(false);
      }
    };

    fetchTransactions();
    const interval = setInterval(fetchTransactions, 10000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-amber-50 to-orange-100">
        <CardHeader>
          <CardTitle className="text-amber-800">Transações Recentes</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-16 bg-amber-200 rounded-lg"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gradient-to-br from-amber-50 to-orange-100 border-amber-200">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2 text-amber-800">
          <Coins className="h-5 w-5" />
          <span>Transações Recentes</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {transactions.length === 0 ? (
            <div className="text-center py-8 text-amber-600">
              <Coins className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>Nenhuma transação encontrada no último bloco</p>
            </div>
          ) : (
            transactions.map((tx) => (
              <div
                key={tx.hash}
                className="bg-white rounded-lg p-4 shadow-sm border border-amber-200 hover:shadow-md transition-all duration-200"
              >
                <div className="flex items-center justify-between mb-3">
                  <Badge variant="outline" className="bg-amber-100 text-amber-700 border-amber-300">
                    Bloco #{tx.blockNumber}
                  </Badge>
                  <div className="flex items-center space-x-1 text-sm text-amber-600">
                    <Hash className="h-3 w-3" />
                    <code className="text-xs bg-amber-100 px-1 rounded">
                      {shortenAddress(tx.hash)}
                    </code>
                  </div>
                </div>
                
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                      {shortenAddress(tx.from)}
                    </code>
                    <ArrowRight className="h-4 w-4 text-amber-500" />
                    <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                      {tx.to ? shortenAddress(tx.to) : 'Contract Creation'}
                    </code>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center space-x-2">
                    <Coins className="h-3 w-3 text-amber-500" />
                    <span className="text-slate-600">Valor:</span>
                    <span className="font-mono text-amber-700 font-medium">
                      {parseFloat(formatEther(tx.value)).toFixed(4)} ETH
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Zap className="h-3 w-3 text-amber-500" />
                    <span className="text-slate-600">Gas:</span>
                    <span className="font-mono text-xs">
                      {tx.gas.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default TransactionList;
