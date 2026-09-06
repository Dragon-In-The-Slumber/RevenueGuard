import { Handle, Position } from '@xyflow/react';

export default function GraphNode({ data }: { data: any }) {
  const { name, description, isActive, color, icon } = data;

  return (
    <div className={`
      relative p-4 rounded-xl border transition-all duration-500 w-64
      ${isActive 
        ? `bg-${color}-500/20 border-${color}-400 text-white shadow-[0_0_25px_rgba(var(--${color}-rgb),0.6)] scale-105` 
        : 'bg-bg-deep/90 border-white/10 text-white/70 shadow-lg backdrop-blur-md'
      }
    `}>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-white/50 !border-0" />
      
      <div className="flex items-start gap-3">
        <div className={`text-xl ${isActive ? 'animate-bounce' : 'opacity-50'}`}>
          {icon}
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            {isActive && <span className={`w-2 h-2 rounded-full bg-${color}-400 animate-pulse`}></span>}
            <h3 className={`font-mono text-sm font-bold ${isActive ? 'text-white' : 'text-white/80'}`}>
              {name}
            </h3>
          </div>
          <p className="text-[10px] text-white/50 leading-tight font-sans">
            {description}
          </p>
        </div>
      </div>
      
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-white/50 !border-0" />
    </div>
  );
}
