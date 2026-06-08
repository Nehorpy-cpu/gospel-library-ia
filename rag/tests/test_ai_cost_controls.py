import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from app.api import routes  # noqa: E402
    from app.schemas.chat import ChatRequest  # noqa: E402
    from app.schemas.search import IndexRequest  # noqa: E402
except ModuleNotFoundError as exc:
    routes = None
    ChatRequest = None
    IndexRequest = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class FakeEstimate:
    def as_dict(self):
        return {
            "documentsToIndex": 2,
            "chunksToEmbed": 5,
            "cachedChunks": 3,
            "estimatedTokens": 1200,
            "estimatedCostUsd": 0.000156,
        }


class FakeCostService:
    paused = False

    def estimate_indexing(self, db, *, limit=100, force=False):
        self.limit = limit
        self.force = force
        return FakeEstimate()

    def is_indexing_paused(self, db):
        return self.paused

    def indexing_state(self, db):
        return {"paused": self.paused, "reason": "openai_insufficient_quota"}


class FakeBM25Retriever:
    def search(self, db, query, filters, limit=5):
        return []


class FailingOrchestrator:
    async def answer(self, db, request):
        raise Exception("429 insufficient_quota")


class AiCostControlsTest(unittest.TestCase):
    def setUp(self):
        if IMPORT_ERROR:
            self.skipTest(f"RAG API dependencies are not installed: {IMPORT_ERROR}")
        self.original_cost_service = routes.AiCostService
        self.original_qdrant_points = routes._qdrant_points_count
        self.original_missing_openai = routes._missing_openai_api_key
        self.original_orchestrator = routes.RAGOrchestrator
        self.original_bm25 = routes.BM25Retriever

    def tearDown(self):
        routes.AiCostService = self.original_cost_service
        routes._qdrant_points_count = self.original_qdrant_points
        routes._missing_openai_api_key = self.original_missing_openai
        routes.RAGOrchestrator = self.original_orchestrator
        routes.BM25Retriever = self.original_bm25

    def test_indexing_estimate_returns_cost_projection_without_openai_call(self):
        routes.AiCostService = FakeCostService

        response = routes.indexing_estimate(limit=25, force=False, db=object())

        self.assertEqual(response["documentsToIndex"], 2)
        self.assertEqual(response["chunksToEmbed"], 5)
        self.assertEqual(response["cachedChunks"], 3)

    def test_indexing_pauses_when_runtime_state_is_paused(self):
        class PausedCostService(FakeCostService):
            paused = True

        routes.AiCostService = PausedCostService
        routes._missing_openai_api_key = lambda: False

        response = routes.index(IndexRequest(limit=10), db=object())

        self.assertEqual(response.status_code, 409)
        self.assertIn("indexing_paused", response.body.decode())

    def test_chat_quota_error_uses_textual_fallback(self):
        routes._qdrant_points_count = lambda: 10
        routes._missing_openai_api_key = lambda: False
        routes.RAGOrchestrator = FailingOrchestrator
        routes.BM25Retriever = FakeBM25Retriever

        response = asyncio.run(routes.chat(ChatRequest(message="fe en Cristo"), db=object()))

        self.assertFalse(response.grounded)
        self.assertTrue(any("OpenAI quota" in warning for warning in response.warnings))


if __name__ == "__main__":
    unittest.main()
