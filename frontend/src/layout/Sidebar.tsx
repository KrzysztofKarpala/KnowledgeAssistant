import {
  Bot,
  Database,
  MessageSquare,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Trash2,
  X,
} from "lucide-react";
import type { RefObject } from "react";
import type { Conversation } from "../api";
import { formatDate } from "../lib/format";
import type { View } from "./types";

export type PendingDeleteConversation = {
  id: string;
  title: string;
};

type SidebarProps = {
  view: View;
  conversations: Conversation[];
  filteredConversations: Conversation[];
  activeDocumentCount: number;
  conversationSearch: string;
  selectedConversationId: string | null;
  isLoading: boolean;
  isSidebarOpen: boolean;
  isMobileNavOpen: boolean;
  pendingDeleteConversation: PendingDeleteConversation | null;
  searchInputRef: RefObject<HTMLInputElement | null>;
  onSetView: (view: View) => void;
  onCloseMobileNav: () => void;
  onToggleSidebar: () => void;
  onCreateConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onSetPendingDeleteConversation: (conversation: PendingDeleteConversation | null) => void;
  onConversationSearchChange: (value: string) => void;
};

export function Sidebar({
  view,
  conversations,
  filteredConversations,
  activeDocumentCount,
  conversationSearch,
  selectedConversationId,
  isLoading,
  isSidebarOpen,
  isMobileNavOpen,
  pendingDeleteConversation,
  searchInputRef,
  onSetView,
  onCloseMobileNav,
  onToggleSidebar,
  onCreateConversation,
  onSelectConversation,
  onDeleteConversation,
  onSetPendingDeleteConversation,
  onConversationSearchChange,
}: SidebarProps) {
  return (
    <aside className={`sidebar ${isMobileNavOpen ? "mobile-open" : ""}`}>
      <div className="brand">
        <div className="brand-mark">
          <Bot size={21} aria-hidden="true" />
        </div>
        <div className="brand-copy">
          <strong>KnowledgeAssistant</strong>
          <span>Local RAG workbench</span>
        </div>
        <button
          type="button"
          className="mobile-drawer-close icon-button"
          onClick={onCloseMobileNav}
          aria-label="Close navigation"
          title="Close navigation"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="workspace-stats" aria-label="Workspace statistics">
        <div>
          <strong>{conversations.length}</strong>
          <span>Chats</span>
        </div>
        <div>
          <strong>{activeDocumentCount}</strong>
          <span>Active docs</span>
        </div>
      </div>

      <button
        type="button"
        className="collapsed-new-conversation"
        onClick={onCreateConversation}
        title="New conversation"
        aria-label="New conversation"
      >
        <MessageSquarePlus size={17} aria-hidden="true" />
      </button>

      <nav className="nav-tabs" aria-label="Primary">
        <button
          className={view === "chat" ? "active" : ""}
          onClick={() => onSetView("chat")}
          title="Chat"
        >
          <MessageSquare size={17} aria-hidden="true" />
          <span>Chat</span>
        </button>
        <button
          className={view === "documents" ? "active" : ""}
          onClick={() => onSetView("documents")}
          title="Documents"
        >
          <Database size={17} aria-hidden="true" />
          <span>Documents</span>
        </button>
      </nav>

      <div className="sidebar-heading">
        <span>Conversations</span>
      </div>

      <label className="conversation-search">
        <Search size={15} aria-hidden="true" />
        <input
          ref={searchInputRef}
          value={conversationSearch}
          onChange={(event) => onConversationSearchChange(event.target.value)}
          placeholder="Search chats"
          aria-label="Search conversations"
        />
        {conversationSearch ? (
          <button
            type="button"
            onClick={() => onConversationSearchChange("")}
            title="Clear search"
            aria-label="Clear search"
          >
            <X size={14} aria-hidden="true" />
          </button>
        ) : null}
      </label>

      <button type="button" className="new-conversation-button" onClick={onCreateConversation}>
        <MessageSquarePlus size={17} aria-hidden="true" />
        New Conversation
      </button>

      <div className="conversation-list">
        {filteredConversations.map((conversation) => {
          const title = conversation.title || "Untitled conversation";
          const isConfirming = pendingDeleteConversation?.id === conversation.id;
          return (
            <div
              key={conversation.id}
              className={`conversation-item ${conversation.id === selectedConversationId ? "selected" : ""} ${
                isConfirming ? "confirming-delete" : ""
              }`}
            >
              {isConfirming ? (
                <div className="conversation-confirm">
                  <strong>Delete this chat?</strong>
                  <div>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => onSetPendingDeleteConversation(null)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => onDeleteConversation(conversation.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <button
                    className="conversation-select"
                    onClick={() => onSelectConversation(conversation.id)}
                  >
                    <strong>{title}</strong>
                    <span>{formatDate(conversation.updated_at)}</span>
                  </button>
                  <button
                    type="button"
                    className="conversation-delete"
                    onClick={() => onSetPendingDeleteConversation({ id: conversation.id, title })}
                    title="Delete conversation"
                    aria-label={`Delete ${title}`}
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                </>
              )}
            </div>
          );
        })}
        {!isLoading && conversations.length === 0 ? (
          <div className="empty-state compact">
            <MessageSquarePlus size={18} aria-hidden="true" />
            <span>No conversations yet.</span>
          </div>
        ) : null}
        {!isLoading && conversations.length > 0 && filteredConversations.length === 0 ? (
          <div className="empty-state compact">
            <Search size={18} aria-hidden="true" />
            <span>No matching conversations.</span>
          </div>
        ) : null}
      </div>

      <div className="sidebar-footer">
        <button
          type="button"
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          title={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          aria-label={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          aria-pressed={!isSidebarOpen}
        >
          {isSidebarOpen ? (
            <PanelLeftClose size={17} aria-hidden="true" />
          ) : (
            <PanelLeftOpen size={17} aria-hidden="true" />
          )}
          <span>{isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}</span>
        </button>
      </div>
    </aside>
  );
}
