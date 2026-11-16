import type { Floor, Item, Point, Report, Visit } from "./types";
export const statusLabels: Record<string, string> = {
  assigned: "Belum Dikerjakan",
  in_progress: "Dalam Proses",
  submitted: "Perlu Review",
  revision_requested: "Perlu Revisi",
  approved: "Disetujui supervisor",
};
export function editable(v: Visit, userId: string) {
  return (
    v.technician_id === userId &&
    ["in_progress", "revision_requested"].includes(v.status)
  );
}
export function pointEvidence(p: Point) {
  const item = p.item,
    runs = (item?.speedtests || [])
      .slice()
      .sort(
        (a, b) =>
          new Date(b.finished_at || b.created_at).getTime() -
          new Date(a.finished_at || a.created_at).getTime(),
      ),
    run = runs[0];
  const accepted =
    run?.status === "completed" &&
    run.context?.transport === "direct_https" &&
    run.context.network === "hotel_wifi" &&
    run.context.wifi_confirmed === true &&
    ["download_mbps", "upload_mbps", "ping_ms"].every((k) =>
      Number.isFinite(run.metrics?.[k as keyof typeof run.metrics]),
    );
  const failed = run?.status === "failed" && !!run.error?.trim();
  const problem = item?.result?.outcome === "fail" || failed;
  const done =
    !!item &&
    ["pass", "fail"].includes(item.result?.outcome || "") &&
    !!(accepted || failed) &&
    item.photos.length > 0;
  return {
    done,
    problem,
    run,
    label: problem
      ? "Bermasalah"
      : done
        ? "Baik"
        : item?.result?.outcome
          ? "Perlu Perhatian"
          : "Belum Diperiksa",
  };
}
export function samplingFloors(items: Item[] = []): Floor[] {
  const floors: Floor[] = [];
  for (const item of items.filter((i) => i.device.device_type === "ap")) {
    const name = item.floor || "Belum dicatat";
    let floor = floors.find((f) => f.name === name);
    if (!floor) {
      floor = { id: name, name, points: [] };
      floors.push(floor);
    }
    floor.points.push({
      id: item.id,
      name: item.point || item.device.name,
      item,
    });
  }
  for (const floor of floors)
    while (floor.points.length < 4)
      floor.points.push({
        id: `target:${floor.id}:${floor.points.length}`,
        name: `Titik ${floor.points.length + 1} · belum ditentukan`,
      });
  return floors;
}
export function progress(v: Visit) {
  const points = samplingFloors(v.devices).flatMap((f) => f.points);
  return {
    total: points.length,
    done: points.filter((p) => pointEvidence(p).done).length,
  };
}
export function reportForSave(r: Report): Report {
  const report = structuredClone(r);
  report.form_version = r.form_version || 2;
  if (report.backbone_mode === "fo_only") report.wireless = null;
  if (report.backbone_mode === "wireless_only") report.fo = null;
  return report;
}
export function when(value?: string) {
  return value
    ? new Date(value).toLocaleString("id-ID", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Belum tersedia";
}
export function period(value: string) {
  return new Date(value + "T00:00:00").toLocaleDateString("id-ID", {
    month: "long",
    year: "numeric",
  });
}
