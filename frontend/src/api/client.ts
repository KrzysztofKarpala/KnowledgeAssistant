import type {
  Conversation,
  ConversationChatResponse,
  ConversationMessage,
  DocumentCreateResponse,
  DocumentItem,
  DocumentUpdatePayload,
} from "./types";

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
  updateConversation: (conversationId: string, title: string) =>
    request<Conversation>(`/conversations/${conversationId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (conversationId: string) =>
    request<void>(`/conversations/${conversationId}`, {
      method: "DELETE",
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
