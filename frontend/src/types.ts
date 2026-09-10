export interface DocumentItem {
  id: string;
  filename: string;
  status: "processing" | "ready" | "error";
  num_pages: number | null;
  error: string | null;
  created_at: string;
}

export interface Citation {
  doc_id: string;
  doc_name: string;
  page_number: number;
  snippet: string;
  image_url: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}
