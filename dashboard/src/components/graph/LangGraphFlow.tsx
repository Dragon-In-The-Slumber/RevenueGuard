"use client";
import { useState, useEffect } from "react";
import { ReactFlow, Controls, Background, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import GraphNode from "./GraphNode";
import { useWebSocketContext } from "@/components/WebSocketProvider";

const nodeTypes = {
  custom: GraphNode,
};

const initialNodes = [
  { id: 'check_overdue', type: 'custom', position: { x: 420, y: 0 }, data: { name: 'check_overdue', description: 'Checks if invoice has passed due date', icon: '\u{1F50D}', color: 'cyan', isActive: false } },
  { id: 'check_stop_conditions', type: 'custom', position: { x: 420, y: 120 }, data: { name: 'check_stop_conditions', description: 'Five stopping rules: paid, PTP window, legal hold, max attempts', icon: '\u{1F6D1}', color: 'red', isActive: false } },
  { id: 'check_cooldown', type: 'custom', position: { x: 420, y: 240 }, data: { name: 'check_cooldown', description: 'Enforces communication limits', icon: '⏳', color: 'cyan', isActive: false } },
  { id: 'log_blocked', type: 'custom', position: { x: 120, y: 360 }, data: { name: 'log_blocked', description: 'Halt workflow (cooldown active)', icon: '\u{1F6AB}', color: 'red', isActive: false } },
  { id: 'retrieve_client_context', type: 'custom', position: { x: 700, y: 360 }, data: { name: 'retrieve_client_context', description: 'Fetch RAG profile + policy from ChromaDB', icon: '\u{1F9E0}', color: 'purple', isActive: false } },
  { id: 'classify_reply', type: 'custom', position: { x: 700, y: 480 }, data: { name: 'classify_reply', description: 'LLM intent classification', icon: '\u{1F4AC}', color: 'purple', isActive: false } },
  { id: 'decide_action', type: 'custom', position: { x: 700, y: 600 }, data: { name: 'decide_action', description: 'THE AGENT CHOOSES: 8-action menu, reads the client profile', icon: '\u{1F3AF}', color: 'purple', isActive: false } },
  { id: 'validate_action', type: 'custom', position: { x: 700, y: 720 }, data: { name: 'validate_action', description: 'POLICY GUARD: 9 rules, can veto and substitute', icon: '⚖️', color: 'amber', isActive: false } },
  { id: 'act_wait', type: 'custom', position: { x: 60, y: 860 }, data: { name: 'act_wait', description: 'Deliberate patience — doing nothing, on purpose', icon: '⏸️', color: 'cyan', isActive: false } },
  { id: 'prepare_offer', type: 'custom', position: { x: 320, y: 860 }, data: { name: 'prepare_offer', description: 'Discount / split / payment plan to Razorpay links', icon: '\u{1F4B0}', color: 'emerald', isActive: false } },
  { id: 'draft_sms', type: 'custom', position: { x: 560, y: 860 }, data: { name: 'draft_sms', description: 'Switch channel to SMS / WhatsApp', icon: '\u{1F4F1}', color: 'purple', isActive: false } },
  { id: 'act_escalate', type: 'custom', position: { x: 1060, y: 860 }, data: { name: 'act_escalate', description: 'Hand the case to a person', icon: '\u{1F464}', color: 'amber', isActive: false } },
  { id: 'act_close', type: 'custom', position: { x: 1300, y: 860 }, data: { name: 'act_close', description: 'Close as unrecoverable', icon: '\u{1F5D1}️', color: 'red', isActive: false } },
  { id: 'draft_email', type: 'custom', position: { x: 800, y: 980 }, data: { name: 'draft_email', description: 'Generate contextual email', icon: '✍️', color: 'purple', isActive: false } },
  { id: 'evaluate_compliance', type: 'custom', position: { x: 800, y: 1100 }, data: { name: 'evaluate_compliance', description: 'Judge LLM runs the 8-rule rubric', icon: '\u{1F6E1}️', color: 'amber', isActive: false } },
  { id: 'draft_email_rewrite', type: 'custom', position: { x: 1100, y: 1100 }, data: { name: 'draft_email (rewrite)', description: 'Rewrite based on Judge feedback', icon: '\u{1F501}', color: 'amber', isActive: false } },
  { id: 'call_razorpay_tools', type: 'custom', position: { x: 560, y: 1220 }, data: { name: 'call_razorpay_tools', description: 'Razorpay payment link via the audited tool layer', icon: '\u{1F527}', color: 'emerald', isActive: false } },
  { id: 'execute_action', type: 'custom', position: { x: 560, y: 1340 }, data: { name: 'execute_action', description: 'Dispatch and send through the tool layer', icon: '\u{1F680}', color: 'emerald', isActive: false } },
  { id: 'notify_human', type: 'custom', position: { x: 1120, y: 1340 }, data: { name: 'notify_human', description: 'Slack / console handoff', icon: '\u{1F4E3}', color: 'amber', isActive: false } },
  { id: 'simulate_client', type: 'custom', position: { x: 260, y: 1460 }, data: { name: 'simulate_client', description: 'SIMULATED ENVIRONMENT (test harness, not the agent)', icon: '\u{1F3B2}', color: 'cyan', isActive: false } },
];

const initialEdges = [
  { id: 'e1', source: 'check_overdue', target: 'check_stop_conditions', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e2', source: 'check_stop_conditions', target: 'check_cooldown', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e2b', source: 'check_stop_conditions', target: 'notify_human', animated: true, style: { stroke: 'rgba(248,113,113,0.35)' }, type: 'step' },
  { id: 'e3', source: 'check_cooldown', target: 'log_blocked', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e4', source: 'check_cooldown', target: 'retrieve_client_context', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e5', source: 'retrieve_client_context', target: 'classify_reply', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e6', source: 'classify_reply', target: 'decide_action', animated: true, style: { stroke: 'rgba(139,92,246,0.5)' } },
  { id: 'e7', source: 'decide_action', target: 'validate_action', animated: true, style: { stroke: 'rgba(139,92,246,0.5)' } },
  { id: 'e8', source: 'validate_action', target: 'act_wait', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e9', source: 'validate_action', target: 'prepare_offer', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e10', source: 'validate_action', target: 'draft_sms', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e11', source: 'validate_action', target: 'draft_email', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e12', source: 'validate_action', target: 'act_escalate', animated: true, style: { stroke: 'rgba(251,191,36,0.4)' } },
  { id: 'e13', source: 'validate_action', target: 'act_close', animated: true, style: { stroke: 'rgba(248,113,113,0.35)' } },
  { id: 'e14', source: 'prepare_offer', target: 'draft_email', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e15', source: 'draft_email', target: 'evaluate_compliance', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e16', source: 'draft_sms', target: 'evaluate_compliance', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' }, type: 'step' },
  { id: 'e17', source: 'evaluate_compliance', target: 'draft_email_rewrite', animated: true, style: { stroke: 'rgba(251,191,36,0.4)' } },
  { id: 'e18', source: 'draft_email_rewrite', target: 'evaluate_compliance', animated: true, style: { stroke: 'rgba(251,191,36,0.4)' }, type: 'step' },
  { id: 'e19', source: 'evaluate_compliance', target: 'call_razorpay_tools', animated: true, style: { stroke: 'rgba(52,211,153,0.4)' } },
  { id: 'e20', source: 'call_razorpay_tools', target: 'execute_action', animated: true, style: { stroke: 'rgba(52,211,153,0.4)' } },
  { id: 'e21', source: 'execute_action', target: 'simulate_client', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e22', source: 'execute_action', target: 'notify_human', animated: true, style: { stroke: 'rgba(251,191,36,0.4)' }, type: 'step' },
  { id: 'e23', source: 'act_escalate', target: 'notify_human', animated: true, style: { stroke: 'rgba(251,191,36,0.4)' } },
  { id: 'e24', source: 'act_close', target: 'notify_human', animated: true, style: { stroke: 'rgba(248,113,113,0.35)' } },
];

export default function LangGraphFlow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  // One shared socket from the app shell. The backend now emits TICK_UPDATE
  // carrying visited_nodes -- the event this component always listened for but
  // which was never sent, which is why the graph never animated.
  const { activeNodes: liveNodes, lastTickAt } = useWebSocketContext();

  useEffect(() => {
    if (!lastTickAt || liveNodes.length === 0) return;
    setActiveNodes(liveNodes);
    const t = setTimeout(() => setActiveNodes([]), 1500);
    return () => clearTimeout(t);
  }, [lastTickAt, liveNodes]);

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
