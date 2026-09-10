import {
  Download,
  Highlighter,
  Loader2,
  RotateCw,
  Scissors,
  StickyNote,
  Trash2,
  Type,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";

import {
  addNote,
  deletePage,
  downloadUrl,
  fillFormFields,
  getFormFields,
  highlightText,
  imageUrl,
  redactText,
  reorderPages,
  resetDocument,
  rotatePage,
  stampText,
} from "../api";
import type { DocumentItem, FormField } from "../types";

// Must match the render DPI used by the backend (app/services/pdf_processor.py).
const RENDER_DPI = 150;
const POINTS_PER_INCH = 72;

interface Props {
  doc: DocumentItem;
  onClose: () => void;
  onChanged: () => void;
}

export default function EditPanel({ doc, onClose, onChanged }: Props) {
  const [numPages, setNumPages] = useState(doc.num_pages ?? 0);
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [highlightPage, setHighlightPage] = useState(1);
  const [highlightQuery, setHighlightQuery] = useState("");

  const [redactScope, setRedactScope] = useState<"all" | "page">("all");
  const [redactPage, setRedactPage] = useState(1);
  const [redactQuery, setRedactQuery] = useState("");

  const [clickMode, setClickMode] = useState<"type" | "note">("type");

  const [formFields, setFormFields] = useState<FormField[]>([]);
  const [formValues, setFormValues] = useState<Record<string, string>>({});

  useEffect(() => {
    refreshFormFields();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshFormFields() {
    try {
      const fields = await getFormFields(doc.id);
      setFormFields(fields);
      setFormValues(Object.fromEntries(fields.map((f) => [f.name, f.value])));
    } catch {
      // form fields are optional; ignore fetch failures
    }
  }

  async function runAction(label: string, action: () => Promise<unknown>, opts?: { refetchForm?: boolean }) {
    setError(null);
    setBusy(label);
    try {
      await action();
      setVersion((v) => v + 1);
      onChanged();
      if (opts?.refetchForm) await refreshFormFields();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed`);
    } finally {
      setBusy(null);
    }
  }

  async function handleDeletePage(pageNumber: number) {
    if (numPages <= 1) {
      setError("Cannot delete the only page in the document");
      return;
    }
    await runAction(`Deleting page ${pageNumber}`, async () => {
      const res = await deletePage(doc.id, pageNumber);
      setNumPages(res.num_pages);
    });
  }

  async function handleRotate(pageNumber: number, degrees: number) {
    await runAction(`Rotating page ${pageNumber}`, () => rotatePage(doc.id, pageNumber, degrees));
  }

  async function handleMove(pageNumber: number, direction: -1 | 1) {
    const target = pageNumber + direction;
    if (target < 1 || target > numPages) return;
    const order = Array.from({ length: numPages }, (_, i) => i + 1);
    [order[pageNumber - 1], order[target - 1]] = [order[target - 1], order[pageNumber - 1]];
    await runAction(`Moving page ${pageNumber}`, () => reorderPages(doc.id, order));
  }

  async function handleHighlight() {
    if (!highlightQuery.trim()) return;
    await runAction("Highlighting", () => highlightText(doc.id, highlightPage, highlightQuery.trim()));
  }

  async function handleRedact() {
    if (!redactQuery.trim()) return;
    if (!window.confirm("Redaction permanently removes this text from the document. Continue?")) return;
    await runAction("Redacting", () =>
      redactText(doc.id, redactQuery.trim(), redactScope === "page" ? redactPage : undefined)
    );
  }

  async function handlePageClick(e: ReactMouseEvent<HTMLImageElement>, pageNumber: number) {
    const img = e.currentTarget;
    const rect = img.getBoundingClientRect();
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;
    const pixelX = (e.clientX - rect.left) * scaleX;
    const pixelY = (e.clientY - rect.top) * scaleY;
    const x = (pixelX / RENDER_DPI) * POINTS_PER_INCH;
    const y = (pixelY / RENDER_DPI) * POINTS_PER_INCH;

    if (clickMode === "type") {
      const text = window.prompt(`Type text to place on page ${pageNumber}:`);
      if (!text) return;
      await runAction(`Typing on page ${pageNumber}`, () => stampText(doc.id, pageNumber, x, y, text));
    } else {
      const text = window.prompt(`Add a sticky note on page ${pageNumber}:`);
      if (!text) return;
      await runAction(`Adding note to page ${pageNumber}`, () => addNote(doc.id, pageNumber, x, y, text));
    }
  }

  async function handleFormSubmit() {
    await runAction("Saving form values", () => fillFormFields(doc.id, formValues), { refetchForm: true });
  }

  async function handleReset() {
    if (!window.confirm("Discard all edits and revert to the originally uploaded PDF?")) return;
    await runAction("Resetting", async () => {
      await resetDocument(doc.id);
      setNumPages(doc.num_pages ?? numPages);
    });
    await refreshFormFields();
  }

  const pages = Array.from({ length: numPages }, (_, i) => i + 1);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex h-full max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-lg bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <div>
            <h2 className="font-semibold text-slate-800">Edit: {doc.filename}</h2>
            <p className="text-xs text-slate-400">{numPages} pages</p>
          </div>
          <div className="flex items-center gap-2">
            {busy && (
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Loader2 className="h-3 w-3 animate-spin" /> {busy}…
              </span>
            )}
            <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {error && <p className="bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>}

        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {pages.map((pageNumber) => (
              <div key={pageNumber} className="flex flex-col gap-1 rounded-md border border-slate-200 p-2">
                <img
                  src={`${imageUrl(`/api/documents/${doc.id}/pages/${pageNumber}/image`)}?v=${version}`}
                  alt={`Page ${pageNumber}`}
                  onClick={(e) => handlePageClick(e, pageNumber)}
                  className="cursor-crosshair rounded border border-slate-100"
                  title="Click to add a note here"
                />
                <p className="text-center text-xs text-slate-400">Page {pageNumber}</p>
                <div className="flex items-center justify-center gap-1">
                  <button
                    title="Move left"
                    onClick={() => handleMove(pageNumber, -1)}
                    disabled={pageNumber === 1}
                    className="rounded p-1 text-slate-400 hover:text-indigo-600 disabled:opacity-30"
                  >
                    ←
                  </button>
                  <button
                    title="Rotate 90°"
                    onClick={() => handleRotate(pageNumber, 90)}
                    className="rounded p-1 text-slate-400 hover:text-indigo-600"
                  >
                    <RotateCw className="h-4 w-4" />
                  </button>
                  <button
                    title="Delete page"
                    onClick={() => handleDeletePage(pageNumber)}
                    className="rounded p-1 text-slate-400 hover:text-red-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                  <button
                    title="Move right"
                    onClick={() => handleMove(pageNumber, 1)}
                    disabled={pageNumber === numPages}
                    className="rounded p-1 text-slate-400 hover:text-indigo-600 disabled:opacity-30"
                  >
                    →
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-md border border-slate-200 p-3">
              <p className="mb-2 flex items-center gap-1 text-sm font-medium text-slate-700">
                <Highlighter className="h-4 w-4" /> Highlight text
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={highlightPage}
                  onChange={(e) => setHighlightPage(Number(e.target.value))}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                >
                  {pages.map((p) => (
                    <option key={p} value={p}>
                      Page {p}
                    </option>
                  ))}
                </select>
                <input
                  value={highlightQuery}
                  onChange={(e) => setHighlightQuery(e.target.value)}
                  placeholder="Text to find and highlight"
                  className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1 text-sm"
                />
                <button
                  onClick={handleHighlight}
                  className="rounded bg-indigo-600 px-3 py-1 text-sm text-white disabled:opacity-40"
                  disabled={!highlightQuery.trim()}
                >
                  Highlight
                </button>
              </div>
            </div>

            <div className="rounded-md border border-slate-200 p-3">
              <p className="mb-2 flex items-center gap-1 text-sm font-medium text-slate-700">
                <Scissors className="h-4 w-4" /> Redact text (permanent)
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={redactScope}
                  onChange={(e) => setRedactScope(e.target.value as "all" | "page")}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                >
                  <option value="all">All pages</option>
                  <option value="page">One page</option>
                </select>
                {redactScope === "page" && (
                  <select
                    value={redactPage}
                    onChange={(e) => setRedactPage(Number(e.target.value))}
                    className="rounded border border-slate-300 px-2 py-1 text-sm"
                  >
                    {pages.map((p) => (
                      <option key={p} value={p}>
                        Page {p}
                      </option>
                    ))}
                  </select>
                )}
                <input
                  value={redactQuery}
                  onChange={(e) => setRedactQuery(e.target.value)}
                  placeholder="Text to redact"
                  className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1 text-sm"
                />
                <button
                  onClick={handleRedact}
                  className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-40"
                  disabled={!redactQuery.trim()}
                >
                  Redact
                </button>
              </div>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span>Click a page thumbnail above to:</span>
            <label className="flex items-center gap-1">
              <input
                type="radio"
                checked={clickMode === "type"}
                onChange={() => setClickMode("type")}
              />
              <Type className="h-3 w-3" /> type visible text (fill a blank on a flat form)
            </label>
            <label className="flex items-center gap-1">
              <input
                type="radio"
                checked={clickMode === "note"}
                onChange={() => setClickMode("note")}
              />
              <StickyNote className="h-3 w-3" /> drop a sticky note (icon, click to reveal)
            </label>
          </div>

          {formFields.length > 0 && (
            <div className="mt-6 rounded-md border border-slate-200 p-3">
              <p className="mb-2 text-sm font-medium text-slate-700">Form fields</p>
              <div className="flex flex-col gap-2">
                {formFields.map((field) => (
                  <label key={field.name} className="flex items-center gap-2 text-sm">
                    <span className="w-40 shrink-0 truncate text-slate-500">{field.name}</span>
                    {field.choices ? (
                      <select
                        value={formValues[field.name] ?? ""}
                        onChange={(e) => setFormValues((v) => ({ ...v, [field.name]: e.target.value }))}
                        className="flex-1 rounded border border-slate-300 px-2 py-1"
                      >
                        {field.choices.map((choice) => (
                          <option key={choice} value={choice}>
                            {choice}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        value={formValues[field.name] ?? ""}
                        onChange={(e) => setFormValues((v) => ({ ...v, [field.name]: e.target.value }))}
                        className="flex-1 rounded border border-slate-300 px-2 py-1"
                      />
                    )}
                  </label>
                ))}
                <button
                  onClick={handleFormSubmit}
                  className="mt-1 self-start rounded bg-indigo-600 px-3 py-1 text-sm text-white"
                >
                  Save form values
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 p-4">
          <button onClick={handleReset} className="text-sm text-slate-400 hover:text-red-500">
            Reset to original
          </button>
          <a
            href={downloadUrl(doc.id)}
            className="flex items-center gap-1 rounded-md bg-indigo-600 px-3 py-2 text-sm text-white"
          >
            <Download className="h-4 w-4" /> Download PDF
          </a>
        </div>
      </div>
    </div>
  );
}
