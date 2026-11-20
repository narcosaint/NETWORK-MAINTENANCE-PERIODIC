import type { SamplingNotes } from "../types";
import { Card } from "./ui";
export type ObservationConflict = {
  code: "sampling_notes_conflict";
  session_id: string;
  fields: (keyof SamplingNotes)[];
  current_notes: SamplingNotes;
  requested_notes: SamplingNotes;
  merged_notes: SamplingNotes;
  current_session_version: number;
  current_visit_version: number;
};
const labels = {
  condition: "Kondisi",
  notes: "Temuan dan Tindakan",
  findings: "Temuan lama",
  action: "Tindakan lama",
  recommendation: "Rekomendasi",
};
function display(key: keyof SamplingNotes, value: string) {
  if (key === "condition")
    return (
      (
        {
          good: "Baik",
          attention: "Perlu perhatian",
          problem: "Bermasalah",
          untested: "Belum diperiksa",
        } as Record<string, string>
      )[value] || value
    );
  return value || "Kosong";
}
export function ObservationConflictCard({
  conflict,
  name,
  busy,
  resolve,
}: {
  conflict: ObservationConflict;
  name: string;
  busy: boolean;
  resolve: (local: boolean) => void;
}) {
  return (
    <div id="area-conflict" tabIndex={-1}>
      <Card title={"Tinjau perubahan area " + name}>
        <p>
          Isian yang sama berubah di server dan perangkat. Pilih isian yang akan
          dipakai sebelum melanjutkan.
        </p>
        {conflict.fields.map((key) => (
          <div className="conflict-comparison" key={key}>
            <strong>{labels[key]}</strong>
            <p>Server: {display(key, conflict.current_notes[key])}</p>
            <p>Perangkat: {display(key, conflict.requested_notes[key])}</p>
          </div>
        ))}
        <button
          className="primary wide"
          disabled={busy}
          onClick={() => resolve(true)}
        >
          Gunakan isian perangkat setelah review
        </button>
        <button
          className="secondary wide"
          disabled={busy}
          onClick={() => resolve(false)}
        >
          Gunakan isian server
        </button>
      </Card>
    </div>
  );
}
