import type { Backbone, Report, Visit } from "../types";
import { Badge, Card, Field, Message } from "../components/ui";
type Props = {
  visit: Visit;
  report: Report;
  onChange: (r: Report) => void;
  save: () => void;
  editable: boolean;
  busy: boolean;
  hasDraft: boolean;
};
export function ReportForm({
  visit,
  report: r,
  onChange,
  save,
  editable,
  busy,
  hasDraft,
}: Props) {
  const set = <K extends keyof Report>(key: K, value: Report[K]) =>
    onChange({ ...r, [key]: value });
  const text = (key: keyof Report, label: string, multiline = false) => (
    <Field label={label}>
      {multiline ? (
        <textarea
          rows={3}
          maxLength={5000}
          value={String(r[key] ?? "")}
          onChange={(e) => set(key, e.target.value || null)}
        />
      ) : (
        <input
          maxLength={key === "pic_contact" ? 200 : 200}
          value={String(r[key] ?? "")}
          onChange={(e) => set(key, e.target.value || null)}
        />
      )}
    </Field>
  );
  const branch = (key: "fo" | "wireless", title: string) => {
    const b = r[key] || {},
      service = visit.site?.maintenance_profile?.[key];
    const enabled =
      key === "fo"
        ? r.backbone_mode !== "wireless_only"
        : r.backbone_mode !== "fo_only";
    const update = <K extends keyof Backbone>(field: K, value: Backbone[K]) =>
      set(key, { ...b, [field]: value, source: "manual" });
    const number = (
      field: keyof Backbone,
      label: string,
      min = 0,
      max?: number,
    ) => (
      <Field label={label}>
        <input
          type="number"
          inputMode="decimal"
          step="any"
          min={min}
          max={max}
          value={(b[field] as number) ?? ""}
          onChange={(e) =>
            update(field, e.target.value === "" ? null : Number(e.target.value))
          }
        />
      </Field>
    );
    return (
      <Card title={title} key={key}>
        {!enabled ? (
          <p className="muted">
            Tidak termasuk koneksi yang dipilih. Data tersimpan tetap
            dipertahankan dalam draf; payload mengikuti pilihan backbone.
          </p>
        ) : (
          <>
            <p className="service">
              SLA ↓ {service?.download_mbps ?? "Belum diatur"} / ↑{" "}
              {service?.upload_mbps ?? "Belum diatur"} Mbps
            </p>
            <Badge>
              {hasDraft
                ? "Kesesuaian dihitung server saat simpan"
                : b.conformity === "conforming"
                  ? "Sesuai"
                  : b.conformity === "not_conforming"
                    ? "Tidak sesuai"
                    : "Belum diperiksa"}
            </Badge>
            <div className="field-grid">
              {number("download_mbps", "Download (Mbps)")}
              {number("upload_mbps", "Upload (Mbps)")}
            </div>
            {key === "wireless" && (
              <>
                {number("signal_dbm", "Signal strength (dBm)", -150, 0)}
                <Field label="Hasil link test radio">
                  <textarea
                    value={b.link_test_radio || ""}
                    maxLength={5000}
                    onChange={(e) =>
                      update("link_test_radio", e.target.value || null)
                    }
                  />
                </Field>
              </>
            )}
            <Field label="Keterangan">
              <textarea
                value={b.notes || ""}
                maxLength={5000}
                rows={3}
                onChange={(e) => update("notes", e.target.value || null)}
              />
            </Field>
            <details>
              <summary>Field Nusanet / hasil format lama</summary>
              <div className="field-grid">
                {number("agreement_mbps", "Service Agreement (Mbps)")}
                {number("speedtest_mbps", "Speedtest format lama (Mbps)")}
                {key === "wireless" && (
                  <>
                    {number("tx_mbps", "TX rate (Mbps)")}
                    {number("rx_mbps", "RX rate (Mbps)")}
                    {number("ccq_percent", "CCQ / Link test (%)", 0, 100)}
                  </>
                )}
              </div>
              <p className="muted">
                Field lama tetap disimpan. Pengukuran ini input manual, bukan
                hasil Wi-Fi native.
              </p>
            </details>
          </>
        )}
      </Card>
    );
  };
  const checks = [
    [
      "router_connector",
      "Koneksi LAN Router",
      [
        ["normal", "Normal"],
        ["abnormal", "Tidak normal"],
        ["not_applicable", "Tidak berlaku"],
      ],
    ],
    [
      "switch_connector",
      "Koneksi LAN Switch",
      [
        ["normal", "Normal"],
        ["abnormal", "Tidak normal"],
        ["not_applicable", "Tidak berlaku"],
      ],
    ],
    [
      "signal_test",
      "Signal Test",
      [
        ["good", "Baik"],
        ["poor", "Buruk"],
        ["not_applicable", "Tidak berlaku"],
      ],
    ],
    [
      "blank_spot",
      "Blank Spot Area",
      [
        ["false", "Tidak ada"],
        ["true", "Ada"],
      ],
    ],
    [
      "hotspot",
      "Hotspot",
      [
        ["true", "Berfungsi"],
        ["false", "Tidak berfungsi"],
      ],
    ],
  ] as const;
  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">TEMPLATE NUSANET</p>
          <h2>Laporan Utama</h2>
        </div>
        <Badge tone={hasDraft ? "warning" : "neutral"}>
          {hasDraft ? "Draf lokal" : "Data server"}
        </Badge>
      </div>
      {!editable && (
        <Message>
          Mode baca. Mulai kunjungan dengan check-in atau gunakan penugasan
          milik Anda yang masih dapat diedit.
        </Message>
      )}
      <fieldset className="form-body" disabled={!editable || busy}>
        <Card title="Informasi pelanggan">
          <p className="muted">
            {visit.site?.customer_name || visit.site?.name}
          </p>
          {text("pic_name", "Nama PIC")}
          {text("pic_contact", "Kontak PIC")}
          <Field label="Koneksi backbone">
            <select
              value={r.backbone_mode || ""}
              onChange={(e) =>
                set(
                  "backbone_mode",
                  (e.target.value as Report["backbone_mode"]) || null,
                )
              }
            >
              <option value="">Belum dipilih</option>
              {[
                ["fo_only", "FO saja"],
                ["wireless_only", "Wireless saja"],
                ["both", "FO + wireless"],
                ["failover", "FO + wireless / failover"],
                ["bonding", "FO + wireless / bonding"],
              ].map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </Card>
        {branch("fo", "Backbone Fiber Optic")}
        {branch("wireless", "Wireless Backbone")}
        <Card title="Local Area Network">
          {checks.map(([key, label, choices], i) => {
            const noteKey = (key + "_notes") as keyof Report;
            return (
              <article className="inspection-item" key={key}>
                <h3>
                  {String.fromCharCode(97 + i)}. {label}
                </h3>
                <Field label="Status">
                  <select
                    value={
                      r[key] === null || r[key] === undefined
                        ? ""
                        : String(r[key])
                    }
                    onChange={(e) =>
                      set(
                        key,
                        key === "blank_spot" || key === "hotspot"
                          ? e.target.value === ""
                            ? null
                            : e.target.value === "true"
                          : e.target.value || null,
                      )
                    }
                  >
                    <option value="">Belum diperiksa</option>
                    {choices.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                {text(noteKey, "Keterangan", true)}
              </article>
            );
          })}
          {r.lan_notes && (
            <p className="muted">Catatan LAN lama: {r.lan_notes}</p>
          )}
        </Card>
        <Card title="Hasil pekerjaan">
          {text("summary", "Ringkasan / hasil pemeriksaan", true)}
          <Field label="Hasil pekerjaan">
            <select
              value={r.work_status || ""}
              onChange={(e) =>
                set(
                  "work_status",
                  (e.target.value as Report["work_status"]) || null,
                )
              }
            >
              <option value="">Belum diperiksa</option>
              <option value="completed">Selesai</option>
              <option value="pending">Pending / tindak lanjut</option>
            </select>
          </Field>
          {text("pending_reason", "Alasan pekerjaan pending", true)}
          {text("customer_feedback", "Feedback pelanggan", true)}
          {text("solution", "Solusi / tindak lanjut", true)}
          {text(
            "pic_exception_reason",
            "Alasan pengecualian tanda tangan PIC",
            true,
          )}
          <p className="muted">
            Persetujuan dan tanda tangan digital PIC belum tersedia.
          </p>
        </Card>
        <button className="primary wide" disabled={!hasDraft || busy}>
          {busy ? "Menyimpan…" : "Simpan laporan ke server"}
        </button>
      </fieldset>
      <p className="muted small">
        Draf disimpan lokal saat Anda mengisi. Simpan ke server memerlukan
        koneksi; tidak ada pengiriman otomatis. Validasi submit tetap mengikuti
        backend existing.
      </p>
    </form>
  );
}
