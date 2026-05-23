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
