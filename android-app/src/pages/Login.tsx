import { useState } from "react";
import { LockKeyhole } from "lucide-react";
import { Capacitor } from "@capacitor/core";
import {
  ApiClient,
  normalizeOrigin,
  DEFAULT_API_ORIGIN,
} from "../services/api";
import type { User } from "../types";
import { Field, Message } from "../components/ui";
export function Login({
  online,
  message,
  onLogin,
}: {
  online: boolean;
  message: string;
  onLogin: (api: ApiClient, user: User) => void;
}) {
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const server =
    import.meta.env.VITE_API_URL ||
    (Capacitor.isNativePlatform() ? DEFAULT_API_ORIGIN : "");
  return (
    <main className="login-page">
      <div className="login-brand">
        <img
          className="login-logo"
          src="/brand/nusa-maintenance-logo.png"
          alt="Nusa Maintenance"
          width="1500"
          height="470"
        />
      </div>
      <p className="eyebrow">PREVENTIVE MAINTENANCE</p>
      <h1>
        Siap merawat
        <br />
        network anda.
      </h1>
      <p className="login-intro">Workspace Teknisi Nusanet</p>
      <form
        className="card login-card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          let client: ApiClient | undefined;
          try {
            client = new ApiClient(normalizeOrigin(server));
            const user = await client.login(username.trim(), password);
            if (user.role !== "technician") {
              await client.logout();
              throw new Error(
                "Aplikasi ini untuk akun teknisi. Gunakan Web Dashboard untuk supervisor.",
              );
            }
            setPassword("");
            onLogin(client, user);
          } catch (err) {
            client?.setToken(null);
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="card-title">
          <h2>Masuk ke aplikasi</h2>
          <LockKeyhole size={18} />
        </div>
        <p className="connection dark">
          <i className={online ? "online" : "offline"} />
          {online ? "Online" : "Offline"}
        </p>
        {message && <Message error>{message}</Message>}
        <Field label="Username">
          <input
            autoComplete="username"
            value={username}
            maxLength={100}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={busy}
          />
        </Field>
        <Field label="Password">
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            maxLength={128}
            required
            disabled={busy}
          />
        </Field>
        {error && <Message error>{error}</Message>}
        <button className="primary wide" disabled={busy || !online}>
          {busy ? "Menghubungkan…" : "Masuk"}
        </button>
        <p className="muted small">
          Password dan token tidak disimpan di penyimpanan perangkat. Masuk
          kembali setelah aplikasi dimuat ulang.
        </p>
      </form>
      <p className="login-footer">MAINTENANCE + NETWORK DIAGNOSTICS</p>
    </main>
  );
}
