import { useEffect, useRef, useState } from "react";
import { ApiClient, ApiError } from "../services/api";
import { store, enqueueLocal, flushLocal } from "../services/storage";
import {
  fieldOutboxKey,
  submitFieldLocations,
} from "../services/fieldLocations";
import type { FieldLocationInput, Visit } from "../types";
import { Card, Field, Message } from "./ui";
type Draft = {
  floor: string;
  name: string;
  reason: string;
  points: FieldLocationInput["points"];
};
const emptyPoint = () => ({ name: "", location: null, device_id: null });
const empty = (): Draft => ({
  floor: "new",
  name: "",
  reason: "",
  points: [emptyPoint()],
});
export function FieldLocationForm({
  api,
  scope,
  visit,
  online,
  busy,
  onVisit,
}: {
  api: ApiClient;
  scope: string;
  visit: Visit;
  online: boolean;
  busy: boolean;
  onVisit: (visit: Visit) => Promise<void>;
}) {
  const [draft, setDraft] = useState<Draft>(empty),
    [open, setOpen] = useState(false),
    [ready, setReady] = useState(false),
    [sending, setSending] = useState(false),
    [pending, setPending] = useState(false),
    [available, setAvailable] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const mounted = useRef(true);
  const inFlight = useRef(false);
  const draftKey = scope + "field-location-draft";
  useEffect(() => {
    mounted.current = true;
    void (async () => {
      try {
        await flushLocal(scope);
        const saved = await store.get<Draft>(draftKey);
        const queued = await store.get(fieldOutboxKey(scope));
        if (mounted.current) {
          if (saved) setDraft(saved);
          setPending(!!queued);
          setReady(true);
        }
      } catch (e) {
        if (mounted.current) setError((e as Error).message);
      }
    })();
    return () => {
      mounted.current = false;
    };
  }, [scope, draftKey]);
  useEffect(() => {
    if (!open || !online) return;
    let active = true;
    void api
      .fieldLocationsEnabled()
      .then((enabled) => {
        if (active) {
          setAvailable(enabled);
        }
      })
      .catch((e) => {
        if (active) {
          setAvailable(false);
          setError(
            e instanceof ApiError && [404, 503].includes(e.status)
              ? "Penambahan lokasi lapangan belum aktif di server. Draf tetap bisa disiapkan."
              : (e as Error).message,
          );
        }
      });
    return () => {
      active = false;
    };
  }, [api, open, online]);
  const change = (next: Draft) => {
    setDraft(next);
    setNotice("");
    void enqueueLocal(scope, async () => {
      await store.put(draftKey, next);
    })
      .then(() => {
        if (mounted.current) setNotice("Draf lokasi tersimpan di perangkat.");
      })
      .catch((e) => {
        if (mounted.current) setError((e as Error).message);
      });
  };
  const disabled = !ready || sending || busy || pending;
  const send = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setSending(true);
    setError("");
    setNotice("");
    try {
      await flushLocal(scope);
      const rows = draft.points.filter(
        (p) => p.name.trim() || p.location?.trim() || p.device_id,
      );
      if (!pending && (!rows.length || rows.some((p) => !p.name.trim())))
        throw new Error(
          "Isi nama setiap area nyata; baris kosong boleh dikosongkan.",
        );
      const input: FieldLocationInput = {
        ...(draft.floor === "new"
          ? { floor_name: draft.name.trim() }
          : { coverage_floor_id: draft.floor }),
        reason:
          draft.reason.trim() || "Penambahan area oleh teknisi di lapangan",
        points: rows,
      };
      const updated = await submitFieldLocations(api, scope, visit, input);
      await onVisit(updated);
      await store.remove(draftKey);
      if (mounted.current) {
        setDraft(empty());
        setPending(false);
        setNotice(
          "Area tersimpan. Pengujian Wi-Fi dan speedtest dicatat terpisah untuk setiap area.",
        );
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        try {
          await onVisit(await api.visit(visit.id));
        } catch {
          /* Retain local draft on refresh failure. */
        }
      }
      if (mounted.current) {
        setError((e as Error).message);
        try {
          setPending(!!(await store.get(fieldOutboxKey(scope))));
        } catch (storageError) {
          setError((storageError as Error).message);
        }
      }
    } finally {
      inFlight.current = false;
      if (mounted.current) setSending(false);
    }
  };
  return (
    <Card title="Test Area">
      <button
        className="secondary wide"
        onClick={() => setOpen(!open)}
        disabled={sending}
      >
        {open ? "Tutup form area" : "Tambah Area"}
      </button>
      {open && (
        <div className="stack">
          <p>
            Tambahkan lokasi aktual pada kunjungan ini. Target awal 4 area per
            lantai; isi nama area yang benar-benar diperiksa.
          </p>
          {!visit.sampling_coverage && (
            <p>
              Cakupan sampling baru dibuat saat dikirim. Data dan hasil AP lama
              tetap tersimpan di laporan utama; hasilnya tidak disalin menjadi
              pengujian area.
            </p>
          )}
          <Field label="Lantai / kelompok area">
            <select
              disabled={disabled}
              value={draft.floor}
              onChange={(e) => change({ ...draft, floor: e.target.value })}
            >
              <option value="new">Tambah lantai / kelompok baru</option>
              {visit.sampling_coverage?.floors.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </Field>
          {draft.floor === "new" && (
            <Field label="Nama lantai / kelompok">
              <input
                maxLength={100}
                disabled={disabled}
                value={draft.name}
                onChange={(e) => change({ ...draft, name: e.target.value })}
              />
            </Field>
          )}
          {draft.points.map((p, index) => (
            <fieldset key={index} disabled={disabled}>
              <legend>Area {index + 1}</legend>
              <Field label={`Nama area ${index + 1}`}>
                <input
                  maxLength={200}
                  value={p.name}
                  onChange={(e) =>
                    change({
                      ...draft,
                      points: draft.points.map((row, i) =>
                        i === index ? { ...row, name: e.target.value } : row,
                      ),
                    })
                  }
                />
              </Field>
              {draft.points.length > 1 && (
                <button
                  className="secondary"
                  onClick={() =>
                    change({
                      ...draft,
                      points: draft.points.filter((_, i) => i !== index),
                    })
                  }
                >
                  Hapus baris area
                </button>
              )}
            </fieldset>
          ))}
          <button
            className="secondary wide"
            disabled={disabled || draft.points.length >= 32}
            onClick={() =>
              change({ ...draft, points: [...draft.points, emptyPoint()] })
            }
          >
            Tambah baris area
          </button>

          {pending && (
            <p>
              Respons kiriman sebelumnya belum pasti. Kirim ulang memakai data
              yang sama agar tidak menggandakan lokasi.
            </p>
          )}
          {!online && (
            <p>Offline: lanjutkan isi draf; kirim setelah tersambung.</p>
          )}
          <button
            className="primary wide"
            disabled={!ready || busy || sending || !online || !available}
            onClick={() => void send()}
          >
            {sending
              ? "Mengirim lokasi…"
              : pending
                ? "Kirim ulang area"
                : "Simpan area"}
          </button>
        </div>
      )}
      {error && <Message error>{error}</Message>}
      {notice && <p role="status">{notice}</p>}
    </Card>
  );
}
