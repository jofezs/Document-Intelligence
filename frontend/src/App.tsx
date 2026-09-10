import { FileStack } from "lucide-react";
import { useEffect, useState } from "react";

import { listDocuments } from "./api";
import ChatPanel from "./components/ChatPanel";
import DocumentList from "./components/DocumentList";
import UploadPanel from "./components/UploadPanel";
import type { DocumentItem } from "./types";

export default function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

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
    <div className="flex h-screen bg-slate-50">
      <aside className="flex w-80 shrink-0 flex-col gap-4 border-r border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 text-slate-800">
          <FileStack className="h-5 w-5 text-indigo-600" />
          <h1 className="font-semibold">Document Intelligence</h1>
        </div>
        <UploadPanel onUploaded={refresh} />
        <div className="flex-1 overflow-y-auto">
          <DocumentList
            documents={documents}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onChanged={refresh}
          />
        </div>
        {selectedIds.length > 0 && (
          <p className="text-xs text-slate-400">
            {selectedIds.length} document(s) selected — queries scoped to them. Click again to deselect.
          </p>
        )}
      </aside>
      <main className="flex-1">
        <ChatPanel documents={documents} selectedIds={selectedIds} />
      </main>
    </div>
  );
}
