import { expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
it("vendored worker sends only its short-lived ticket to exact selected transfer endpoints", () => {
  class Xhr {
    headers: Record<string, string> = {};
    open() {}
    send() {}
    setRequestHeader(key: string, value: string) {
      this.headers[key] = value;
    }
  }
  const context = {
    XMLHttpRequest: Xhr,
    addEventListener() {},
    URL,
    self: { location: { origin: "https://localhost" } },
  };
  runInNewContext(
    readFileSync(
      new URL(
        "../../backend/app/web/librespeed/speedtest_worker.js",
        import.meta.url,
      ),
      "utf8",
    ),
    context,
  );
  runInNewContext(
    'settings.hotel_transfer_token="ticket";settings.hotel_run_id="run-a";settings.hotel_endpoint_origin="https://measure.test";',
    context,
  );
  for (const [url, allowed] of [
    [
      "https://measure.test/network-speedtests/transfer/run-a/ping?cache=1",
      true,
    ],
    ["https://measure.test/network-speedtests/transfer/run-a/upload", true],
    ["https://measure.test/network-speedtests/transfer/run-a/download", true],
    ["https://evil.test/network-speedtests/transfer/run-a/ping", false],
    ["https://measure.test/network-speedtests/transfer/run-b/ping", false],
    [
      "https://measure.test/network-speedtests/transfer/run-a/ping/extra",
      false,
    ],
    ["https://measure.test/auth/login", false],
  ] as const) {
    const request = new Xhr();
    (request.open as (...args: unknown[]) => void)("GET", url);
    request.send();
    expect(request.headers).toEqual(
      allowed ? { "X-Speedtest-Token": "ticket" } : {},
    );
  }
});
