import { ConfirmDialog } from "./components/ConfirmDialog";
import { ContactProfile } from "./components/ContactProfile";
import { useEffect, useState } from "react";
import { App as NativeApp } from "@capacitor/app";
import { Capacitor } from "@capacitor/core";
import { Network } from "@capacitor/network";
import {
  ArrowRight,
  CalendarDays,
  CheckCheck,
  RefreshCw,
  Wifi,
} from "lucide-react";
import type { Hotel, User, Visit } from "./types";
import type { Route } from "./components/ui";
import {
  Badge,
  BottomNav,
  Card,
  Empty,
  Header,
  Message,
} from "./components/ui";
import { ApiClient } from "./services/api";
import { accountScope, store } from "./services/storage";
import { period, statusLabels } from "./domain";
import { Login } from "./pages/Login";
import { SyncStatus } from "./components/SyncStatus";
import { VisitWorkspace } from "./pages/VisitWorkspace";
function useConnection() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    const native = Capacitor.isNativePlatform();
    const listener = native
      ? Network.addListener("networkStatusChange", (s) =>
          setOnline(s.connected),
        )
      : null;
    if (native)
      void Network.getStatus()
        .then((s) => setOnline(s.connected))
        .catch(() => {});
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
      void listener?.then((h) => h.remove());
    };
  }, []);
  return online;
}
export default function App() {
  const online = useConnection();
  const [session, setSession] = useState<{ api: ApiClient; user: User } | null>(
      null,
    ),
    [route, setRoute] = useState<Route>("home"),
    [selected, setSelected] = useState<string | null>(null),
    [message, setMessage] = useState(""),
    [visits, setVisits] = useState<Visit[]>([]),
    [hotels, setHotels] = useState<Hotel[]>([]),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [revision, setRevision] = useState(0),
    [cached, setCached] = useState(false),
    [loggingOut, setLoggingOut] = useState(false),
    [confirmLogout, setConfirmLogout] = useState(false);
  useEffect(() => {
    if (!session) return;
    let active = true;
    const scope = accountScope(session.api.origin, session.user.id);
    setLoading(true);
    setError("");
    void (async () => {
      try {
        const [rows, sites] = await Promise.all([
          session.api.visits(),
          session.api.hotels(),
        ]);
        if (!active) return;
        setVisits(rows.filter((v) => v.technician_id === session.user.id));
        setHotels(sites);
        setCached(false);
        try {
          await store.put(scope + "schedule", {
            visits: rows.filter((v) => v.technician_id === session.user.id),
            hotels: sites,
          });
        } catch (err) {
          if (active) setError((err as Error).message);
        }
      } catch (err) {
        if (!active) return;
        setError((err as Error).message);
        try {
          const saved = await store.get<{ visits: Visit[]; hotels: Hotel[] }>(
            scope + "schedule",
          );
          if (active && saved) {
            setVisits(saved.visits);
            setHotels(saved.hotels);
            setCached(true);
          }
        } catch (storageError) {
          if (active) setError((storageError as Error).message);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [session, revision]);
  const back = () =>
    setRoute(
      route === "point"
        ? "floors"
        : ["report", "floors", "review"].includes(route) && selected
          ? "hotel"
          : route === "hotel"
            ? "schedule"
            : "home",
    );
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;
    const listener = NativeApp.addListener("backButton", () =>
      setRoute(
        route === "point"
          ? "floors"
          : ["report", "floors", "review"].includes(route) && selected
            ? "hotel"
            : route === "hotel"
              ? "schedule"
              : "home",
      ),
    );
    return () => {
      void listener.then((h) => h.remove());
    };
  }, [route, selected]);
  useEffect(() => {
    document.getElementById("main-content")?.focus();
    document.getElementById("main-content")?.scrollTo(0, 0);
    window.scrollTo(0, 0);
  }, [route, selected]);
  if (!session)
    return (
      <Login
        online={online}
        message={message}
        onLogin={(api, user) => {
          api.onExpired(() => {
            api.setToken(null);
            setSession(null);
            setVisits([]);
            setHotels([]);
            setSelected(null);
            setRoute("home");
            setMessage(
              "Sesi berakhir. Draf lokal tetap tersimpan; silakan masuk kembali.",
            );
          });
          setSession({ api, user });
          setMessage("");
          setRoute("home");
        }}
      />
    );
  const { api, user } = session;
  const title = (
    {
      home: "Dashboard Teknisi",
      schedule: "Jadwal Maintenance",
      hotel: "Detail Hotel",
      report: "Laporan Utama",
      floors: "Network Test",
      point: "Detail Area",
      review: "Review Laporan",
      profile: "Profil Teknisi",
    } as Record<Route, string>
  )[route];
  const hotelName = (v: Visit) =>
    hotels.find((h) => h.id === v.hotel_id)?.name ||
    "Informasi hotel belum tersedia";
  const open = (v: Visit) => {
    setSelected(v.id);
    setRoute("hotel");
  };
  const jobs = visits
    .slice()
    .sort((a, b) => a.planned_date.localeCompare(b.planned_date));
  const jobCards = (
    <div className="stack">
      {jobs.map((v) => (
        <button className="job-card card" key={v.id} onClick={() => open(v)}>
          <div className="section-heading">
            <span className="job-icon">
              <Wifi />
            </span>
            <Badge
              tone={
                v.status === "approved"
                  ? "success"
                  : v.status === "assigned"
                    ? "neutral"
                    : "warning"
              }
            >
              {statusLabels[v.status]}
            </Badge>
          </div>
          <h3>{hotelName(v)}</h3>
          <p>
            <CalendarDays size={14} />
            {period(v.planned_date)}
          </p>
          <div className="job-bottom">
            <span>{v.planned_date}</span>
            <span>
              Buka maintenance <ArrowRight size={16} />
            </span>
          </div>
        </button>
      ))}
      {!jobs.length && !loading && (
        <Card>
          <Empty title="Belum ada penugasan">
            Jadwal maintenance akan tampil setelah supervisor menugaskan hotel
            kepada Anda.
          </Empty>
        </Card>
      )}
    </div>
  );
  const inWorkspace =
    ["hotel", "report", "floors", "point", "review"].includes(route) &&
    selected;
  return (
    <div className="app-shell">
      <Header
        title={title}
        subtitle={user.name}
        online={online}
        back={route !== "home" ? back : undefined}
      />
      <main id="main-content" tabIndex={-1} className="app-content">
        {inWorkspace ? (
          <VisitWorkspace
            key={selected}
            api={api}
            user={user}
            visitId={selected}
            route={route}
            go={setRoute}
            online={online}
            onVisit={(updated) =>
              setVisits((rows) =>
                rows.map((v) => (v.id === updated.id ? updated : v)),
              )
            }
          />
        ) : route === "profile" ? (
          <div className="stack">
            <Card title="Data teknisi">
              <div className="profile-avatar">{user.name.slice(0, 1)}</div>
              <h2>{user.name}</h2>
              <p className="muted">@{user.username} · Teknisi</p>
              <Badge tone="success">
                {user.active ? "Akun aktif" : "Akun tidak aktif"}
              </Badge>
            </Card>
            <ContactProfile
              api={api}
              scope={accountScope(api.origin, user.id)}
              online={online}
            />
            <Card title="Status sinkronisasi">
              <SyncStatus scope={accountScope(api.origin, user.id)} />
              <p className="muted">
                Laporan, hasil pengujian dan foto tersimpan ke server melalui
                tombol yang tersedia. Saat Review, draf yang masih menunggu akan
                dikirim sebelum tanda tangan PIC.
              </p>
              <p className="muted">
                Draf dipisahkan per server, akun, kunjungan dan titik. Tidak
                dihapus ketika logout.
              </p>
              <p>Status koneksi: {online ? "Online" : "Offline"}</p>
              <p>Versi aplikasi: 1.7.0</p>
              <p>
                Penugasan: {visits.length} · Lokasi: {hotels.length}
              </p>
            </Card>
            <button
              className="secondary wide"
              disabled={loggingOut}
              onClick={() => setConfirmLogout(true)}
            >
              {loggingOut ? "Keluar…" : "Logout"}
            </button>
          </div>
        ) : route === "review" ? (
          <Card>
            <Empty title="Pilih penugasan untuk review">
              Buka hotel dari jadwal untuk melihat ringkasan laporan dan
              sampling.
            </Empty>
            <button
              className="primary wide"
              onClick={() => setRoute("schedule")}
            >
              Pilih jadwal
            </button>
          </Card>
        ) : (
          <div className="stack">
            {route === "home" && (
              <>
                <section className="greeting">
                  <p className="eyebrow">SELAMAT BERTUGAS</p>
                  <h2>Halo, {user.name.split(" ")[0]}.</h2>
                  <p className="muted">
                    Pilih hotel dan lanjutkan pemeriksaan jaringan.
                  </p>
                </section>
                <div className="stats-grid">
                  <Card>
                    <CalendarDays />
                    <strong>{visits.length}</strong>
                    <span>Jumlah Penugasan</span>
                  </Card>
                  <Card>
                    <CheckCheck />
                    <strong>
                      {visits.filter((v) => v.maintenance_completed).length}
                    </strong>
                    <span>Jumlah Tugas Selesai</span>
                  </Card>
                </div>
                <Card title="Progress pekerjaan">
                  <div className="workflow-counts">
                    <span>
                      {visits.filter((v) => v.status === "in_progress").length}{" "}
                      dalam proses
                    </span>
                    <span>
                      {
                        visits.filter((v) =>
                          ["submitted", "revision_requested"].includes(
                            v.status,
                          ),
                        ).length
                      }{" "}
                      perlu review
                    </span>
                  </div>
                  <p className="muted">
                    Progress Network Test terlihat di detail penugasan.
                  </p>
                </Card>
              </>
            )}
            <div className="section-heading">
              <h2>
                {route === "home"
                  ? "Jadwal maintenance"
                  : "Hotel yang ditugaskan"}
              </h2>
              <button
                aria-label="Muat ulang jadwal"
                className="icon-button light"
                disabled={loading}
                onClick={() => setRevision((v) => v + 1)}
              >
                <RefreshCw size={18} />
              </button>
            </div>
            {cached && (
              <Message>
                Menampilkan jadwal tersimpan. Data server belum diperbarui.
              </Message>
            )}
            {error && <Message error>{error}</Message>}
            {loading && <p role="status">Memuat penugasan…</p>}
            {jobCards}
            <details className="sync-info">
              <summary>Status sinkronisasi</summary>
              <p>
                Jadwal dan hasil tersimpan dibaca dari server. Draf laporan,
                catatan dan foto disimpan lokal; tidak ada sinkronisasi
                otomatis.
              </p>
            </details>
          </div>
        )}
      </main>
      <ConfirmDialog
        open={confirmLogout}
        onCancel={() => setConfirmLogout(false)}
        onConfirm={async () => {
          setConfirmLogout(false);
          setLoggingOut(true);
          let feedback = "";
          try {
            await api.logout();
          } catch {
            feedback =
              "Logout lokal selesai. Server tidak dapat dihubungi untuk mencabut sesi; token mengikuti kedaluwarsa server.";
          } finally {
            api.setToken(null);
            setSession(null);
            setVisits([]);
            setHotels([]);
            setSelected(null);
            setRoute("home");
            setMessage(feedback);
            setLoggingOut(false);
          }
        }}
      />
      <BottomNav route={route} go={setRoute} />
    </div>
  );
}
