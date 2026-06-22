import assert from "node:assert/strict";
import test from "node:test";

import { isSuggestedReference, mapWorkspaceAiTypeToBlockType, sourceStatusLabel } from "./study-ai.ts";

test("mapea sugerencias de IA a tipos de bloque compatibles", () => {
  assert.equal(mapWorkspaceAiTypeToBlockType("doctrinal_analysis"), "doctrinal_analysis");
  assert.equal(mapWorkspaceAiTypeToBlockType("quote"), "quote");
  assert.equal(mapWorkspaceAiTypeToBlockType("manual_reference"), "quote");
  assert.equal(mapWorkspaceAiTypeToBlockType("reflection_question"), "reflection");
  assert.equal(mapWorkspaceAiTypeToBlockType("powerful_phrase"), "post_it");
  assert.equal(mapWorkspaceAiTypeToBlockType("scripture_connection"), "scripture");
});

test("marca referencias sugeridas sin tratarlas como citas verificadas", () => {
  assert.equal(sourceStatusLabel("suggested"), "Referencia sugerida");
  assert.equal(isSuggestedReference("suggested"), true);
  assert.equal(isSuggestedReference("local"), false);
});
