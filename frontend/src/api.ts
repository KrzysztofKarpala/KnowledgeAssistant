export type ConversationStatus = "active" | "archived";
export type MessageRole = "user" | "assistant" | "system";
export type Confidence = "low" | "medium" | "high";

export type SourceReference = {
  document_id: string;
  parent_id: string | null;
  document_title: string;
  document_version: string | null;
  effective_from: string | null;
  chunk_id: string;
  chunk_index: number;
  similarity: number;
  source_role: string;
};

export type Conversation = {
  id: string;
  title: string | null;
  status: ConversationStatus;
  created_at: string;
  updated_at: string;
};

export type ConversationMessage = {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  cited_chunk_ids: string[];
  metadata: {
    sources?: SourceReference[];
    confidence?: Confidence;
    [key: string]: unknown;
  };
  created_at: string;
};

export type ConversationChatResponse = {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  answer: string;
  sources: SourceReference[];
  cited_chunk_ids: string[];
  confidence: Confidence;
};

export type DocumentStatus = "active" | "archived";

export type DocumentItem = {
  id: string;
  title: string;
  content: string;
  parent_id: string | null;
  status: DocumentStatus;
  version: string | null;
  effective_from: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DocumentCreateResponse = {
  id: string;
  title: string;
  chunks_created: number;
};

export type DocumentUpdatePayload = {
  title?: string;
  content?: string;
  status?: DocumentStatus;
  version?: string | null;
  effective_from?: string | null;
  metadata?: Record<string, unknown>;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => JSON.stringify(item)).join("; ");
    }
  } catch {
    return null;
  }

  return null;
}

export const api = {
  listConversations: () => request<Conversation[]>("/conversations"),
  createConversation: (title?: string) =>
    request<Conversation>("/conversations", {
      method: "POST",
      body: JSON.stringify({ title: title || null }),
    }),
  listMessages: (conversationId: string) =>
    request<ConversationMessage[]>(`/conversations/${conversationId}/messages`),
  sendMessage: (conversationId: string, content: string) =>
    request<ConversationChatResponse>(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  listDocuments: () => request<DocumentItem[]>("/documents"),
  createDocument: (payload: {
    title: string;
    content: string;
    version?: string | null;
    effective_from?: string | null;
    metadata?: Record<string, unknown>;
  }) =>
    request<DocumentCreateResponse>("/documents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateDocument: (documentId: string, payload: DocumentUpdatePayload) =>
    request<DocumentItem>(`/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteDocument: (documentId: string) =>
    request<void>(`/documents/${documentId}`, {
      method: "DELETE",
    }),
};
