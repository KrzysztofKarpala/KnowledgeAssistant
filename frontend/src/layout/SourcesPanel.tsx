import { Archive, PanelRightClose, PanelRightOpen } from "lucide-react";
import type { SourceReference } from "../api";

type SourcesPanelProps = {
  sources: SourceReference[];
  isOpen: boolean;
  onToggle: () => void;
};

export function SourcesPanel({ sources, isOpen, onToggle }: SourcesPanelProps) {
  return (
    <aside className={`sources-panel ${isOpen ? "mobile-open" : "collapsed"}`}>
      <div className="panel-title">
        <button
          type="button"
          className="panel-toggle"
          onClick={onToggle}
          title={isOpen ? "Hide evidence" : "Show evidence"}
          aria-pressed={isOpen}
        >
          {isOpen ? (
            <PanelRightClose size={18} aria-hidden="true" />
          ) : (
            <PanelRightOpen size={18} aria-hidden="true" />
          )}
          <span>Evidence</span>
        </button>
        <span className="source-count">{sources.length}</span>
      </div>
      {isOpen ? <SourcePanel sources={sources} /> : null}
    </aside>
  );
}

function SourcePanel({ sources }: { sources: SourceReference[] }) {
  if (!sources.length) {
    return (
      <div className="empty-state evidence-empty">
        <Archive size={22} aria-hidden="true" />
        <span>Select an assistant answer to inspect its sources.</span>
      </div>
    );
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
