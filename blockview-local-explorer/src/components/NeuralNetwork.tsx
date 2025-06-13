
import { useEffect, useState } from 'react';

interface Node {
  id: string;
  x: number;
  y: number;
  type: 'block' | 'transaction' | 'validator';
  active: boolean;
  connections: string[];
}

interface NetworkProps {
  blocks: number;
  className?: string;
}

const NeuralNetwork = ({ blocks, className = '' }: NetworkProps) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [activeConnections, setActiveConnections] = useState<Set<string>>(new Set());

  useEffect(() => {
    // Gerar rede neural baseada nos blocos
    const generateNetwork = () => {
      const newNodes: Node[] = [];
      const nodeCount = Math.min(blocks + 10, 25); // Máximo de 25 nós
      
      for (let i = 0; i < nodeCount; i++) {
        const angle = (i / nodeCount) * 2 * Math.PI;
        const radius = 150 + Math.random() * 100;
        const x = 300 + Math.cos(angle) * radius;
        const y = 300 + Math.sin(angle) * radius;
        
        const nodeType = i < blocks ? 'block' : Math.random() > 0.5 ? 'transaction' : 'validator';
        
        newNodes.push({
          id: `node-${i}`,
          x,
          y,
          type: nodeType,
          active: Math.random() > 0.3,
          connections: []
        });
      }
      
      // Criar conexões entre nós próximos
      newNodes.forEach((node, i) => {
        const connections: string[] = [];
        newNodes.forEach((otherNode, j) => {
          if (i !== j) {
            const distance = Math.sqrt(
              Math.pow(node.x - otherNode.x, 2) + Math.pow(node.y - otherNode.y, 2)
            );
            if (distance < 200 && Math.random() > 0.6) {
              connections.push(otherNode.id);
            }
          }
        });
        node.connections = connections.slice(0, 3); // Máximo 3 conexões por nó
      });
      
      setNodes(newNodes);
    };

    generateNetwork();
  }, [blocks]);

  useEffect(() => {
    // Animar conexões ativas
    const interval = setInterval(() => {
      const newActiveConnections = new Set<string>();
      nodes.forEach(node => {
        if (Math.random() > 0.7) {
          node.connections.forEach(connectionId => {
            newActiveConnections.add(`${node.id}-${connectionId}`);
          });
        }
      });
      setActiveConnections(newActiveConnections);
    }, 1500);

    return () => clearInterval(interval);
  }, [nodes]);

  const getNodeColor = (type: string, active: boolean) => {
    const colors = {
      block: active ? '#3b82f6' : '#1e40af',
      transaction: active ? '#10b981' : '#047857',
      validator: active ? '#f59e0b' : '#d97706'
    };
    return colors[type as keyof typeof colors] || '#6b7280';
  };

  const isConnectionActive = (nodeId: string, connectionId: string) => {
    return activeConnections.has(`${nodeId}-${connectionId}`) || 
           activeConnections.has(`${connectionId}-${nodeId}`);
  };

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <svg
        viewBox="0 0 600 600"
        className="w-full h-full"
        style={{ background: 'radial-gradient(circle at center, rgba(30, 64, 175, 0.1) 0%, transparent 70%)' }}
      >
        <defs>
          {/* Gradientes para conexões */}
          <linearGradient id="activeConnection" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#8b5cf6" stopOpacity="1" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.8" />
          </linearGradient>
          
          <linearGradient id="inactiveConnection" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#374151" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#4b5563" stopOpacity="0.1" />
          </linearGradient>

          {/* Filtros para brilho */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Conexões */}
        {nodes.map(node =>
          node.connections.map(connectionId => {
            const targetNode = nodes.find(n => n.id === connectionId);
            if (!targetNode) return null;
            
            const isActive = isConnectionActive(node.id, connectionId);
            
            return (
              <g key={`${node.id}-${connectionId}`}>
                <line
                  x1={node.x}
                  y1={node.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke={isActive ? 'url(#activeConnection)' : 'url(#inactiveConnection)'}
                  strokeWidth={isActive ? '2' : '1'}
                  opacity={isActive ? 1 : 0.3}
                  filter={isActive ? 'url(#glow)' : undefined}
                >
                  {isActive && (
                    <animate
                      attributeName="stroke-dasharray"
                      values="0,10;5,5;10,0"
                      dur="2s"
                      repeatCount="indefinite"
                    />
                  )}
                </line>
                
                {/* Partícula fluindo */}
                {isActive && (
                  <circle r="2" fill="#60a5fa" opacity="0.8">
                    <animateMotion
                      dur="3s"
                      repeatCount="indefinite"
                      path={`M ${node.x} ${node.y} L ${targetNode.x} ${targetNode.y}`}
                    />
                    <animate
                      attributeName="r"
                      values="1;3;1"
                      dur="3s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}
              </g>
            );
          })
        )}

        {/* Nós */}
        {nodes.map(node => (
          <g key={node.id}>
            {/* Halo do nó */}
            {node.active && (
              <circle
                cx={node.x}
                cy={node.y}
                r="15"
                fill={getNodeColor(node.type, true)}
                opacity="0.2"
                filter="url(#glow)"
              >
                <animate
                  attributeName="r"
                  values="15;25;15"
                  dur="2s"
                  repeatCount="indefinite"
                />
              </circle>
            )}
            
            {/* Nó principal */}
            <circle
              cx={node.x}
              cy={node.y}
              r={node.type === 'block' ? '8' : '6'}
              fill={getNodeColor(node.type, node.active)}
              stroke={node.active ? '#ffffff' : 'transparent'}
              strokeWidth="1"
              opacity={node.active ? 1 : 0.6}
              filter={node.active ? 'url(#glow)' : undefined}
            >
              {node.active && (
                <animate
                  attributeName="opacity"
                  values="0.6;1;0.6"
                  dur="1.5s"
                  repeatCount="indefinite"
                />
              )}
            </circle>

            {/* Ícone do tipo de nó */}
            <text
              x={node.x}
              y={node.y + 2}
              textAnchor="middle"
              fontSize="8"
              fill="white"
              fontWeight="bold"
            >
              {node.type === 'block' ? '⬜' : node.type === 'transaction' ? '💫' : '⚡'}
            </text>
          </g>
        ))}

        {/* Ondas de energia */}
        {[...Array(3)].map((_, i) => (
          <circle
            key={i}
            cx="300"
            cy="300"
            r="50"
            fill="none"
            stroke="#3b82f6"
            strokeWidth="1"
            opacity="0.3"
          >
            <animate
              attributeName="r"
              values="50;200;350"
              dur="8s"
              repeatCount="indefinite"
              begin={`${i * 2.7}s`}
            />
            <animate
              attributeName="opacity"
              values="0.5;0.2;0"
              dur="8s"
              repeatCount="indefinite"
              begin={`${i * 2.7}s`}
            />
          </circle>
        ))}
      </svg>

      {/* Informações da rede */}
      <div className="absolute top-4 left-4 bg-black/20 backdrop-blur-sm rounded-lg p-3 text-white">
        <div className="text-xs font-medium mb-1">Rede Neural Ativa</div>
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
            <span>{nodes.filter(n => n.type === 'block').length} Blocos</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <span>{nodes.filter(n => n.type === 'transaction').length} TX</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
            <span>{nodes.filter(n => n.type === 'validator').length} Validadores</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NeuralNetwork;
