import assert from "node:assert/strict";
import test from "node:test";

import { apiErrorMessage, studyWorkspaceAiErrorMessage, studyWorkspaceCreateErrorMessage } from "./api-errors.ts";

test("diferencia errores de autenticacion y API", () => {
  assert.equal(apiErrorMessage(401), "Debes iniciar sesion para continuar.");
  assert.match(apiErrorMessage(404), /endpoint de la API/);
  assert.match(apiErrorMessage(422), /datos enviados no son validos/);
  assert.match(apiErrorMessage(500), /error interno/);
});

test("mantiene detalles utiles para otros estados", () => {
  assert.equal(apiErrorMessage(403, "Acceso denegado"), "Acceso denegado");
});

test("usa mensajes especificos al crear estudios personales", () => {
  assert.equal(studyWorkspaceCreateErrorMessage(401), "Debes iniciar sesion para crear estudios.");
  assert.equal(studyWorkspaceCreateErrorMessage(404), "El endpoint de estudios no esta disponible en la API desplegada.");
  assert.equal(studyWorkspaceCreateErrorMessage(422), "Revisa los campos del estudio.");
  assert.equal(studyWorkspaceCreateErrorMessage(500), "La API tuvo un error al crear el estudio.");
});

test("usa mensajes especificos para sugerencias de IA del estudio", () => {
  assert.equal(studyWorkspaceAiErrorMessage(401), "Debes iniciar sesion para usar la IA del estudio.");
  assert.equal(studyWorkspaceAiErrorMessage(404), "El endpoint de IA de estudios no esta disponible en la API desplegada.");
  assert.equal(studyWorkspaceAiErrorMessage(422), "Revisa los campos del pedido de IA.");
  assert.equal(studyWorkspaceAiErrorMessage(502), "La IA respondio con un formato inesperado.");
  assert.equal(studyWorkspaceAiErrorMessage(503), "La funcion de IA todavia no esta configurada en el servidor.");
  assert.equal(studyWorkspaceAiErrorMessage(504), "La IA tardo demasiado en responder. Intenta nuevamente mas tarde.");
});
