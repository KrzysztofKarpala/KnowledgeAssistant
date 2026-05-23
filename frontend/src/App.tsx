import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { Conversation, ConversationMessage, DocumentItem, SourceReference } from "./api";
import { ChatPanel } from "./features/chat/ChatPanel";
import { DocumentsPanel } from "./features/documents/DocumentsPanel";
import type { DocumentDraft } from "./features/documents/types";
import { MobileAppBar } from "./layout/MobileAppBar";
import { Sidebar } from "./layout/Sidebar";
import type { PendingDeleteConversation } from "./layout/Sidebar";
import { SourcesPanel } from "./layout/SourcesPanel";
import type { View } from "./layout/types";
import { formatError } from "./lib/format";

type Notice = {
  kind: "error" | "info";
  text: string;
};

const EVIDENCE_STORAGE_KEY = "knowledgeassistant:evidence-open";

export function App() {
  const [view, setView] = useState<View>("chat");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationSearch, setConversationSearch] = useState("");
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedSources, setSelectedSources] = useState<SourceReference[]>([]);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(() => readEvidencePreference());
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [pendingDeleteConversation, setPendingDeleteConversation] =
    useState<PendingDeleteConversation | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    void loadConversations();
    void loadDocuments();
  }, []);

  useEffect(() => {
    window.localStorage.setItem(EVIDENCE_STORAGE_KEY, isEvidenceOpen ? "1" : "0");
  }, [isEvidenceOpen]);

  useEffect(() => {
    if (!notice) {
      return;
    }

    const timeoutId = window.setTimeout(() => setNotice(null), 3600);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  useEffect(() => {
    function handleGlobalKeys(event: globalThis.KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const isTyping =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable;

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      if (event.key === "Escape") {
        setPendingDeleteConversation(null);
        setIsMobileNavOpen(false);
        if (!isTyping) {
          setIsEvidenceOpen(false);
        }
      }
    }

    window.addEventListener("keydown", handleGlobalKeys);
    return () => window.removeEventListener("keydown", handleGlobalKeys);
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
  const activeDocumentCount = documents.filter((document) => document.status === "active").length;
  const filteredConversations = useMemo(() => {
    const query = conversationSearch.trim().toLowerCase();
    if (!query) {
      return conversations;
    }

    return conversations.filter((conversation) =>
      (conversation.title || "Untitled conversation").toLowerCase().includes(query),
    );
  }, [conversationSearch, conversations]);

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
      const conversation = await api.createConversation();
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
        const conversation = await api.createConversation();
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

  async function renameConversation(conversationId: string, title: string) {
    try {
      const updated = await api.updateConversation(conversationId, title);
      setConversations((current) =>
        current.map((conversation) => (conversation.id === updated.id ? updated : conversation)),
      );
      setNotice({ kind: "info", text: "Conversation renamed." });
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
      throw error;
    }
  }

  async function deleteConversation(conversationId: string) {
    try {
      await api.deleteConversation(conversationId);
      const remaining = conversations.filter((item) => item.id !== conversationId);
      setConversations(remaining);
      setPendingDeleteConversation(null);
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(remaining[0]?.id ?? null);
        setSelectedSources([]);
        setSelectedMessageId(null);
      }
      setNotice({ kind: "info", text: "Conversation deleted." });
    } catch (error) {
      setNotice({ kind: "error", text: formatError(error) });
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
      throw error;
    }
  }

  async function updateDocument(documentId: string, payload: DocumentDraft) {
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
    <div
      className={`app-shell ${isEvidenceOpen ? "" : "evidence-collapsed"} ${
        isSidebarOpen ? "" : "sidebar-collapsed"
      }`}
    >
      <MobileAppBar
        view={view}
        sourceCount={selectedSources.length}
        onOpenNavigation={() => setIsMobileNavOpen(true)}
        onOpenEvidence={() => setIsEvidenceOpen(true)}
        onRefreshDocuments={() => void loadDocuments()}
      />

      {isMobileNavOpen ? (
        <button
          type="button"
          className="mobile-overlay"
          onClick={() => setIsMobileNavOpen(false)}
          aria-label="Dismiss navigation drawer"
        />
      ) : null}

      <Sidebar
        view={view}
        conversations={conversations}
        filteredConversations={filteredConversations}
        activeDocumentCount={activeDocumentCount}
        conversationSearch={conversationSearch}
        selectedConversationId={selectedConversationId}
        isLoading={isLoading}
        isSidebarOpen={isSidebarOpen}
        isMobileNavOpen={isMobileNavOpen}
        pendingDeleteConversation={pendingDeleteConversation}
        searchInputRef={searchInputRef}
        onSetView={(nextView) => {
          setView(nextView);
          setIsMobileNavOpen(false);
        }}
        onCloseMobileNav={() => setIsMobileNavOpen(false)}
        onToggleSidebar={() => setIsSidebarOpen((current) => !current)}
        onCreateConversation={() => {
          setIsMobileNavOpen(false);
          void createConversation();
        }}
        onSelectConversation={(conversationId) => {
          setSelectedConversationId(conversationId);
          setView("chat");
          setIsMobileNavOpen(false);
        }}
        onDeleteConversation={(conversationId) => void deleteConversation(conversationId)}
        onSetPendingDeleteConversation={setPendingDeleteConversation}
        onConversationSearchChange={setConversationSearch}
      />

      <main className="main-panel">
        {view === "chat" ? (
          <ChatPanel
            conversation={selectedConversation}
            messages={messages}
            isSending={isSending}
            selectedMessageId={selectedMessageId}
            onSend={sendMessage}
            onRename={renameConversation}
            onSelectSources={(message) => {
              setSelectedMessageId(message.id);
              setSelectedSources(message.metadata.sources ?? []);
              setIsEvidenceOpen(true);
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

      {view === "chat" ? (
        <>
          {isEvidenceOpen ? (
            <button
              type="button"
              className="mobile-overlay evidence-overlay"
              onClick={() => setIsEvidenceOpen(false)}
              aria-label="Dismiss evidence panel"
            />
          ) : null}
          <SourcesPanel
            sources={selectedSources}
            isOpen={isEvidenceOpen}
            onToggle={() => setIsEvidenceOpen((current) => !current)}
          />
        </>
      ) : null}

      {notice ? (
        <div className={`toast ${notice.kind}`} role="status">
          {notice.text}
        </div>
      ) : null}
    </div>
  );
}

function readEvidencePreference(): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  return window.localStorage.getItem(EVIDENCE_STORAGE_KEY) !== "0";
}
