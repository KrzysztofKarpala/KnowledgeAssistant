import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { Check, Edit3, LoaderCircle, Send, Sparkles } from "lucide-react";
import type { Conversation, ConversationMessage, SourceReference } from "../../api";

type ChatPanelProps = {
  conversation: Conversation | null;
  messages: ConversationMessage[];
  isSending: boolean;
  selectedMessageId: string | null;
  onSend: (content: string) => Promise<void>;
  onRename: (conversationId: string, title: string) => Promise<void>;
  onSelectSources: (message: ConversationMessage) => void;
};

export function ChatPanel({
  conversation,
  messages,
  isSending,
  selectedMessageId,
  onSend,
  onRename,
  onSelectSources,
}: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    function handleShortcut(event: globalThis.KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const isTyping =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable;

      if (!isTyping && event.key === "/") {
        event.preventDefault();
        textareaRef.current?.focus();
      }
    }

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || isSending) {
      return;
    }
    setDraft("");
    await onSend(content);
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      (event.key === "Enter" && !event.shiftKey) ||
      (event.key === "Enter" && (event.ctrlKey || event.metaKey))
    ) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <section className="chat-panel">
      <header className="content-header">
        <div className="conversation-title-block">
          <span className="eyebrow">Conversation</span>
          <ConversationTitle conversation={conversation} onRename={onRename} />
        </div>
      </header>

      <div className="message-thread">
        {messages.length === 0 ? (
          <div className="start-state">
            <div className="start-icon">
              <Sparkles size={24} aria-hidden="true" />
            </div>
            <h2>Ask a grounded question</h2>
            <p>Answers will cite indexed document chunks and keep the conversation history.</p>
          </div>
        ) : null}
        {messages.map((message) => {
          const citedSources = getCitedSources(message);
          return (
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
                {message.metadata.confidence ? (
                  <span>{message.metadata.confidence} confidence</span>
                ) : null}
              </div>
              <MessageContent content={message.content} />
              {citedSources.length ? <CitationStrip sources={citedSources} /> : null}
            </article>
          );
        })}
        {isSending ? (
          <div className="message assistant pending">
            <div className="message-meta">
              <span>assistant</span>
            </div>
            <div className="typing-indicator" aria-label="Generating answer">
              <span />
              <span />
              <span />
            </div>
          </div>
        ) : null}
      </div>

      <form className="composer" onSubmit={submit}>
        <div className="composer-input">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleComposerKeyDown}
            placeholder="Ask about indexed knowledge..."
            rows={3}
          />
        </div>
        <button type="submit" disabled={!draft.trim() || isSending} title="Send message">
          {isSending ? (
            <LoaderCircle size={18} aria-hidden="true" className="spin" />
          ) : (
            <Send size={18} aria-hidden="true" />
          )}
          Send
        </button>
      </form>
    </section>
  );
}

function ConversationTitle({
  conversation,
  onRename,
}: {
  conversation: Conversation | null;
  onRename: (conversationId: string, title: string) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const displayTitle = conversation?.title || "New conversation";

  useEffect(() => {
    if (!isEditing) {
      setDraft(displayTitle);
    }
  }, [displayTitle, isEditing]);

  async function save() {
    const title = draft.trim();
    if (!conversation || !title || title === displayTitle || isSaving) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      await onRename(conversation.id, title);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  if (isEditing) {
    return (
      <form
        className="conversation-title-form"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          autoFocus
          maxLength={80}
          aria-label="Conversation title"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setDraft(displayTitle);
              setIsEditing(false);
            }
          }}
        />
        <button
          type="submit"
          className="icon-button"
          disabled={!draft.trim() || isSaving}
          title="Save title"
          aria-label="Save title"
        >
          <Check size={16} aria-hidden="true" />
        </button>
      </form>
    );
  }

  return (
    <div className="conversation-title-row">
      <h1>{displayTitle}</h1>
      {conversation ? (
        <button
          type="button"
          className="icon-button"
          onClick={() => {
            setDraft(displayTitle);
            setIsEditing(true);
          }}
          title="Rename conversation"
          aria-label="Rename conversation"
        >
          <Edit3 size={16} aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}

function MessageContent({ content }: { content: string }) {
  return <div className="message-content">{renderMarkdownBlocks(content)}</div>;
}

function renderMarkdownBlocks(content: string) {
  const blocks: Array<{ type: "code" | "list" | "paragraph"; content: string; items?: string[] }> =
    [];
  const lines = content.split("\n");
  let paragraph: string[] = [];
  let list: string[] = [];
  let code: string[] | null = null;

  function flushParagraph() {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", content: paragraph.join("\n") });
      paragraph = [];
    }
  }

  function flushList() {
    if (list.length) {
      blocks.push({ type: "list", content: "", items: list });
      list = [];
    }
  }

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (code) {
        blocks.push({ type: "code", content: code.join("\n") });
        code = null;
      } else {
        flushParagraph();
        flushList();
        code = [];
      }
      continue;
    }

    if (code) {
      code.push(line);
      continue;
    }

    const listMatch = line.match(/^\s*[-*]\s+(.+)$/);
    if (listMatch) {
      flushParagraph();
      list.push(listMatch[1]);
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();
  if (code) {
    blocks.push({ type: "code", content: code.join("\n") });
  }

  return blocks.map((block, index) => {
    if (block.type === "code") {
      return (
        <pre key={index}>
          <code>{block.content}</code>
        </pre>
      );
    }
    if (block.type === "list") {
      return (
        <ul key={index}>
          {block.items?.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
    }
    return <p key={index}>{renderInlineMarkdown(block.content)}</p>;
  });
}

function renderInlineMarkdown(content: string) {
  const parts = content.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function CitationStrip({ sources }: { sources: SourceReference[] }) {
  return (
    <div className="citation-strip" aria-label="Cited sources">
      {sources.map((source, index) => (
        <span key={source.chunk_id} className="citation-chip">
          Source {index + 1}: {source.document_title}, chunk {source.chunk_index}
        </span>
      ))}
    </div>
  );
}

function getCitedSources(message: ConversationMessage): SourceReference[] {
  if (message.role !== "assistant" || !message.cited_chunk_ids.length) {
    return [];
  }

  const sources = message.metadata.sources ?? [];
  const citedIds = new Set(message.cited_chunk_ids);
  return sources.filter((source) => citedIds.has(source.chunk_id));
}
