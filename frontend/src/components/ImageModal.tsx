import { X } from "lucide-react";

import { imageUrl } from "../api";
import type { Citation } from "../types";

interface Props {
  citation: Citation;
  onClose: () => void;
}

export default function ImageModal({ citation, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6" onClick={onClose}>
      <div
        className="max-h-full max-w-3xl overflow-auto rounded-lg bg-white p-3"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between gap-4">
          <p className="text-sm font-medium text-slate-700">
            {citation.doc_name} — Page {citation.page_number}
          </p>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X className="h-5 w-5" />
          </button>
        </div>
        <img src={imageUrl(citation.image_url)} alt={`Page ${citation.page_number}`} className="max-w-full rounded" />
      </div>
    </div>
  );
}
