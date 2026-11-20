import { describe, expect, it } from "vitest";
import {
  editable,
  pointEvidence,
  reportForSave,
  samplingFloors,
  progress,
} from "../src/domain";
import { normalizeOrigin, ApiClient, ApiError } from "../src/services/api";
import { libreSpeedService } from "../src/services/librespeed";
import { wifiService } from "../src/services/native";
import {
  accountScope,
  visitScope,
  enqueueLocal,
  flushLocal,
} from "../src/services/storage";
import type { Item, Report, Visit, SamplingCoverage } from "../src/types";
import { vi, afterEach } from "vitest";
const item: Item = {
  id: "point1",
  device_id: "ap1",
  device: { id: "ap1", name: "AP asli", device_type: "ap" },
  floor: "2",
  point: "Koridor",
  result: { outcome: "pass" },
  photos: [{ id: "p", url: "/private", created_at: "2026-11-13" }],
  speedtests: [],
};
afterEach(() => vi.unstubAllGlobals());
describe("server coverage", () => {
  const coverage: SamplingCoverage = {
    id: "coverage",
    hotel_visit_id: "visit",
    period: "2026-11-01",
    completion_available: false,
    photo_policy: { sampling_categories: [], infrastructure_categories: [] },
    floors: [
      {
        id: "floor-snapshot",
        floor_id: "master-floor",
        name: "Snapshot lantai",
        target_count: 2,
        points: ["a", "b"].map((id) => ({
          id,
          sampling_point_id: "master-" + id,
          name: "Titik " + id,
          location: null,
          device: { id: "ap1", name: "AP sama", mac_address: null },
          status: "untested",
          version: 1,
        })),
      },
    ],
  };
  it("uses snapshot locations without copying AP evidence or padding the frozen scope", () => {
    const floors = samplingFloors([item], coverage);
    expect(floors[0].name).toBe("Snapshot lantai");
    expect(floors[0].points.map((p) => p.id)).toEqual(["a", "b"]);
    expect(
      floors[0].points.every(
        (p) => p.session && !p.item && !pointEvidence(p).done,
      ),
    ).toBe(true);
  });
  it("counts actual field areas without imposing a historical target", () => {
    const field = structuredClone(coverage);
    field.floors[0].target_count = 4;
    field.floors[0].points = field.floors[0].points.slice(0, 1);
    expect(progress({ sampling_coverage: field } as Visit)).toEqual({
      total: 1,
      done: 0,
    });
    expect(samplingFloors([], field)[0].points).toHaveLength(1);
  });
  it("accepts nullable coverage responses without weakening ordinary API validation", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ coverage_enabled: true })),
      )
      .mockResolvedValueOnce(new Response("null"))
      .mockResolvedValueOnce(new Response("null"));
    vi.stubGlobal("fetch", fetcher);
    const api = new ApiClient("/api");
    expect(await api.samplingCoverage("visit")).toBeNull();
    await expect(api.visit("visit")).rejects.toThrow(
      "Respons server tidak valid",
    );
  });
});
describe("physical sampling evidence", () => {
  it("pads to 2 without inventing server items or mutating the source", () => {
    const floors = samplingFloors([item]);
    expect(floors[0].points).toHaveLength(2);
    expect(floors[0].points.filter((p) => p.item)).toHaveLength(1);
    expect(item.point).toBe("Koridor");
    expect(samplingFloors([])).toEqual([]);
  });
  it("does not accept manual measurements or diagnostics as completed sampling", () => {
    expect(pointEvidence({ id: item.id, name: "Test", item }).done).toBe(false);
    expect(pointEvidence({ id: "local", name: "Local" }).done).toBe(false);
  });
  it("accepts actual zero results but requires context, outcome and photos", () => {
    const measured = {
      ...item,
      speedtests: [
        {
          id: "run",
          band: "band_24",
          status: "completed",
          created_at: "2026-11-13",
          context: {
            transport: "direct_https",
            network: "hotel_wifi",
            wifi_confirmed: true,
          },
          metrics: { download_mbps: 0, upload_mbps: 0, ping_ms: 0 },
        },
      ],
    };
    expect(
      pointEvidence({ id: item.id, name: "Test", item: measured }).done,
    ).toBe(true);
    expect(
      pointEvidence({
        id: item.id,
        name: "Test",
        item: { ...measured, photos: [] },
      }).done,
    ).toBe(false);
    measured.speedtests[0].context.transport = "diagnostic_tunnel_or_local";
    expect(
      pointEvidence({ id: item.id, name: "Test", item: measured }).done,
    ).toBe(false);
  });
  it("accepts failed testing only with a real reason and marks a finding", () => {
    const failed = {
      ...item,
      speedtests: [
        {
          id: "run",
          band: "band_24",
          status: "failed",
          error: "Tidak terhubung",
          created_at: "2026-11-13",
        },
      ],
    };
    expect(
      pointEvidence({ id: item.id, name: "Test", item: failed }),
    ).toMatchObject({ done: true, problem: true });
    failed.speedtests[0].error = " ";
    expect(
      pointEvidence({ id: item.id, name: "Test", item: failed }).done,
    ).toBe(false);
  });
});
describe("compatibility and storage", () => {
  it("preserves all legacy Nusanet fields and the draft while pruning inactive backbone in payload", () => {
    const r: Report = {
      form_version: 1,
      backbone_mode: "fo_only",
      fo: { speedtest_mbps: 0, agreement_mbps: 20 },
      wireless: { tx_mbps: 18, rx_mbps: 20, ccq_percent: 100, signal_dbm: -62 },
      lan_notes: "Lama",
      router_connector_notes: "Asli",
    };
    const saved = reportForSave(r);
    expect(saved.fo?.speedtest_mbps).toBe(0);
    expect(saved.form_version).toBe(1);
    expect(saved.lan_notes).toBe("Lama");
    expect(saved.wireless).toBeNull();
    expect(r.wireless?.ccq_percent).toBe(100);
  });
  it("limits changes to the assigned owner and editable states", () => {
    expect(
      editable({ technician_id: "a", status: "in_progress" } as Visit, "a"),
    ).toBe(true);
    expect(
      editable({ technician_id: "a", status: "approved" } as Visit, "a"),
    ).toBe(false);
    expect(
      editable({ technician_id: "b", status: "in_progress" } as Visit, "a"),
    ).toBe(false);
  });
  it("separates server, account and visit storage scopes", () => {
    expect(accountScope("https://a", "u")).not.toBe(
      accountScope("https://b", "u"),
    );
    expect(visitScope(accountScope("https://a", "u"), "v")).not.toBe(
      visitScope(accountScope("https://a", "x"), "v"),
    );
  });
  it("serializes writes across screen lifetimes and keeps errors visible", async () => {
    const order: number[] = [];
    const a = enqueueLocal("test", async () => {
      await Promise.resolve();
      order.push(1);
    });
    const b = enqueueLocal("test", async () => {
      order.push(2);
    });
    await flushLocal("test");
    await Promise.all([a, b]);
    expect(order).toEqual([1, 2]);
    await expect(
      enqueueLocal("fail", async () => {
        throw Error("Quota");
      }),
    ).rejects.toThrow("Quota");
    await expect(flushLocal("fail")).rejects.toThrow("Quota");
  });
});
describe("native interfaces", () => {
  it("cannot fabricate radio or speedtest results", async () => {
    expect(await wifiService.connection()).toMatchObject({ available: false });
    expect(await wifiService.scan("5 GHz")).toMatchObject({ available: false });
    expect(libreSpeedService.capability()).toMatchObject({ available: false });
  });
});
describe("API safety and contract", () => {
  it("requires a secure credential-free native origin", () => {
    expect(normalizeOrigin("https://hotel.example/", true)).toBe(
      "https://hotel.example",
    );
    for (const origin of [
      "http://maintenance.inisaja.id",
      "http://maintenance.inisaja.id:8000",
      "http://maintenance.inisaja.id.evil.example",
      "http://maintenance.inisaja.id/path",
      "http://user:pass@maintenance.inisaja.id",
      "http://sub.maintenance.inisaja.id",
      "http://hotel.example",
      "https://user:pass@hotel.example",
      "https://hotel.example/path",
      "https://hotel.example?token=x",
      "",
    ])
      expect(() => normalizeOrigin(origin, true)).toThrow();
    expect(normalizeOrigin("", false)).toBe("/api");
  });
  it("paginates all schedules and keeps auth in headers", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify(Array.from({ length: 100 }, (_, id) => ({ id }))),
        ),
      )
      .mockResolvedValueOnce(new Response("[]"));
    vi.stubGlobal("fetch", fetcher);
    const api = new ApiClient("/api");
    api.setToken("fixture-token");
    expect(await api.visits()).toHaveLength(100);
    expect(fetcher.mock.calls[1][0]).toBe(
      "/api/hotel-visits?limit=100&offset=100",
    );
    expect(fetcher.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer fixture-token",
    );
  });
  it("uses PUT and expected_version without losing legacy values", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetcher);
    const api = new ApiClient("/api");
    await api.saveReport("visit", 7, { fo: { speedtest_mbps: 0 } });
    expect(fetcher.mock.calls[0][1].method).toBe("PUT");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      expected_version: 7,
      report: { fo: { speedtest_mbps: 0 } },
    });
  });
  it("handles conflicts and expires auth on 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response("{}", { status: 409 }))
        .mockResolvedValueOnce(new Response("{}", { status: 401 })),
    );
    const expired = vi.fn(),
      api = new ApiClient("/api", expired);
    await expect(api.visit("x")).rejects.toMatchObject({ status: 409 });
    await expect(api.visit("x")).rejects.toBeInstanceOf(ApiError);
    expect(expired).toHaveBeenCalledOnce();
  });
});
