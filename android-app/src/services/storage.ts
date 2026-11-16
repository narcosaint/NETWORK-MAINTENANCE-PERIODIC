// Separate app database: never changes the web application's IndexedDB or production DB.
let opened: Promise<IDBDatabase> | undefined;
function database() {
  return (opened ??= new Promise<IDBDatabase>((resolve, reject) => {
    const r = indexedDB.open("hotel-maintenance-android-v1", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("records");
    r.onsuccess = () => {
      r.result.onversionchange = () => {
        r.result.close();
        opened = undefined;
      };
      resolve(r.result);
    };
    r.onerror = () => {
      opened = undefined;
      reject(new Error("Penyimpanan lokal tidak tersedia."));
    };
    r.onblocked = () => {
      opened = undefined;
      reject(
        new Error("Tutup tab aplikasi lain untuk membuka penyimpanan lokal."),
      );
    };
  }));
}
async function transaction<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest,
): Promise<T> {
  const db = await database();
  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction("records", mode);
      const request = run(tx.objectStore("records"));
      tx.oncomplete = () => resolve(request.result as T);
      tx.onerror = tx.onabort = () =>
        reject(
          new Error(
            "Gagal menyimpan/membaca draf lokal. Perubahan belum aman; jangan tutup aplikasi.",
          ),
        );
    } catch {
      reject(
        new Error(
          "Gagal menyimpan/membaca draf lokal. Perubahan belum aman; jangan tutup aplikasi.",
        ),
      );
    }
  });
}
export const store = {
  get: <T>(key: string) =>
    transaction<T | undefined>("readonly", (s) => s.get(key)),
  put: (key: string, value: unknown) =>
    transaction<void>("readwrite", (s) => s.put(value, key)),
  remove: (key: string) => transaction<void>("readwrite", (s) => s.delete(key)),
  async prefix<T>(prefix: string) {
    const rows = await transaction<IDBValidKey[]>("readonly", (s) => {
      const request = s.getAllKeys(
        IDBKeyRange.bound(prefix, prefix + "\uffff"),
      );
      return request;
    });
    return Promise.all(
      rows.map(async (key) => ({
        key: String(key),
        value: (await this.get<T>(String(key)))!,
      })),
    );
  },
};
export function accountScope(origin: string, userId: string) {
  return JSON.stringify([origin, userId]) + ":";
}
export function visitScope(scope: string, id: string) {
  return scope + "visit:" + id + ":";
}
// Queue survives screen changes; a returning screen waits for its own outstanding writes.
const queues = new Map<string, Promise<void>>();
export function enqueueLocal(scope: string, task: () => Promise<void>) {
  const next = (queues.get(scope) || Promise.resolve())
    .catch(() => {})
    .then(task);
  queues.set(scope, next);
  return next;
}
export function flushLocal(scope: string) {
  return queues.get(scope) || Promise.resolve();
}
export async function flushAccount(scope: string) {
  await Promise.all(
    Array.from(queues.entries())
      .filter(([key]) => key.startsWith(scope))
      .map(([, pending]) => pending),
  );
}
