import { Capacitor, CapacitorHttp } from "@capacitor/core";
import type { CheckIn, Hotel, Report, User, Visit } from "../types";
export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
  ) {
    super(message);
  }
}
export function normalizeOrigin(
  value: string,
  native = Capacitor.isNativePlatform(),
): string {
  if (!value.trim() && !native) return "/api";
  let u: URL;
  try {
    u = new URL(value.trim());
  } catch {
    throw new Error("Isi alamat HTTPS server yang valid.");
  }
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(u.hostname);
  if (
    (u.protocol !== "https:" &&
      !(u.protocol === "http:" && local && !native)) ||
    u.username ||
    u.password ||
    u.search ||
    u.hash ||
    u.pathname !== "/"
  )
    throw new Error("Gunakan origin HTTPS tanpa path, credential atau query.");
  return u.origin;
}
export class ApiClient {
  private token: string | null = null;
  constructor(
    public readonly origin: string,
    private expired: () => void = () => {},
  ) {}
  onExpired(callback: () => void) {
    this.expired = callback;
  }
  setToken(token: string | null) {
    this.token = token;
  }
  async request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
    };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let status: number, data: unknown;
    try {
      if (Capacitor.isNativePlatform()) {
        const response = await CapacitorHttp.request({
          url: this.origin + path,
          method,
          headers,
          data: body,
          responseType: "json",
          connectTimeout: 15000,
          readTimeout: 20000,
          disableRedirects: true,
        });
        status = response.status;
        data = response.data;
      } else {
        const response = await fetch(this.origin + path, {
          method,
          headers,
          body: body === undefined ? undefined : JSON.stringify(body),
          cache: "no-store",
          credentials: "omit",
          redirect: "error",
          signal: AbortSignal.timeout(20000),
        });
        status = response.status;
        data =
          response.status === 204
            ? null
            : await response.json().catch(() => null);
      }
    } catch {
      throw new ApiError(
        "Server tidak dapat dihubungi. Periksa koneksi dan alamat server.",
      );
    }
    if (status === 401) {
      this.token = null;
      this.expired();
      throw new ApiError(
        "Sesi berakhir atau username/password tidak sesuai.",
        401,
      );
    }
    if (status < 200 || status >= 300) {
      const detail = (data as { detail?: unknown } | null)?.detail;
      const message =
        status === 409
          ? "Data server berubah / status tidak sesuai. Draf tetap tersimpan; muat ulang dan tinjau sebelum menyimpan ulang."
          : status === 403
            ? "Akun tidak memiliki izin untuk tindakan ini."
            : status === 429
              ? "Terlalu banyak percobaan. Tunggu sebentar."
              : typeof detail === "string"
                ? detail
                : Array.isArray(detail)
                  ? "Data belum valid. Periksa isian laporan."
                  : "Server gagal memproses permintaan.";
      throw new ApiError(message, status);
    }
    if (status !== 204 && (data === null || typeof data !== "object"))
      throw new ApiError(
        "Respons server tidak valid. Periksa konfigurasi API.",
      );
    return data as T;
  }
  async list<T>(path: string) {
    const result: T[] = [];
    for (let offset = 0; ; offset += 100) {
      const rows = await this.request<T[]>(
        `${path}?limit=100&offset=${offset}`,
      );
      if (!Array.isArray(rows))
        throw new ApiError("Daftar server tidak valid.");
      result.push(...rows);
      if (rows.length < 100) return result;
    }
  }
  async login(username: string, password: string) {
    const auth = await this.request<{ access_token: string }>(
      "/auth/login",
      "POST",
      { username, password },
    );
    if (!auth.access_token) throw new ApiError("Token server tidak tersedia.");
    this.token = auth.access_token;
    return this.request<User>("/auth/me");
  }
  visits() {
    return this.list<Visit>("/hotel-visits");
  }
  hotels() {
    return this.list<Hotel>("/hotels");
  }
  visit(id: string) {
    return this.request<Visit>("/hotel-visits/" + encodeURIComponent(id));
  }
  checkIn(id: string, data: CheckIn) {
    return this.request<Visit>(
      `/hotel-visits/${encodeURIComponent(id)}/check-in`,
      "POST",
      data,
    );
  }
  saveReport(id: string, version: number, report: Report) {
    return this.request<Visit>(
      `/hotel-visits/${encodeURIComponent(id)}/report`,
      "PUT",
      { expected_version: version, report },
    );
  }
  async logout() {
    try {
      await this.request("/auth/logout", "POST");
    } finally {
      this.token = null;
    }
  }
}
