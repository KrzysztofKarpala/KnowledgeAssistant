import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bot,
  Database,
  Edit3,
  FilePlus,
  MessageSquarePlus,
  PanelRight,
  RefreshCw,
  Save,
  Send,
  Trash2,
  X,
} from "lucide-react";
import {
  api,
  Conversation,
  ConversationMessage,
  DocumentItem,
  SourceReference,
} from "./api";

type View = "chat" | "documents";

type Notice = {
  kind: "error" | "info";
  text: string;
};

export function App() {
  const [view, setView] = useState<View>("chat");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedSources, setSelectedSources] = useState<SourceReference[]>([]);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    void loadConversations();
    void loadDocuments();
  }, []);

  useEffect(() => {
    if (selectedConversationId) {
      void loadMessages(selectedConversationId);
    } else {
      setMessages([]);
      setSelectedSources([]);
      setSelectedMessageId(null);
    }
  }, [selectedConversationId]);

  const selectedConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === selectedConversationId) ?? null,
    [conversations, selectedConversationId],
  );

  async function loadConversations() {
    setIsLoading(true);
    try {
      const items = await api.listConversations();
      setConversations(items);
      setSelectedConversationId((current) => current ?? items[0]?.id ?? null);
      setNotice(null);
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
    } finally {
      setIsLoading(false);
    }
  }

  async function loadMessages(conversationId: string) {
    try {
      const items = await api.listMessages(conversationId);
      setMessages(items);
      const latestAssistant = [...items].reverse().find((message) => message.role === "assistant");
      setSelectedMessageId(latestAssistant?.id ?? null);
      setSelectedSources(latestAssistant?.metadata.sources ?? []);
      setNotice(null);
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
    }
  }

  async function loadDocuments() {
    try {
      setDocuments(await api.listDocuments());
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
    }
  }

  async function createConversation() {
    try {
      const conversation = await api.createConversation("New conversation");
      setConversations((current) => [conversation, ...current]);
      setSelectedConversationId(conversation.id);
      setView("chat");
      setNotice(null);
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
    }
  }

  async function sendMessage(content: string) {
    let conversationId = selectedConversationId;
    setIsSending(true);
    try {
      if (!conversationId) {
        const conversation = await api.createConversation(content.slice(0, 80));
        conversationId = conversation.id;
        setConversations((current) => [conversation, ...current]);
        setSelectedConversationId(conversation.id);
      }

      const userMessage: ConversationMessage = {
        id: `pending-${Date.now()}`,
        conversation_id: conversationId,
        role: "user",
        content,
        cited_chunk_ids: [],
        metadata: {},
        created_at: new Date().toISOString(),
      };
      setMessages((current) => [...current, userMessage]);

      const response = await api.sendMessage(conversationId, content);
      const assistantMessage: ConversationMessage = {
        id: response.assistant_message_id,
        conversation_id: response.conversation_id,
        role: "assistant",
        content: response.answer,
        cited_chunk_ids: response.cited_chunk_ids,
        metadata: {
          sources: response.sources,
          confidence: response.confidence,
        },
        created_at: new Date().toISOString(),
      };

      setMessages((current) => [
        ...current.filter((message) => message.id !== userMessage.id),
        { ...userMessage, id: response.user_message_id },
        assistantMessage,
      ]);
      setSelectedMessageId(assistantMessage.id);
      setSelectedSources(response.sources);
      setNotice(null);
      void loadConversations();
    } catch (error) {
      setMessages((current) => current.filter((message) => !message.id.startsWith("pending-")));
      setNotice({ kind: "error", text: formatError(error) });
    } finally {
      setIsSending(false);
    }
  }

  async function createDocument(payload: {
    title: string;
    content: string;
    version?: string;
    effective_from?: string;
  }) {
    try {
      const created = await api.createDocument({
        title: payload.title,
        content: payload.content,
        version: payload.version || null,
        effective_from: payload.effective_from || null,
        metadata: {},
      });
      setNotice({
        kind: "info",
        text: `Created "${created.title}" with ${created.chunks_created} indexed chunk(s).`,
      });
      await loadDocuments();
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
    }
  }

  async function updateDocument(
    documentId: string,
    payload: {
      title: string;
      content: string;
      status: "active" | "archived";
      version?: string;
      effective_from?: string;
    },
  ) {
    try {
      const updated = await api.updateDocument(documentId, {
        title: payload.title,
        content: payload.content,
        status: payload.status,
        version: payload.version || null,
        effective_from: payload.effective_from || null,
      });
      setDocuments((current) =>
        current.map((document) => (document.id === updated.id ? updated : document)),
      );
      setNotice({ kind: "info", text: `Updated "${updated.title}".` });
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
      throw error;
    }
  }

  async function deleteDocument(documentId: string) {
    try {
      await api.deleteDocument(documentId);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      setNotice({ kind: "info", text: "Document deleted." });
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
      throw error;
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Bot size={22} aria-hidden="true" />
          <div>
            <strong>KnowledgeAssistant</strong>
            <span>Local RAG workbench</span>
          </div>
        </div>

        <nav className="nav-tabs" aria-label="Primary">
          <button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}>
            <MessageSquarePlus size={17} aria-hidden="true" />
            Chat
          </button>
          <button
            className={view === "documents" ? "active" : ""}
            onClick={() => setView("documents")}
          >
            <Database size={17} aria-hidden="true" />
            Documents
          </button>
        </nav>

        <div className="sidebar-heading">
          <span>Conversations</span>
          <button className="icon-button" onClick={createConversation} title="New conversation">
            <MessageSquarePlus size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="conversation-list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={conversation.id === selectedConversationId ? "selected" : ""}
              onClick={() => {
                setSelectedConversationId(conversation.id);
                setView("chat");
              }}
            >
              <strong>{conversation.title || "Untitled conversation"}</strong>
              <span>{formatDate(conversation.updated_at)}</span>
            </button>
          ))}
          {!isLoading && conversations.length === 0 ? (
            <p className="empty-state">No conversations yet.</p>
          ) : null}
        </div>
      </aside>

      <main className="main-panel">
        {notice ? <div className={`notice ${notice.kind}`}>{notice.text}</div> : null}
        {view === "chat" ? (
          <ChatPanel
            conversation={selectedConversation}
            messages={messages}
            isSending={isSending}
            selectedMessageId={selectedMessageId}
            onSend={sendMessage}
            onSelectSources={(message) => {
              setSelectedMessageId(message.id);
              setSelectedSources(message.metadata.sources ?? []);
            }}
          />
        ) : (
          <DocumentsPanel
            documents={documents}
            onRefresh={loadDocuments}
            onCreate={createDocument}
            onUpdate={updateDocument}
            onDelete={deleteDocument}
          />
        )}
      </main>

      <aside className="sources-panel">
        <div className="panel-title">
          <PanelRight size={18} aria-hidden="true" />
          <span>Evidence</span>
        </div>
        <SourcePanel sources={selectedSources} />
      </aside>
    </div>
  );
}

