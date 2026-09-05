"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

interface RosterEntry { name: string }

export default function RagSearchBar() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [matchedClient, setMatchedClient] = useState<string | null>(null);

  // The roster comes from the backend so client names are never hardcoded here.
  const { data: roster } = useApi<{ clients: RosterEntry[] }>("/api/clients/roster");
  const names = roster?.clients.map((c) => c.name) ?? [];

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    // Match the query against the real roster. Previously an unmatched name fell
    // through to Acme Corp, presenting Acme's profile as an answer about someone else.
    const lower = searchQuery.toLowerCase();
    const clientName = names.find((n) =>
      n.toLowerCase().split(/\s+/).some((word) => word.length > 2 && lower.includes(word))
    );

    if (!clientName) {
      setMatchedClient(null);
      setResult(
        `No client in the roster matches that query.\n\nKnown clients: ${names.join(", ") || "(roster unavailable)"}`
      );
      return;
    }

    try {
      setLoading(true);
      setMatchedClient(clientName);
      const res = await apiFetch<{ context: string }>(
        `/api/clients/${encodeURIComponent(clientName)}/context`
      );
      setResult(res.context);
    } catch (e) {
      setResult(e instanceof Error ? `Failed to retrieve context: ${e.message}` : "Failed to retrieve context from ChromaDB.");
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
        {names.slice(0, 3).map((n) => `What is ${n}'s payment history?`).map((q) => (
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
            {matchedClient && <span className="text-white/40 normal-case">· {matchedClient}</span>}
          </p>
          <pre className="text-xs font-mono text-white/70 whitespace-pre-wrap leading-relaxed">
            {result}
          </pre>
        </div>
      )}
    </div>
  );
}
