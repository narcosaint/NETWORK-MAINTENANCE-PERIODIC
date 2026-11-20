import { describe, expect, it } from "vitest";
import { photoCategory, signatureReady } from "../src/services/completion";
describe("compatibility with photo drafts from installed APKs", () => {
  it("uploads historical Indonesian category labels with the server category", () => {
    expect(photoCategory("Foto Access Point")).toBe("ap");
    expect(photoCategory("Foto perangkat")).toBe("device");
    expect(photoCategory("Foto area sampling")).toBe("area");
    expect(photoCategory("Foto temuan")).toBe("finding");
    expect(photoCategory("router")).toBe("router");
  });
});

it("rejects a tap before freezing a signature retry and accepts a drawn stroke", () => {
  expect(signatureReady([[[0.1, 0.2]]])).toBe(false);
  expect(
    signatureReady([
      Array.from({ length: 12 }, (_, i) => [i / 20, 0.5] as [number, number]),
    ]),
  ).toBe(true);
});

import { combinedAreaNotes } from "../src/services/areaNotes";
it("keeps installed draft findings and actions in one editable field", () => {
  const saved = {
    condition: "good" as const,
    notes: "Catatan",
    findings: "Baik",
    action: "Bersihkan",
    recommendation: "",
  };
  expect(combinedAreaNotes(undefined, saved)).toBe(
    "Catatan\nTemuan: Baik\nTindakan: Bersihkan",
  );
  expect(
    combinedAreaNotes(
      { findings: "Draf lama", action: "Tindakan lama", updatedAt: "" },
      saved,
    ),
  ).toBe("Catatan\nTemuan: Draf lama\nTindakan: Tindakan lama");
  expect(
    combinedAreaNotes({ notes: "", combinedNotes: true, updatedAt: "" }, saved),
  ).toBe("");
  expect(combinedAreaNotes({ updatedAt: "" }, saved)).toBe(
    "Catatan\nTemuan: Baik\nTindakan: Bersihkan",
  );
});
