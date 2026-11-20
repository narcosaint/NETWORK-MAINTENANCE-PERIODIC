import { useEffect, useState } from "react";
import type { ApiClient } from "../services/api";
import { enqueueLocal, flushLocal, store } from "../services/storage";
import { Card, Field, Message } from "./ui";

type Profile = {
  phone: string | null;
  email: string | null;
  division: string | null;
  work_area: string | null;
  version: number;
};
const empty: Profile = {
  phone: null,
  email: null,
  division: null,
  work_area: null,
  version: 0,
};
const fields = [
  ["phone", "Nomor WhatsApp", "tel", 40],
  ["email", "Email kantor", "email", 254],
  ["division", "Divisi", "text", 200],
  ["work_area", "Wilayah kerja", "text", 200],
] as const;

export function ContactProfile({
  api,
  scope,
  online,
}: {
  api: ApiClient;
  scope: string;
  online: boolean;
}) {
  const [form, setForm] = useState<Profile>(empty);
  const [server, setServer] = useState<Profile>();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(0);
  const key = scope + "contact-profile";
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void (async () => {
      try {
        await flushLocal(key);
        const [draft, cached] = await Promise.all([
          store.get<Profile>(key + ":draft"),
          store.get<Profile>(key),
        ]);
        if (!active) return;
        setForm(draft || cached || empty);
        setDirty(!!draft);
        setServer(cached);
        if (online) {
          const fresh = await api.request<Profile>("/auth/me/profile");
          if (!active) return;
          setServer(fresh);
          if (!draft) setForm(fresh);
          await store.put(key, fresh);
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [api, key, online, reload]);
  const change = (next: Profile) => {
    setForm(next);
    setDirty(true);
    setNotice("Menyimpan draf profil…");
    void enqueueLocal(key, () => store.put(key + ":draft", next)).then(
      () =>
        setNotice(
          "Draf profil tersimpan di perangkat. Tekan Simpan Profil untuk mengirim.",
        ),
      (e) => setError((e as Error).message),
    );
  };
  const conflict = dirty && server && form.version !== server.version;
  const save = async () => {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await flushLocal(key);
      if (!online)
        throw new Error(
          "Offline. Draf profil tetap tersimpan; kirim saat online.",
        );
      if (conflict)
        throw new Error("Tinjau perubahan profil server terlebih dahulu.");
      const { version, ...data } = form;
      const saved = await api.request<Profile>("/auth/me/profile", "PUT", {
        ...data,
        expected_version: version,
      });
      await store.put(key, saved);
      await store.remove(key + ":draft");
      setForm(saved);
      setServer(saved);
      setDirty(false);
      setNotice("Profil tersimpan di server.");
    } catch (e) {
      setError((e as Error).message);
      if ((e as { status?: number }).status === 409) setReload((n) => n + 1);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card title="Kontak & wilayah kerja">
      {error && <Message error>{error}</Message>}
      {notice && <Message>{notice}</Message>}
      {loading && <p role="status">Memuat profil…</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <fieldset className="form-body" disabled={loading || busy}>
          {fields.map(([key, label, type, maxLength]) => (
            <Field key={key} label={label}>
              <input
                type={type}
                autoComplete={
                  key === "phone" ? "tel" : key === "email" ? "email" : "off"
                }
                maxLength={maxLength}
                value={form[key] || ""}
                onChange={(e) =>
                  change({ ...form, [key]: e.target.value || null })
                }
              />
            </Field>
          ))}
          {conflict && server && (
            <div className="profile-conflict">
              <p>
                Profil server sudah berubah. Bandingkan sebelum menyimpan draf.
              </p>
              <dl className="info-list">
                {fields.map(([key, label]) => (
                  <div key={key}>
                    <dt>{label} di server</dt>
                    <dd>{server[key] || "Belum diisi"}</dd>
                  </div>
                ))}
              </dl>
              <button
                type="button"
                className="secondary wide"
                onClick={() => change({ ...form, version: server.version })}
              >
                Gunakan draf setelah review
              </button>
              <button
                type="button"
                className="secondary wide"
                onClick={() => change(server)}
              >
                Gunakan isian server
              </button>
            </div>
          )}
          <button className="primary wide" disabled={!dirty || !!conflict}>
            {busy ? "Menyimpan…" : "Simpan Profil"}
          </button>
        </fieldset>
      </form>
    </Card>
  );
}
