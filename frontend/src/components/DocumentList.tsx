import { AlertCircle, CheckCircle2, FileText, Loader2, Trash2 } from "lucide-react";
import type { MouseEvent } from "react";

import { deleteDocument } from "../api";
import type { DocumentItem } from "../types";

interface Props {
  documents: DocumentItem[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onChanged: () => void;
}

const statusIcon: Record<DocumentItem["status"], JSX.Element> = {
  processing: <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-500" />,
  ready: <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />,
  error: <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />,
};

export default function DocumentList({ documents, selectedIds, onToggleSelect, onChanged }: Props) {
  async function handleDelete(id: string, e: MouseEvent) {
    e.stopPropagation();
    await deleteDocument(id);
    onChanged();
  }

  if (documents.length === 0) {
    return <p className="text-sm text-slate-400">No documents uploaded yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {documents.map((doc) => (
        <li
          key={doc.id}
          onClick={() => doc.status === "ready" && onToggleSelect(doc.id)}
          className={`flex items-center gap-2 rounded-md border p-2 text-sm ${
            selectedIds.includes(doc.id) ? "border-indigo-400 bg-indigo-50" : "border-slate-200"
          } ${doc.status === "ready" ? "cursor-pointer" : "cursor-default opacity-80"}`}
        >
          <FileText className="h-4 w-4 shrink-0 text-slate-400" />
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-slate-700">{doc.filename}</p>
            <p className="truncate text-xs text-slate-400">
              {doc.status === "ready" && `${doc.num_pages} pages`}
              {doc.status === "processing" && "Processing…"}
              {doc.status === "error" && (doc.error || "Failed")}
            </p>
          </div>
          {statusIcon[doc.status]}
          <button onClick={(e) => handleDelete(doc.id, e)} className="shrink-0 text-slate-300 hover:text-red-500">
            <Trash2 className="h-4 w-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
