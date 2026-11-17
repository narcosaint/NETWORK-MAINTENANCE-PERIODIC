import { useEffect, useRef, useState } from "react";
import type { Point } from "../types";
import {
  wifiService,
  type RadioDraft,
  type WifiScanBatch,
} from "../services/wifi";
import { Card, Empty, Message } from "./ui";
import { when } from "../domain";

function ScanGraph({ scan }: { scan: WifiScanBatch }) {
  const min = scan.band === "2.4 GHz" ? 2400 : 5000,
    max = scan.band === "2.4 GHz" ? 2500 : 5900;
  const x = (frequency: number) => 20 + ((frequency - min) / (max - min)) * 460;
  return (
    <svg
      viewBox="0 0 500 180"
      role="img"
      aria-label={`RSSI ${scan.networks.length} jaringan ${scan.band}`}
      className="wifi-graph"
    >
      <line x1="20" y1="150" x2="480" y2="150" stroke="currentColor" />
      {[-100, -80, -60, -40].map((rssi) => (
        <g key={rssi}>
          <line
            x1="20"
            y1={150 - (rssi + 100) * 1.5}
            x2="480"
            y2={150 - (rssi + 100) * 1.5}
            stroke="currentColor"
            opacity="0.12"
          />
          <text x="0" y={150 - (rssi + 100) * 1.5} fontSize="10">
            {rssi}
          </text>
        </g>
      ))}
      {scan.networks.map((network, index) => {
        const center = x(network.frequencyMhz),
          width = (20 / (max - min)) * 460;
        const top =
          150 - Math.max(0, Math.min(80, network.rssiDbm + 100)) * 1.5;
        return (
          <path
            key={network.bssid + index}
            d={`M ${center - width / 2} 150 Q ${center} ${top - 20} ${center + width / 2} 150`}
            fill="none"
            stroke={["#0c7559", "#3777b5", "#b66b1a", "#884eaa"][index % 4]}
            opacity={network.cached ? 0.45 : 0.85}
          >
            <title>
              {network.ssid || "SSID tersembunyi"}: {network.rssiDbm} dBm,{" "}
              {network.frequencyMhz} MHz
            </title>
          </path>
        );
      })}
      <text x="20" y="173" fontSize="11">
        {min} MHz
      </text>
      <text x="420" y="173" fontSize="11">
        {max} MHz
      </text>
    </svg>
  );
}

export function NativeWifiPanel({
  mode,
  point,
  radio,
  capture,
  busy,
  setBusy,
}: {
  mode: "connection" | "scan";
  point: Point;
  radio?: RadioDraft;
  capture?: (value: RadioDraft) => Promise<void>;
  busy: boolean;
  setBusy: (value: boolean) => void;
}) {
  const [error, setError] = useState(""),
    [band, setBand] = useState<"2.4 GHz" | "5 GHz">("2.4 GHz");
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const read = async () => {
    if (busy || !capture) return;
    setBusy(true);
    setError("");
    try {
      const result =
        mode === "connection"
          ? await wifiService.connection()
          : await wifiService.scan(band);
      if (!mounted.current) return;
      if (!result.available) {
        setError(result.reason);
        return;
      }
      await capture(
        mode === "connection"
          ? { connection: result.data as NonNullable<RadioDraft["connection"]> }
          : { scan: result.data as WifiScanBatch },
      );
    } catch (error) {
      if (mounted.current) setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  };
  if (mode === "connection") {
    const connection = radio?.connection;
    const inventory = point.session?.device;
    const identified =
      !!connection?.bssid &&
      !!inventory?.mac_address &&
      connection.bssid.toLowerCase() === inventory.mac_address.toLowerCase();
    const fields: [string, string | number | null | undefined][] = [
      ["SSID", connection?.ssid],
      ["BSSID", connection?.bssid],
      ["Frequency (MHz)", connection?.frequencyMhz],
      ["Channel", connection?.channel],
      ["Band", connection?.band],
      ["RSSI (dBm)", connection?.rssiDbm],
      ["Link speed (Mbps)", connection?.linkSpeedMbps],
      ["IP Address", connection?.ipAddress],
      ["Gateway", connection?.gateway],
    ];
    return (
      <Card title="Connected Network">
        <p>{identified ? inventory?.name : "AP Belum Teridentifikasi"}</p>
        {connection && (
          <p className="muted">
            Pembacaan Android {when(connection.observedAt)} · snapshot
            pengukuran, bukan monitor koneksi langsung.
          </p>
        )}
        <dl className="network-grid">
          {fields.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value ?? "Belum tersedia"}</dd>
            </div>
          ))}
        </dl>
        {error && <Message error>{error}</Message>}
        <button
          className="secondary wide"
          disabled={busy || !capture}
          onClick={() => void read()}
        >
          {busy ? "Membaca Wi-Fi…" : "Baca koneksi Wi-Fi"}
        </button>
        <p className="muted">
          Izin lokasi presisi dan layanan lokasi diperlukan. Hasil tidak
          membuktikan trafik speedtest terikat ke Wi-Fi.
        </p>
      </Card>
    );
  }
  const scan = radio?.scan?.band === band ? radio.scan : undefined;
  const overlapping = scan?.networks.filter((n) =>
    scan.networks.some(
      (other) =>
        other.bssid !== n.bssid &&
        Math.abs(other.frequencyMhz - n.frequencyMhz) < 20,
    ),
  ).length;
  return (
    <Card title="Wi-Fi Analyzer">
      <div className="segmented" aria-label="Band Wi-Fi">
        {(["2.4 GHz", "5 GHz"] as const).map((value) => (
          <button
            key={value}
            aria-pressed={band === value}
            disabled={busy}
            onClick={() => setBand(value)}
          >
            {value}
          </button>
        ))}
      </div>
      {error && <Message error>{error}</Message>}
      {scan ? (
        <>
          <p>
            {scan.networks.length} jaringan ·{" "}
            {scan.cached ? "Memuat cache OS" : "Scan selesai"} ·{" "}
            {when(scan.observedAt)}
          </p>
          {scan.reason && <p>{scan.reason}</p>}
          <ScanGraph scan={scan} />
          <p className="muted">
            Kurva ilustrasi 20 MHz dari frekuensi/RSSI. {overlapping} jaringan
            berpusat pada kanal berdekatan (&lt;20 MHz); estimasi ini bukan
            interferensi terukur.
          </p>
          <ul className="wifi-networks">
            {scan.networks.map((network, index) => (
              <li key={network.bssid + index}>
                <strong>{network.ssid || "SSID tersembunyi"}</strong>
                <span>
                  {network.bssid} · {network.rssiDbm} dBm · Kanal{" "}
                  {network.channel ?? "—"}
                </span>
                <small>
                  {network.frequencyMhz} MHz ·{" "}
                  {network.cached ? "Cache · " : ""}
                  {when(network.observedAt)}
                </small>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <Empty title="Belum ada hasil scan">
          Hasil hanya berasal dari radio Android, tanpa simulasi.
        </Empty>
      )}
      <button
        className="secondary wide"
        disabled={busy || !capture}
        onClick={() => void read()}
      >
        {busy ? "Memindai…" : "Pindai Wi-Fi"}
      </button>
      <p className="muted">
        Hasil disimpan sebagai draf pada titik ini. Kirim melalui Simpan catatan
        ke server. Android dapat membatasi scan.
      </p>
    </Card>
  );
}
