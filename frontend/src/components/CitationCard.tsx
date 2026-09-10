import { imageUrl } from "../api";
import type { Citation } from "../types";

interface Props {
  citation: Citation;
  onClick: () => void;
}

export default function CitationCard({ citation, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="flex w-40 shrink-0 flex-col overflow-hidden rounded-md border border-slate-200 bg-white text-left hover:border-indigo-300"
    >
      <img
        src={imageUrl(citation.image_url)}
        alt={`Page ${citation.page_number}`}
        className="h-24 w-full object-cover"
      />
      <div className="p-2">
        <p className="truncate text-xs font-medium text-slate-700">{citation.doc_name}</p>
        <p className="text-xs text-slate-400">Page {citation.page_number}</p>
      </div>
    </button>
  );
}
