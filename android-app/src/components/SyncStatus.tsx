import { useEffect, useState } from "react";
import { flushAccount, store } from "../services/storage";
import { Badge, Message } from "./ui";
export function SyncStatus({ scope }: { scope: string }) {
  const [count, setCount] = useState<number | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await flushAccount(scope);
        const rows = await store.prefix<unknown>(scope);
        const total = rows.reduce((n, row) => {
          if (row.key.endsWith(":report")) return n + 1;
          if (row.key.endsWith(":photos") && Array.isArray(row.value))
            return n + row.value.length;
          if (
            row.key.endsWith(":notes") &&
            row.value &&
            typeof row.value === "object"
          )
            return n + Object.keys(row.value).length;
          return n;
        }, 0);
        if (active) setCount(total);
      } catch (err) {
        if (active) setError((err as Error).message);
      }
    })();
    return () => {
      active = false;
    };
  }, [scope]);
  return (
    <>
      {error ? (
        <Message error>{error}</Message>
      ) : (
        <Badge tone={count ? "warning" : "neutral"}>
          {count === null
            ? "Memeriksa draf lokal…"
            : count
              ? `${count} perubahan lokal belum disinkronkan`
              : "Tidak ada draf lokal"}
        </Badge>
      )}
    </>
  );
}
