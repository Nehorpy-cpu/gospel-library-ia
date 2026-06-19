import assert from "node:assert/strict";
import test from "node:test";

import { buildApiUrl, normalizeApiOrigin } from "./api-client.ts";

test("construye la URL canonica para crear estudios personales", () => {
  process.env.NEXT_PUBLIC_API_URL = "https://api.estudiopy.com";
  process.env.NEXT_PUBLIC_ENVIRONMENT = "production";

  const url = buildApiUrl("/study-workspaces");

  assert.equal(url, "https://api.estudiopy.com/api/study-workspaces");
  assert.equal(url.includes("http://api:8000"), false);
});

test("acepta configuraciones que terminan en /api sin duplicar el prefijo", () => {
  assert.equal(normalizeApiOrigin("https://api.estudiopy.com/api"), "https://api.estudiopy.com");
});
