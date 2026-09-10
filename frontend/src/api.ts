import type { DocumentItem, FormField, QueryResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function listDocuments() {
  return request<DocumentItem[]>("/api/documents");
}

export function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request<DocumentItem>("/api/documents", {
    method: "POST",
    body: formData,
  });
}

export function deleteDocument(id: string) {
  return request<{ status: string }>(`/api/documents/${id}`, { method: "DELETE" });
}

export function queryDocuments(question: string, docIds?: string[]) {
  return request<QueryResponse>("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, doc_ids: docIds }),
  });
}

export function imageUrl(path: string) {
  return `${API_BASE}${path}`;
}

function postJson<T>(path: string, body: unknown) {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function highlightText(docId: string, pageNumber: number, text: string) {
  return postJson<{ matches: number }>(`/api/documents/${docId}/highlight`, {
    page_number: pageNumber,
    text,
  });
}

export function addNote(docId: string, pageNumber: number, x: number, y: number, text: string) {
  return postJson<{ status: string }>(`/api/documents/${docId}/note`, {
    page_number: pageNumber,
    x,
    y,
    text,
  });
}

export function stampText(docId: string, pageNumber: number, x: number, y: number, text: string) {
  return postJson<{ status: string }>(`/api/documents/${docId}/stamp`, {
    page_number: pageNumber,
    x,
    y,
    text,
  });
}

export function redactText(docId: string, text: string, pageNumber?: number) {
  return postJson<{ matches: number }>(`/api/documents/${docId}/redact`, {
    text,
    page_number: pageNumber,
  });
}

export function deletePage(docId: string, pageNumber: number) {
  return request<{ num_pages: number }>(`/api/documents/${docId}/pages/${pageNumber}`, {
    method: "DELETE",
  });
}

export function rotatePage(docId: string, pageNumber: number, degrees: number) {
  return postJson<{ status: string }>(`/api/documents/${docId}/pages/${pageNumber}/rotate`, { degrees });
}

export function reorderPages(docId: string, order: number[]) {
  return postJson<{ status: string }>(`/api/documents/${docId}/pages/reorder`, { order });
}

export function getFormFields(docId: string) {
  return request<FormField[]>(`/api/documents/${docId}/form-fields`);
}

export function fillFormFields(docId: string, values: Record<string, string>) {
  return postJson<{ updated: number }>(`/api/documents/${docId}/form-fields`, { values });
}

export function resetDocument(docId: string) {
  return postJson<{ status: string }>(`/api/documents/${docId}/reset`, {});
}

export function downloadUrl(docId: string) {
  return `${API_BASE}/api/documents/${docId}/download`;
}
