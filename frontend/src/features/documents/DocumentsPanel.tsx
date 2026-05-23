import { FormEvent, useState } from "react";
import { Edit3, FilePlus, FileText, RefreshCw, Save, Trash2, X } from "lucide-react";
import type { DocumentItem } from "../../api";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { formatDate } from "../../lib/format";
import type { DocumentDraft, DocumentEditorState } from "./types";

type DocumentsPanelProps = {
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
    payload: DocumentDraft,
  ) => Promise<void>;
  onDelete: (documentId: string) => Promise<void>;
};

export function DocumentsPanel({
  documents,
  onRefresh,
  onCreate,
  onUpdate,
  onDelete,
}: DocumentsPanelProps) {
  const [editor, setEditor] = useState<DocumentEditorState | null>(null);
  const [pendingDeleteDocument, setPendingDeleteDocument] = useState<DocumentItem | null>(null);
  const archivedCount = documents.filter((document) => document.status === "archived").length;

  async function saveDocument(draft: DocumentDraft) {
    if (editor?.mode === "edit") {
      await onUpdate(editor.document.id, draft);
    } else {
      await onCreate(draft);
    }
    setEditor(null);
  }

  async function removeDocument(documentId: string) {
    await onDelete(documentId);
    setPendingDeleteDocument(null);
  }

  return (
    <section className="documents-panel">
      <header className="content-header documents-header">
        <div>
          <span className="eyebrow">Knowledge base</span>
          <h1>Documents</h1>
        </div>
        <div className="header-actions">
          <button className="secondary-button" onClick={() => void onRefresh()}>
            <RefreshCw size={16} aria-hidden="true" />
            Refresh
          </button>
          <button onClick={() => setEditor({ mode: "create" })}>
            <FilePlus size={17} aria-hidden="true" />
            Add document
          </button>
        </div>
      </header>

      <div className="document-summary" aria-label="Document summary">
        <div>
          <strong>{documents.length}</strong>
          <span>Total documents</span>
        </div>
        <div>
          <strong>{documents.length - archivedCount}</strong>
          <span>Active</span>
        </div>
        <div>
          <strong>{archivedCount}</strong>
          <span>Archived</span>
        </div>
      </div>

      <div className="document-list">
        {documents.map((document) => (
          <DocumentCard
            key={document.id}
            document={document}
            onEdit={() => setEditor({ mode: "edit", document })}
            onDelete={() => setPendingDeleteDocument(document)}
          />
        ))}
        {documents.length === 0 ? (
          <div className="document-empty">
            <FileText size={22} aria-hidden="true" />
            <span>No documents indexed yet.</span>
          </div>
        ) : null}
      </div>

      {editor ? (
        <DocumentEditorModal
          editor={editor}
          onCancel={() => setEditor(null)}
          onSave={saveDocument}
        />
      ) : null}

      {pendingDeleteDocument ? (
        <ConfirmDialog
          title="Delete document?"
          body={`This will remove "${pendingDeleteDocument.title}" from the knowledge base.`}
          confirmLabel="Delete"
          onCancel={() => setPendingDeleteDocument(null)}
          onConfirm={() => void removeDocument(pendingDeleteDocument.id)}
        />
      ) : null}
    </section>
  );
}

function DocumentEditorModal({
  editor,
  onCancel,
  onSave,
}: {
  editor: DocumentEditorState;
  onCancel: () => void;
  onSave: (draft: DocumentDraft) => Promise<void>;
}) {
  const [draft, setDraft] = useState<DocumentDraft>(() => ({
    title: editor.document?.title ?? "",
    content: editor.document?.content ?? "",
    status: editor.document?.status ?? "active",
    version: editor.document?.version ?? "",
    effective_from: editor.document?.effective_from ?? "",
  }));
  const [isSaving, setIsSaving] = useState(false);
  const isValid = draft.title.trim() && draft.content.trim();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || isSaving) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave({
        ...draft,
        title: draft.title.trim(),
        content: draft.content.trim(),
        version: draft.version.trim(),
      });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <form
        className="document-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={submit}
      >
        <header>
          <div>
            <span className="eyebrow">Knowledge base</span>
            <h2 id="document-modal-title">
              {editor.mode === "edit" ? "Edit document" : "Add document"}
            </h2>
          </div>
          <button type="button" className="icon-button" onClick={onCancel} title="Close">
            <X size={16} aria-hidden="true" />
          </button>
        </header>

        <div className="form-grid">
          <label>
            Title
            <input
              value={draft.title}
              onChange={(event) =>
                setDraft((current) => ({ ...current, title: event.target.value }))
              }
              autoFocus
            />
          </label>
          <label>
            Version
            <input
              value={draft.version}
              onChange={(event) =>
                setDraft((current) => ({ ...current, version: event.target.value }))
              }
            />
          </label>
          <label>
            Effective from
            <input
              type="date"
              value={draft.effective_from}
              onChange={(event) =>
                setDraft((current) => ({ ...current, effective_from: event.target.value }))
              }
            />
          </label>
        </div>
        {editor.mode === "edit" ? (
          <label>
            Status
            <select
              value={draft.status}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  status: event.target.value as DocumentDraft["status"],
                }))
              }
            >
              <option value="active">active</option>
              <option value="archived">archived</option>
            </select>
          </label>
        ) : null}
        <label>
          Content
          <textarea
            value={draft.content}
            onChange={(event) =>
              setDraft((current) => ({ ...current, content: event.target.value }))
            }
            rows={11}
          />
        </label>
        <div className="confirm-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" disabled={!isValid || isSaving}>
            <Save size={16} aria-hidden="true" />
            Save
          </button>
        </div>
      </form>
    </div>
  );
}

function DocumentCard({
  document,
  onEdit,
  onDelete,
}: {
  document: DocumentItem;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <article className="document-card">
      <div>
        <div className="document-title">
          <FileText size={18} aria-hidden="true" />
          <strong>{document.title}</strong>
          <span className={`status-pill ${document.status}`}>{document.status}</span>
        </div>
        <p>{document.content}</p>
      </div>
      <div className="document-card-side">
        <dl>
          <div>
            <dt>Version</dt>
            <dd>{document.version || "unknown"}</dd>
          </div>
          <div>
            <dt>Effective</dt>
            <dd>{document.effective_from || "unknown"}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDate(document.updated_at)}</dd>
          </div>
        </dl>
        <div className="document-actions">
          <button type="button" className="secondary-button" onClick={onEdit}>
            <Edit3 size={16} aria-hidden="true" />
            Edit
          </button>
          <button type="button" className="danger-button" onClick={onDelete}>
            <Trash2 size={16} aria-hidden="true" />
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}
