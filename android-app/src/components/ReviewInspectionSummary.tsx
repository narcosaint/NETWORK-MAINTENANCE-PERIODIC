import type { Backbone, Point, Report } from "../types";
import { pointEvidence } from "../domain";
import { Badge } from "./ui";
function backboneSummary(b?: Backbone | null) {
  const values = [
    b?.download_mbps,
    b?.upload_mbps,
    b?.speedtest_mbps,
    b?.signal_dbm,
    b?.tx_mbps,
    b?.rx_mbps,
    b?.ccq_percent,
  ];
  if (!values.some(Number.isFinite))
    return {
      label: "Belum diperiksa",
      tone: "neutral",
      detail: "Belum ada pengukuran tersimpan.",
    };
  const detail =
    [
      Number.isFinite(b?.download_mbps) ? `↓ ${b!.download_mbps} Mbps` : null,
      Number.isFinite(b?.upload_mbps) ? `↑ ${b!.upload_mbps} Mbps` : null,
      Number.isFinite(b?.speedtest_mbps)
        ? `Hasil lama ${b!.speedtest_mbps} Mbps`
        : null,
      Number.isFinite(b?.signal_dbm) ? `${b!.signal_dbm} dBm` : null,
    ]
      .filter(Boolean)
      .join(" · ") || "Pengukuran format lama tersimpan.";
  return {
    label:
      b?.conformity === "not_conforming"
        ? "Tidak sesuai"
        : b?.conformity === "conforming"
          ? "Sesuai"
          : "Pengukuran tersimpan",
    tone:
      b?.conformity === "not_conforming"
        ? "danger"
        : b?.conformity === "conforming"
          ? "success"
          : "neutral",
    detail,
  };
}
export function ReviewInspectionSummary({
  report,
  points,
}: {
  report: Report;
  points: Point[];
}) {
  const fields = [
    report.router_connector,
    report.switch_connector,
    report.signal_test,
    report.blank_spot,
    report.hotspot,
  ];
  const count = fields.filter((v) => v !== null && v !== undefined).length;
  const problem =
    report.router_connector === "abnormal" ||
    report.switch_connector === "abnormal" ||
    report.signal_test === "poor" ||
    report.blank_spot === true ||
    report.hotspot === false;
  const evidence = points.map(pointEvidence),
    done = evidence.filter((e) => e.done).length;
  const sampled = points.some(
    (p) => p.item?.result?.outcome || p.item?.speedtests?.length,
  );
  const entries = [
    { title: "Backbone Fiber Optic", ...backboneSummary(report.fo) },
    { title: "Wireless Backbone", ...backboneSummary(report.wireless) },
    {
      title: "Local Area Network",
      label: !count
        ? "Belum diperiksa"
        : problem
          ? "Perlu perhatian"
          : count === 5
            ? "Pemeriksaan tersimpan"
            : "Sebagian diperiksa",
      tone: !count
        ? "neutral"
        : problem
          ? "danger"
          : count === 5
            ? "success"
            : "warning",
      detail: `${count}/5 item LAN tersimpan.`,
    },
    {
      title: "Sampling Wi-Fi",
      label: !sampled
        ? "Belum diperiksa"
        : evidence.some((e) => e.problem)
          ? "Perlu perhatian"
          : done === points.length
            ? "Pemeriksaan lengkap"
            : "Sebagian diperiksa",
      tone: !sampled
        ? "neutral"
        : evidence.some((e) => e.problem)
          ? "danger"
          : done === points.length
            ? "success"
            : "warning",
      detail: points.length
        ? `${done}/${points.length} titik selesai.`
        : "Belum ada titik server.",
    },
  ];
  return (
    <section className="review-summary" aria-label="Ringkasan pemeriksaan">
      {entries.map((e) => (
        <article className="card" key={e.title}>
          <h3>{e.title}</h3>
          <Badge tone={e.tone}>{e.label}</Badge>
          <p>{e.detail}</p>
        </article>
      ))}
    </section>
  );
}
