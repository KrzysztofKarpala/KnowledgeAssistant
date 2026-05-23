import type { DocumentItem } from "../../api";

export type DocumentDraft = {
  title: string;
  content: string;
  status: "active" | "archived";
  version: string;
  effective_from: string;
};

export type DocumentEditorState =
  | { mode: "create"; document?: undefined }
  | { mode: "edit"; document: DocumentItem };
