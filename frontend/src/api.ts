import type { DocumentItem, QueryResponse } from "./types";

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
