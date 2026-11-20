import type { SamplingCoverage } from "../types";
import { Card } from "./ui";

const photoLabels: Record<string, string> = {
  ap: "Access Point",
  device: "Perangkat",
  area: "Area sampling",
  finding: "Temuan",
  router: "Router",
  switch: "Switch",
  rack: "Rack",
  backbone: "Backbone",
  cable: "Kabel",
};

export function SamplingCoveragePanel({
  coverage,
  cached,
}: {
  coverage: SamplingCoverage;
  cached: boolean;
}) {
  return (
    <Card title="Cakupan sampling kunjungan">
      <p>
        {cached
          ? "Snapshot cache perangkat · periksa pembaruan saat online."
          : "Snapshot tersimpan di server."}
      </p>
      <p>
        Periode {coverage.period}. Penambahan lokasi lapangan dicatat pada
        kunjungan ini. Lengkapi review PIC sebelum mengirim laporan.
      </p>
      {coverage.floors.map((floor) => (
        <details key={floor.id}>
          <summary>
            {floor.name} · {floor.points.length} area · target{" "}
            {floor.target_count}
          </summary>
          <ul>
            {floor.points.map((point) => (
              <li key={point.id}>
                {point.name} ·
                Belum Diperiksa
                {point.location && <p>{point.location}</p>}
              </li>
            ))}
          </ul>
        </details>
      ))}
      <p>
        Foto wajib tiap area:{" "}
        {coverage.photo_policy.sampling_categories
          .map((category) => photoLabels[category] || category)
          .join(", ") || "Tidak diwajibkan"}
        .
      </p>
      <p>
        Foto wajib infrastruktur:{" "}
        {coverage.photo_policy.infrastructure_categories
          .map((category) => photoLabels[category] || category)
          .join(", ") || "Tidak diwajibkan"}
        .
      </p>
      <p>
        Hasil AP pada laporan existing belum menjadi hasil tiap sesi dalam
        cakupan ini.
      </p>
    </Card>
  );
}
