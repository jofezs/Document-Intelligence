import { AlertCircle, CheckCircle2, FileText, Loader2, Pencil, Trash2 } from "lucide-react";
import type { MouseEvent } from "react";

import { deleteDocument } from "../api";
import type { DocumentItem } from "../types";

interface Props {
  documents: DocumentItem[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onEdit: (doc: DocumentItem) => void;
  onChanged: () => void;
}

const statusIcon: Record<DocumentItem["status"], JSX.Element> = {
  processing: <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-500" />,
  ready: <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />,
  error: <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />,
};

export default function DocumentList({ documents, selectedIds, onToggleSelect, onEdit, onChanged }: Props) {
  async function handleDelete(id: string, e: MouseEvent) {
    e.stopPropagation();
    await deleteDocument(id);
    onChanged();
  }

  function handleEdit(doc: DocumentItem, e: MouseEvent) {
    e.stopPropagation();
    onEdit(doc);
  }

  if (documents.length === 0) {
    return <p className="text-sm text-slate-400 dark:text-slate-500">No documents uploaded yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {documents.map((doc) => (
        <li
          key={doc.id}
          onClick={() => doc.status === "ready" && onToggleSelect(doc.id)}
          className={`flex items-center gap-2 rounded-md border p-2 text-sm ${
            selectedIds.includes(doc.id)
              ? "border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-950"
              : "border-slate-200 dark:border-slate-700"
          } ${doc.status === "ready" ? "cursor-pointer" : "cursor-default opacity-80"}`}
        >
          <FileText className="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500" />
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-slate-700 dark:text-slate-200">{doc.filename}</p>
            <p className="truncate text-xs text-slate-400 dark:text-slate-500">
              {doc.status === "ready" && `${doc.num_pages} pages`}
              {doc.status === "processing" && "Processing…"}
              {doc.status === "error" && (doc.error || "Failed")}
            </p>
          </div>
          {statusIcon[doc.status]}
          {doc.status === "ready" && (
            <button
              onClick={(e) => handleEdit(doc, e)}
              className="shrink-0 text-slate-300 hover:text-indigo-600 dark:text-slate-600 dark:hover:text-indigo-400"
            >
              <Pencil className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={(e) => handleDelete(doc.id, e)}
            className="shrink-0 text-slate-300 hover:text-red-500 dark:text-slate-600 dark:hover:text-red-400"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