function ChatPanel({
  conversation,
  messages,
  isSending,
  selectedMessageId,
  onSend,
  onSelectSources,
}: {
  conversation: Conversation | null;
  messages: ConversationMessage[];
  isSending: boolean;
  selectedMessageId: string | null;
  onSend: (content: string) => Promise<void>;
  onSelectSources: (message: ConversationMessage) => void;
}) {
  const [draft, setDraft] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || isSending) {
      return;
    }
    setDraft("");
    await onSend(content);
  }

  return (
    <section className="chat-panel">
      <header className="content-header">
        <div>
          <span className="eyebrow">Conversation</span>
          <h1>{conversation?.title || "New conversation"}</h1>
        </div>
      </header>

      <div className="message-thread">
        {messages.length === 0 ? (
          <div className="start-state">
            <h2>Ask a grounded question</h2>
            <p>Answers will cite indexed document chunks and keep the conversation history.</p>
          </div>
        ) : null}
        {messages.map((message) => (
          <article
            key={message.id}
            className={`message ${message.role} ${message.id === selectedMessageId ? "selected" : ""}`}
            onClick={() => {
              if (message.role === "assistant") {
                onSelectSources(message);
              }
            }}
          >
            <div className="message-meta">
              <span>{message.role}</span>
              {message.metadata.confidence ? <span>{message.metadata.confidence} confidence</span> : null}
            </div>
            <p>{message.content}</p>
          </article>
        ))}
        {isSending ? <div className="message assistant pending">Generating answer...</div> : null}
      </div>

      <form className="composer" onSubmit={submit}>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask about indexed knowledge..."
          rows={3}
        />
        <button type="submit" disabled={!draft.trim() || isSending} title="Send message">
          <Send size={18} aria-hidden="true" />
          Send
        </button>
      </form>
    </section>
  );
}

