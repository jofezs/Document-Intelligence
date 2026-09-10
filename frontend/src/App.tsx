import { FileStack, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { listDocuments } from "./api";
import ChatPanel from "./components/ChatPanel";
import DocumentList from "./components/DocumentList";
import EditPanel from "./components/EditPanel";
import UploadPanel from "./components/UploadPanel";
import { useTheme } from "./hooks/useTheme";
import type { DocumentItem } from "./types";

export default function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const { theme, toggleTheme } = useTheme();

  async function refresh() {
    setDocuments(await listDocuments());
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

  function toggleSelect(id: string) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-900">
      <aside className="flex w-80 shrink-0 flex-col gap-4 border-r border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 dark:text-slate-100">
            <FileStack className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h1 className="font-semibold">Document Intelligence</h1>
          </div>
          <button
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="rounded p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-100"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
        <UploadPanel onUploaded={refresh} />
        <div className="flex-1 overflow-y-auto">
          <DocumentList
            documents={documents}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onEdit={setEditingDoc}
            onChanged={refresh}
          />
        </div>
        {selectedIds.length > 0 && (
          <p className="text-xs text-slate-400 dark:text-slate-500">
            {selectedIds.length} document(s) selected — queries scoped to them. Click again to deselect.
          </p>
        )}
      </aside>
      <main className="flex-1">
        <ChatPanel documents={documents} selectedIds={selectedIds} />
      </main>
      {editingDoc && (
        <EditPanel doc={editingDoc} onClose={() => setEditingDoc(null)} onChanged={refresh} />
      )}
    </div>
  );
}
