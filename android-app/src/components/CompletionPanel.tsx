import { useEffect, useRef, useState } from "react";
import type { ApiClient } from "../services/api";
import type { Visit } from "../types";
import { store, flushLocal } from "../services/storage";
import {
  openPdf,
  signatureReady,
  type Completion,
  type SignatureRequest,
  type Strokes,
  type PdfDownload,
} from "../services/completion";
import { gpsService } from "../services/native";
import { SignaturePad } from "./SignaturePad";
import { Card, Field, Message } from "./ui";
import { when } from "../domain";
type Draft = {
  name: string;
  position: string;
  strokes: Strokes;
  consent: boolean;
};
export function CompletionPanel({
  api,
  visit,
  scope,
  online,
  blocked,
  busy,
  onVisit,
  prepare,
}: {
  api: ApiClient;
  visit: Visit;
  scope: string;
  online: boolean;
  blocked: boolean;
  busy: boolean;
  onVisit: (visit: Visit) => Promise<void>;
  prepare: () => Promise<Visit>;
}) {
  const [info, setInfo] = useState<Completion>(),
    [draft, setDraft] = useState<Draft>({
      name: visit.report.pic_name || "",
      position: "",
      strokes: [],
      consent: false,
    }),
    [ready, setReady] = useState(false),
    [working, setWorking] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const lock = useRef(false),
    key = scope + "pic-draft";
  const feedback = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error || working) {
      const target =
        document.getElementById("area-conflict") || feedback.current;
      target?.focus({ preventScroll: true });
      target?.scrollIntoView({ block: "nearest" });
    }
  }, [error, working]);
  useEffect(() => {
    let active = true;
    void store
      .get<Draft>(key)
      .then((saved) => {
        if (active) {
          if (saved) setDraft(saved);
          setReady(true);
        }
      })
      .catch((e) => {
        if (active) setError((e as Error).message);
      });
    return () => {
      active = false;
    };
  }, [key]);
  useEffect(() => {
    let active = true;
    if (!online) {
      setInfo(undefined);
      return;
    }
    void api
      .request<Completion>(`/hotel-visits/${visit.id}/completion`)
      .then((value) => {
        if (active) setInfo(value);
      })
      .catch((e) => {
        if (active) setError((e as Error).message);
      });
    return () => {
      active = false;
    };
  }, [api, visit.id, visit.version, online]);
  const editing = ["in_progress", "revision_requested"].includes(visit.status);
  const disabled = busy || working || !ready;
  const change = (next: Draft) => {
    setDraft(next);
    void store.put(key, next).catch((e) => setError((e as Error).message));
  };
  const run = async (action: () => Promise<void>) => {
    if (lock.current) return;
    lock.current = true;
    setWorking(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      lock.current = false;
      setWorking(false);
    }
  };
  const validate = async () => {
    if (!online)
      throw new Error("Hubungkan ke server untuk menyimpan laporan.");
    const current = await prepare();
    const review = await api.request<Completion>(
      `/hotel-visits/${current.id}/completion`,
    );
    setInfo(review);
    if (!review.ready) throw new Error(review.errors.join(". "));
    return { current, review };
  };
  const sign = () =>
    run(async () => {
      if (
        !draft.name.trim() ||
        !draft.position.trim() ||
        !draft.consent ||
        !signatureReady(draft.strokes)
      )
        throw new Error(
          "Isi nama, jabatan, tanda tangan dan persetujuan PIC terlebih dahulu.",
        );
      await flushLocal(scope);
      // Reconcile a lost response using the original UUID before creating a new signature.
      let request = await store.get<SignatureRequest>(scope + "pic-outbox");
      if (request) {
        try {
          const response = await api.request<{
            visit: Visit;
            completion: Completion;
          }>(`/hotel-visits/${visit.id}/pic-signature`, "POST", request);
          await store.remove(scope + "pic-outbox");
          await onVisit(response.visit);
          setInfo(response.completion);
          if (!response.completion.signature)
            throw new Error(
              "Isi laporan berubah setelah tanda tangan diterima. Tinjau kembali lalu simpan tanda tangan untuk laporan terbaru.",
            );
          setNotice("Tanda tangan PIC tersimpan.");
          return;
        } catch (e) {
          if ((e as { status?: number }).status !== 409) throw e;
          await store.remove(scope + "pic-outbox");
          throw new Error(
            "Isi laporan berubah. Tinjau kembali laporan sebelum menyimpan tanda tangan.",
            { cause: e },
          );
        }
      }
      const { current, review } = await validate();
      request = {
        id: crypto.randomUUID(),
        expected_version: current.version,
        document_digest: review.document_digest,
        name: draft.name.trim(),
        position: draft.position.trim(),
        consent: true,
        strokes: draft.strokes,
      };
      await store.put(scope + "pic-outbox", request);
      const response = await api.request<{
        visit: Visit;
        completion: Completion;
      }>(`/hotel-visits/${current.id}/pic-signature`, "POST", request);
      await store.remove(scope + "pic-outbox");
      await onVisit(response.visit);
      setInfo(response.completion);
      setNotice("Tanda tangan PIC tersimpan.");
    });
  const submit = () =>
    run(async () => {
      if (!online)
        throw new Error("Hubungkan ke server untuk mengirim laporan.");
      const latest = await api.visit(visit.id);
      if (["submitted", "approved"].includes(latest.status)) {
        await onVisit(latest);
        setNotice("Laporan sudah dikirim ke supervisor.");
        return;
      }
      const { current, review } = await validate();
      if (!review.signature)
        throw new Error(
          "Simpan tanda tangan PIC untuk laporan terbaru terlebih dahulu.",
        );
      let body: unknown = { expected_version: current.version };
      if (current.status !== "revision_requested") {
        let evidence;
        try {
          evidence = await gpsService.current();
        } catch {
          evidence = {
            device_time: new Date().toISOString(),
            gps_exception_reason:
              "GPS tidak tersedia dari perangkat saat check-out; dicatat otomatis oleh aplikasi.",
          };
        }
        body = { expected_version: current.version, ...evidence };
      }
      const response = await api.request<Visit>(
        `/hotel-visits/${current.id}/${current.status === "revision_requested" ? "resubmit" : "check-out"}`,
        "POST",
        body,
      );
      await onVisit(response);
      setNotice("Laporan dikirim. Menunggu review supervisor.");
    });
  const preview = () =>
    run(async () => {
      if (!online) throw new Error("Review PDF memerlukan koneksi server.");
      const current = await prepare();
      const pdf = await api.request<PdfDownload>(
        `/hotel-visits/${current.id}/report-preview-download`,
      );
      await openPdf(pdf);
    });
  const pdf = () =>
    run(async () => {
      if (online && !info?.pdf_available)
        throw new Error(
          "PDF final tersedia setelah tanda tangan PIC tersimpan. Gunakan Review Hasil PDF untuk melihat drafnya.",
        );
      let saved: PdfDownload | undefined;
      if (online) {
        saved = await api.request<PdfDownload>(
          `/hotel-visits/${visit.id}/report-download`,
        );
        await store.put(scope + "pdf", saved);
      } else {
        saved = await store.get<PdfDownload>(scope + "pdf");
        if (!saved)
          throw new Error("PDF belum diunduh. Hubungkan ke server dahulu.");
        setNotice(
          "Membuka salinan PDF terakhir yang diunduh; belum memeriksa perubahan server.",
        );
      }
      await openPdf(saved);
    });
  return (
    <Card title="Review, PIC & laporan PDF">
      <div ref={feedback} tabIndex={-1}>
        {error && <Message error>{error}</Message>}
        {working && <Message>Memproses permintaan…</Message>}
        {notice && <Message>{notice}</Message>}
      </div>
      {blocked && (
        <p role="status">
          Perubahan lokal akan dikirim saat membuka draf PDF atau menyimpan
          tanda tangan PIC.
        </p>
      )}
      {info && !blocked && (
        <>
          {!!info.errors.length && (
            <>
              <p>Lengkapi pemeriksaan berikut:</p>
              <ul>
                {info.errors.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </>
          )}
          {info.ready && <p>Seluruh pemeriksaan wajib sudah lengkap.</p>}
          {info.signature && (
            <p>
              PIC: {info.signature.name} · {info.signature.position} ·{" "}
              {when(info.signature.signed_at)}
            </p>
          )}
        </>
      )}
      {editing && (!info?.signature || blocked) && (
        <fieldset disabled={disabled}>
          <legend>Persetujuan PIC</legend>
          <button
            className="secondary wide"
            disabled={disabled || !online}
            onClick={() => void preview()}
          >
            Review Hasil PDF
          </button>
          <Field label="Nama PIC">
            <input
              value={draft.name}
              maxLength={200}
              onChange={(e) => change({ ...draft, name: e.target.value })}
            />
          </Field>
          <Field label="Jabatan PIC">
            <input
              value={draft.position}
              maxLength={200}
              onChange={(e) => change({ ...draft, position: e.target.value })}
            />
          </Field>
          <SignaturePad
            value={draft.strokes}
            disabled={disabled}
            onChange={(strokes) => change({ ...draft, strokes })}
          />
          <label className="consent-line">
            <input
              type="checkbox"
              checked={draft.consent}
              onChange={(e) => change({ ...draft, consent: e.target.checked })}
            />
            <span>
              Saya sebagai PIC telah meninjau dan menyetujui isi laporan ini.
            </span>
          </label>
          <button
            className="primary wide"
            disabled={disabled || !online}
            onClick={() => void sign()}
          >
            {working ? "Menyimpan…" : "Simpan tanda tangan PIC"}
          </button>
        </fieldset>
      )}
      {editing && (
        <button
          className="primary wide"
          disabled={disabled || !online}
          onClick={() => void submit()}
        >
          Check-out & kirim laporan
        </button>
      )}
      <button
        className="secondary wide"
        disabled={disabled}
        onClick={() => void pdf()}
      >
        Unduh / bagikan PDF
      </button>
    </Card>
  );
}