function DocumentsPanel({
  documents,
  onRefresh,
  onCreate,
  onUpdate,
  onDelete,
}: {
  documents: DocumentItem[];
  onRefresh: () => Promise<void>;
  onCreate: (payload: {
    title: string;
    content: string;
    version?: string;
    effective_from?: string;
  }) => Promise<void>;
  onUpdate: (
    documentId: string,
    payload: {
      title: string;
      content: string;
      status: "active" | "archived";
      version?: string;
      effective_from?: string;
    },
  ) => Promise<void>;
  onDelete: (documentId: string) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [content, setContent] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !content.trim()) {
      return;
    }
    await onCreate({
      title: title.trim(),
      content: content.trim(),
      version: version.trim(),
      effective_from: effectiveFrom,
    });
    setTitle("");
    setVersion("");
    setEffectiveFrom("");
    setContent("");
  }

  return (
    <section className="documents-panel">
      <header className="content-header">
        <div>
          <span className="eyebrow">Knowledge base</span>
          <h1>Documents</h1>
        </div>
        <button className="secondary-button" onClick={() => void onRefresh()}>
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </header>

      <form className="document-form" onSubmit={submit}>
        <div className="form-grid">
          <label>
            Title
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            Version
            <input value={version} onChange={(event) => setVersion(event.target.value)} />
          </label>
          <label>
            Effective from
            <input
              type="date"
              value={effectiveFrom}
              onChange={(event) => setEffectiveFrom(event.target.value)}
            />
          </label>
        </div>
        <label>
          Content
          <textarea value={content} onChange={(event) => setContent(event.target.value)} rows={6} />
        </label>
        <button type="submit" disabled={!title.trim() || !content.trim()}>
          <FilePlus size={17} aria-hidden="true" />
          Add document
        </button>
      </form>

      <div className="document-list">
        {documents.map((document) => (
          <DocumentCard
            key={document.id}
            document={document}
            onUpdate={onUpdate}
            onDelete={onDelete}
          />
        ))}
      </div>
    </section>
  );
}

function DocumentCard({
  document,
  onUpdate,
  onDelete,
}: {
  document: DocumentItem;
  onUpdate: (
    documentId: string,
    payload: {
      title: string;
      content: string;
      status: "active" | "archived";
      version?: string;
      effective_from?: string;
    },
  ) => Promise<void>;
  onDelete: (documentId: string) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [title, setTitle] = useState(document.title);
  const [content, setContent] = useState(document.content);
  const [status, setStatus] = useState<"active" | "archived">(document.status);
  const [version, setVersion] = useState(document.version ?? "");
  const [effectiveFrom, setEffectiveFrom] = useState(document.effective_from ?? "");

  function resetForm() {
    setTitle(document.title);
    setContent(document.content);
    setStatus(document.status);
    setVersion(document.version ?? "");
    setEffectiveFrom(document.effective_from ?? "");
  }

  async function save() {
    if (!title.trim() || !content.trim()) {
      return;
    }

    setIsBusy(true);
    try {
      await onUpdate(document.id, {
        title: title.trim(),
        content: content.trim(),
        status,
        version: version.trim(),
        effective_from: effectiveFrom,
      });
      setIsEditing(false);
    } finally {
      setIsBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Delete "${document.title}"?`)) {
      return;
    }

    setIsBusy(true);
    try {
      await onDelete(document.id);
    } finally {
      setIsBusy(false);
    }
  }

  if (isEditing) {
    return (
      <article className="document-card editing">
        <div className="document-edit-form">
          <label>
            Title
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            Content
            <textarea value={content} onChange={(event) => setContent(event.target.value)} rows={7} />
          </label>
        </div>
        <div className="document-edit-side">
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}>
              <option value="active">active</option>
              <option value="archived">archived</option>
            </select>
          </label>
          <label>
            Version
            <input value={version} onChange={(event) => setVersion(event.target.value)} />
          </label>
          <label>
            Effective
            <input
              type="date"
              value={effectiveFrom}
              onChange={(event) => setEffectiveFrom(event.target.value)}
            />
          </label>
          <div className="document-actions">
            <button type="button" onClick={() => void save()} disabled={isBusy || !title.trim() || !content.trim()}>
              <Save size={16} aria-hidden="true" />
              Save
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => {
                resetForm();
                setIsEditing(false);
              }}
              disabled={isBusy}
            >
              <X size={16} aria-hidden="true" />
              Cancel
            </button>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="document-card">
      <div>
        <strong>{document.title}</strong>
        <p>{document.content}</p>
      </div>
      <div className="document-card-side">
        <dl>
          <div>
            <dt>Status</dt>
            <dd>{document.status}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{document.version || "unknown"}</dd>
          </div>
          <div>
            <dt>Effective</dt>
            <dd>{document.effective_from || "unknown"}</dd>
          </div>
        </dl>
        <div className="document-actions">
          <button type="button" className="secondary-button" onClick={() => setIsEditing(true)} disabled={isBusy}>
            <Edit3 size={16} aria-hidden="true" />
            Edit
          </button>
          <button type="button" className="danger-button" onClick={() => void remove()} disabled={isBusy}>
            <Trash2 size={16} aria-hidden="true" />
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}

function SourcePanel({ sources }: { sources: SourceReference[] }) {
  if (!sources.length) {
    return <p className="empty-state">Select an assistant answer to inspect its sources.</p>;
  }

  return (
    <div className="source-list">
      {sources.map((source) => (
        <article key={source.chunk_id} className="source-card">
          <div className="source-score">{Math.round(source.similarity * 100)}%</div>
          <strong>{source.document_title}</strong>
          <dl>
            <div>
              <dt>Chunk</dt>
              <dd>{source.chunk_index}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>{source.source_role}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{source.document_version || "unknown"}</dd>
            </div>
          </dl>
          <code>{source.chunk_id}</code>
        </article>
      ))}
    </div>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error.";
}
