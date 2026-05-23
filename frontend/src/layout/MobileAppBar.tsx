import { Archive, PanelLeftOpen, RefreshCw } from "lucide-react";
import type { View } from "./types";

type MobileAppBarProps = {
  view: View;
  sourceCount: number;
  onOpenNavigation: () => void;
  onOpenEvidence: () => void;
  onRefreshDocuments: () => void;
};

export function MobileAppBar({
  view,
  sourceCount,
  onOpenNavigation,
  onOpenEvidence,
  onRefreshDocuments,
}: MobileAppBarProps) {
  return (
    <header className="mobile-app-bar">
      <button
        type="button"
        className="icon-button"
        onClick={onOpenNavigation}
        aria-label="Open navigation"
        title="Open navigation"
      >
        <PanelLeftOpen size={18} aria-hidden="true" />
      </button>
      <div>
        <strong>{view === "chat" ? "Chat" : "Documents"}</strong>
        <span>KnowledgeAssistant</span>
      </div>
      {view === "chat" ? (
        <button
          type="button"
          className="mobile-evidence-button"
          onClick={onOpenEvidence}
          aria-label="Open evidence"
          title="Open evidence"
        >
          <Archive size={17} aria-hidden="true" />
          <span>{sourceCount}</span>
        </button>
      ) : (
        <button
          type="button"
          className="icon-button"
          onClick={onRefreshDocuments}
          aria-label="Refresh documents"
          title="Refresh documents"
        >
          <RefreshCw size={17} aria-hidden="true" />
        </button>
      )}
    </header>
  );
}
