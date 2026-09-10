import { Loader2, Send } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import ReactMarkdown from "react-markdown";

import { queryDocuments } from "../api";
import type { ChatMessage, Citation, DocumentItem } from "../types";
import CitationCard from "./CitationCard";
import ImageModal from "./ImageModal";

interface Props {
  documents: DocumentItem[];
  selectedIds: string[];
}

export default function ChatPanel({ documents, selectedIds }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const readyDocs = documents.filter((d) => d.status === "ready");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await queryDocuments(question, selectedIds.length ? selectedIds : undefined);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, citations: res.citations }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "query failed"}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            {readyDocs.length === 0
              ? "Upload a PDF to get started."
              : "Ask a question about your documents — text, tables, charts and layout are all fair game."}
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block max-w-[85%] rounded-lg px-3 py-2 text-left text-sm ${
                msg.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"
              }`}
            >
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
            {msg.citations && msg.citations.length > 0 && (
              <div className="mt-2 flex gap-2 overflow-x-auto">
                {msg.citations.map((c, ci) => (
                  <CitationCard key={ci} citation={c} onClick={() => setActiveCitation(c)} />
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-slate-200 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your documents…"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || readyDocs.length === 0}
          className="flex items-center gap-1 rounded-md bg-indigo-600 px-3 py-2 text-sm text-white disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
      {activeCitation && <ImageModal citation={activeCitation} onClose={() => setActiveCitation(null)} />}
    </div>
  );
}
