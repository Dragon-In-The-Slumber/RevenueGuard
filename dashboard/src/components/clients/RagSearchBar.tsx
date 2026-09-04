"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function RagSearchBar() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;
    try {
      setLoading(true);
      // For demo purposes, we map the query to one of the hero clients to trigger the RAG endpoint
      let clientName = "Acme Corp";
      if (searchQuery.toLowerCase().includes("globex")) clientName = "Globex Solutions";
      if (searchQuery.toLowerCase().includes("initech")) clientName = "Initech";
      if (searchQuery.toLowerCase().includes("soylent")) clientName = "Soylent Corp";
      
      const res: any = await apiFetch(`/api/clients/${encodeURIComponent(clientName)}/context`);
      setResult(res.context);
    } catch (e) {
      console.error(e);
      setResult("Failed to retrieve context from ChromaDB.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel p-6">
      <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-widest flex items-center gap-2">
        <span className="text-purple-400">🔍</span> RAG Context Search
      </h3>
      
      <div className="flex gap-2 mb-4">
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about any client (e.g., 'What are Globex's payment terms?')"
          onKeyDown={(e) => e.key === 'Enter' && handleSearch(query)}
          className="flex-1 bg-black/40 border border-white/10 text-white rounded-lg px-4 py-2 outline-none focus:border-purple-500 transition-colors"
        />
        <button 
          onClick={() => handleSearch(query)}
          disabled={loading || !query.trim()}
          className="bg-purple-500/20 text-purple-400 border border-purple-500/30 hover:bg-purple-500/30 px-6 py-2 rounded-lg font-bold transition-colors disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
      
      <div className="flex gap-2 mb-6 overflow-x-auto no-scrollbar">
        {["What are Globex's payment terms?", "Has Initech disputed before?", "What is Acme Corp's risk level?"].map((q) => (
          <button 
            key={q}
            onClick={() => { setQuery(q); handleSearch(q); }}
            className="whitespace-nowrap px-3 py-1 bg-white/5 hover:bg-white/10 rounded-full text-xs text-white/50 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {result && (
        <div className="bg-black/40 border border-white/10 rounded-lg p-4">
          <p className="text-[10px] uppercase font-mono tracking-wider text-purple-400 mb-2 flex items-center gap-2">
            <span>⚡</span> ChromaDB Raw Context
          </p>
          <pre className="text-xs font-mono text-white/70 whitespace-pre-wrap leading-relaxed">
            {result}
          </pre>
        </div>
      )}
    </div>
  );
}
