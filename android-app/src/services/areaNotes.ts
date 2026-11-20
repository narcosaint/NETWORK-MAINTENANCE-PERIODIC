import type { PointDraft, SamplingNotes } from "../types";
export function combinedAreaNotes(
  draft?: PointDraft,
  saved?: SamplingNotes,
): string {
  if (draft?.combinedNotes) return draft.notes || "";
  const base = { ...saved, ...draft };
  const parts = [
    base?.notes,
    base?.findings ? "Temuan: " + base.findings : "",
    base?.action ? "Tindakan: " + base.action : "",
  ];
  return parts.filter(Boolean).join("\n");
}
