import { Capacitor, registerPlugin } from "@capacitor/core";
import type { ApiClient } from "./api";
import type { LocalPhoto, Visit } from "../types";
export type Evidence = {
  id: string;
  session_id: string | null;
  category: string;
  caption: string;
  captured_at: string;
  created_at: string;
  url: string;
};
export type Completion = {
  ready: boolean;
  errors: string[];
  document_digest: string;
  can_submit: boolean;
  pdf_available: boolean;
  signature: null | {
    id: string;
    name: string;
    position: string;
    signed_at: string;
  };
  points: {
    id: string;
    name: string;
    floor: string;
    speedtest_accepted: boolean;
    failed_with_reason: boolean;
  }[];
};
export type Strokes = [number, number][][];
export type SignatureRequest = {
  id: string;
  expected_version: number;
  document_digest: string;
  name: string;
  position: string;
  consent: true;
  strokes: Strokes;
};
export async function blobBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Foto tidak dapat dibaca."));
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.readAsDataURL(blob);
  });
}
export function photoCategory(value: string): string {
  return (
    (
      {
        "Foto Access Point": "ap",
        "Foto perangkat": "device",
        "Foto perangkat jaringan": "device",
        "Foto area sampling": "area",
        "Foto temuan": "finding",
        "Foto temuan/kerusakan": "finding",
      } as Record<string, string>
    )[value] || value
  );
}
export async function uploadPhoto(
  api: ApiClient,
  visit: Visit,
  photo: LocalPhoto,
) {
  return api.request<{ visit: Visit; replayed: boolean }>(
    `/hotel-visits/${visit.id}/evidence`,
    "POST",
    {
      id: photo.id,
      expected_version: visit.version,
      session_id: photo.pointId === "infrastructure" ? null : photo.pointId,
      category: photoCategory(photo.category),
      caption: photo.caption,
      captured_at: photo.createdAt,
      content_type: photo.blob.type,
      image_base64: await blobBase64(photo.blob),
    },
  );
}
export type PdfDownload = {
  filename: string;
  content_type: string;
  data_base64: string;
};
const documents = registerPlugin<{
  sharePdf(input: { filename: string; data_base64: string }): Promise<void>;
}>("HotelDocuments");
export async function openPdf(pdf: PdfDownload) {
  if (Capacitor.isNativePlatform()) {
    await documents.sharePdf(pdf);
    return;
  }
  const binary = atob(pdf.data_base64);
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  const url = URL.createObjectURL(
    new Blob([bytes], { type: "application/pdf" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = pdf.filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export function signatureReady(strokes: Strokes): boolean {
  const count = strokes.reduce((n, stroke) => n + stroke.length, 0);
  const travel = strokes.reduce(
    (n, stroke) =>
      n +
      stroke
        .slice(1)
        .reduce(
          (m, point, i) =>
            m + Math.hypot(point[0] - stroke[i][0], point[1] - stroke[i][1]),
          0,
        ),
    0,
  );
  return count >= 8 && count <= 8000 && travel >= 0.05;
}
