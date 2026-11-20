import { PhotoPicker } from "./PhotoPicker";
import { useEffect, useState } from "react";
import type { ApiClient } from "../services/api";
import type { LocalPhoto, Visit } from "../types";
import { Card, Field, Message } from "./ui";
import { when } from "../domain";
import type { Evidence } from "../services/completion";
export function PhotoPreview({
  api,
  visitId,
  photo,
}: {
  api: ApiClient;
  visitId: string;
  photo: Evidence;
}) {
  const [src, setSrc] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void api
      .request<{ image_base64: string }>(
        `/hotel-visits/${visitId}/evidence/${photo.id}/thumbnail`,
      )
      .then((value) => {
        if (active) setSrc("data:image/jpeg;base64," + value.image_base64);
      })
      .catch(() => {
        if (active)
          setError("Pratinjau belum tersedia. Foto tetap tersimpan di server.");
      });
    return () => {
      active = false;
    };
  }, [api, visitId, photo.id]);
  return (
    <article className="photo-card">
      {src && <img src={src} alt={photo.caption || photo.category} />}
      <strong>{photo.category.toUpperCase()}</strong>
      <p>{photo.caption}</p>
      <small>{when(photo.captured_at)} · Server</small>
      {error && <p>{error}</p>}
    </article>
  );
}
function LocalPreview({ photo }: { photo: LocalPhoto }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const next = URL.createObjectURL(photo.blob);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [photo.blob]);
  return (
    <article className="photo-card">
      <img src={url || undefined} alt={photo.caption || photo.category} />
      <strong>{photo.category.toUpperCase()}</strong>
      <p>{photo.caption}</p>
      <small>{when(photo.createdAt)} · Belum dikirim</small>
    </article>
  );
}
export function EvidencePanel({
  api,
  visit,
  photos,
  busy,
  online,
  editable,
  addPhotos,
  upload,
  removePhoto,
}: {
  api: ApiClient;
  visit: Visit;
  photos: LocalPhoto[];
  busy: boolean;
  online: boolean;
  editable: boolean;
  addPhotos: (photos: LocalPhoto[]) => Promise<void>;
  upload: (photo: LocalPhoto) => Promise<void>;
  removePhoto: (photo: LocalPhoto) => Promise<void>;
}) {
  const [category, setCategory] = useState("router"),
    [caption, setCaption] = useState(""),
    [error, setError] = useState("");
  return (
    <Card title="Dokumentasi & sinkronisasi foto">
      {error && <Message error>{error}</Message>}
      <p>
        Foto area dan dokumentasi utama harus dikirim ke server agar masuk
        laporan PDF.
      </p>
      {editable && (
        <fieldset disabled={busy}>
          <legend>Tambah dokumentasi utama</legend>
          <Field label="Kategori">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {[
                "router",
                "switch",
                "rack",
                "backbone",
                "ap",
                "cable",
                "finding",
              ].map((c) => (
                <option key={c} value={c}>
                  {c.toUpperCase()}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Keterangan">
            <textarea
              value={caption}
              maxLength={2000}
              onChange={(e) => setCaption(e.target.value)}
            />
          </Field>
          <PhotoPicker
            label="Ambil / pilih foto"
            disabled={busy}
            onFiles={async (files) => {
              await addPhotos(
                files.map((file) => ({
                  id: crypto.randomUUID(),
                  pointId: "infrastructure",
                  category,
                  caption,
                  createdAt: new Date().toISOString(),
                  blob: file,
                })),
              );
              setCaption("");
            }}
          />
        </fieldset>
      )}
      <div className="photo-grid">
        {photos.map((photo) => (
          <div key={photo.id}>
            <LocalPreview photo={photo} />
            <button
              className="primary"
              disabled={busy || !online || !editable}
              onClick={() =>
                void upload(photo).catch((e) => setError((e as Error).message))
              }
            >
              Kirim foto ke server
            </button>
            <button
              className="secondary"
              disabled={busy || !editable}
              onClick={() =>
                void removePhoto(photo).catch((e) =>
                  setError((e as Error).message),
                )
              }
            >
              Hapus foto lokal
            </button>
          </div>
        ))}
      </div>
      {!!visit.evidence?.length && (
        <details>
          <summary>Foto tersimpan di server ({visit.evidence.length})</summary>
          <div className="photo-grid">
            {visit.evidence.map((photo) => (
              <PhotoPreview
                key={photo.id}
                api={api}
                visitId={visit.id}
                photo={photo}
              />
            ))}
          </div>
        </details>
      )}
    </Card>
  );
}
