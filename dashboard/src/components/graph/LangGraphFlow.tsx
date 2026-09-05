"use client";
import { useState, useEffect } from "react";
import { ReactFlow, Controls, Background, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import GraphNode from "./GraphNode";
import { useWebSocket } from "@/hooks/useWebSocket";

const nodeTypes = {
  custom: GraphNode,
};

const initialNodes = [
  { id: 'check_overdue', type: 'custom', position: { x: 300, y: 50 }, data: { name: 'check_overdue', description: 'Checks if invoice has passed due date', icon: '🔍', color: 'cyan', isActive: false } },
  { id: 'check_cooldown', type: 'custom', position: { x: 300, y: 180 }, data: { name: 'check_cooldown', description: 'Enforces communication limits', icon: '⏳', color: 'cyan', isActive: false } },
  { id: 'log_blocked', type: 'custom', position: { x: 50, y: 310 }, data: { name: 'log_blocked', description: 'Halt workflow (cooldown active)', icon: '🛑', color: 'red', isActive: false } },
  { id: 'retrieve_context', type: 'custom', position: { x: 550, y: 310 }, data: { name: 'retrieve_context', description: 'Fetch RAG context from ChromaDB', icon: '🧠', color: 'purple', isActive: false } },
  { id: 'classify_reply', type: 'custom', position: { x: 550, y: 440 }, data: { name: 'classify_reply', description: 'LLM intent classification', icon: '🧠', color: 'purple', isActive: false } },
  { id: 'execute_action', type: 'custom', position: { x: 300, y: 570 }, data: { name: 'execute_action', description: 'Perform deterministic updates', icon: '🔧', color: 'emerald', isActive: false } },
  { id: 'draft_email', type: 'custom', position: { x: 800, y: 570 }, data: { name: 'draft_email', description: 'Generate contextual email', icon: '✍️', color: 'purple', isActive: false } },
  { id: 'evaluate_compliance', type: 'custom', position: { x: 800, y: 700 }, data: { name: 'evaluate_compliance', description: 'Judge LLM runs checks', icon: '⚖️', color: 'amber', isActive: false } },
  { id: 'call_razorpay_tools', type: 'custom', position: { x: 550, y: 830 }, data: { name: 'call_razorpay_tools', description: 'Generate Payment Link / VA', icon: '🔧', color: 'emerald', isActive: false } },
  { id: 'draft_email_rewrite', type: 'custom', position: { x: 1050, y: 830 }, data: { name: 'draft_email (rewrite)', description: 'Rewrite based on Judge feedback', icon: '✍️', color: 'amber', isActive: false } },
  { id: 'simulate_client', type: 'custom', position: { x: 300, y: 830 }, data: { name: 'simulate_client', description: 'Agentic response simulation', icon: '🤖', color: 'purple', isActive: false } },
];

const initialEdges = [
  { id: 'e1', source: 'check_overdue', target: 'check_cooldown', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e2', source: 'check_cooldown', target: 'log_blocked', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e3', source: 'check_cooldown', target: 'retrieve_context', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e4', source: 'retrieve_context', target: 'classify_reply', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e5', source: 'classify_reply', target: 'execute_action', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e6', source: 'classify_reply', target: 'draft_email', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e7', source: 'draft_email', target: 'evaluate_compliance', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e8', source: 'evaluate_compliance', target: 'call_razorpay_tools', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e9', source: 'evaluate_compliance', target: 'draft_email_rewrite', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e10', source: 'draft_email_rewrite', target: 'evaluate_compliance', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' }, type: 'step' },
  { id: 'e11', source: 'call_razorpay_tools', target: 'execute_action', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e12', source: 'execute_action', target: 'simulate_client', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
];

export default function LangGraphFlow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  const { ws } = useWebSocket();
  
  useEffect(() => {
    if (!ws) return;
    
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'TICK_UPDATE' && data.payload?.active_nodes) {
          setActiveNodes(data.payload.active_nodes);
          setTimeout(() => setActiveNodes([]), 1200);
        }
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };
    
    ws.addEventListener('message', handleMessage);
    return () => ws.removeEventListener('message', handleMessage);
  }, [ws]);

  useEffect(() => {
    setNodes((nds) => 
      nds.map((node) => {
        const isActive = activeNodes.includes(node.id) || 
                        (node.id === 'draft_email_rewrite' && activeNodes.includes('draft_email'));
        return { ...node, data: { ...node.data, isActive } };
      })
    );
    
    setEdges((eds) => 
      eds.map((edge) => {
        const isSourceActive = activeNodes.includes(edge.source);
        const isTargetActive = activeNodes.includes(edge.target);
        
        return {
          ...edge,
          style: { 
            stroke: isSourceActive || isTargetActive ? '#00F0FF' : 'rgba(255,255,255,0.2)',
            strokeWidth: isSourceActive || isTargetActive ? 3 : 1,
            filter: isSourceActive || isTargetActive ? 'drop-shadow(0 0 5px #00F0FF)' : 'none'
          }
        };
      })
    );
  }, [activeNodes, setNodes, setEdges]);

  return (
    <div className="w-full h-[600px] relative group border border-white/5 rounded-xl overflow-hidden glass-panel">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        className="bg-[#0B0F19]"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(255, 255, 255, 0.03)" gap={20} size={1} />
        <Controls className="!bg-black/50 !border-white/10 !fill-white" />
      </ReactFlow>
    </div>
  );
}
