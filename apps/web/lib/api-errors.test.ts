import assert from "node:assert/strict";
import test from "node:test";

import { apiErrorMessage } from "./api-errors.ts";

test("diferencia errores de autenticacion y API", () => {
  assert.equal(apiErrorMessage(401), "Debes iniciar sesion para continuar.");
  assert.match(apiErrorMessage(404), /endpoint de la API/);
  assert.match(apiErrorMessage(422), /datos enviados no son validos/);
  assert.match(apiErrorMessage(500), /error interno/);
});

test("mantiene detalles utiles para otros estados", () => {
  assert.equal(apiErrorMessage(403, "Acceso denegado"), "Acceso denegado");
});
