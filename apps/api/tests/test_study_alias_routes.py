from contextlib import contextmanager
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import study

USER_ID = "00000000-0000-0000-0000-000000000001"
WORKSPACE_ID = "00000000-0000-0000-0000-000000000010"


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    row_factory = None

    def execute(self, sql, params=None):
      query = str(sql)
      if "SELECT count(*)::int AS workspace_count" in query:
          return FakeResult([{"workspace_count": 0}])
      if "INSERT INTO study_workspaces" in query:
          return FakeResult(
              [
                  {
                      "id": WORKSPACE_ID,
                      "user_id": USER_ID,
                      "name": params["name"],
                      "description": params["description"],
                      "source_filters": params["source_filters"].obj,
                      "settings": params["settings"].obj,
                      "created_at": None,
                      "updated_at": None,
                  }
              ]
          )
      if "information_schema.columns" in query:
          return FakeResult(
              [
                  ("id",),
                  ("source_id",),
                  ("title",),
                  ("canonical_url",),
                  ("author",),
                  ("language",),
                  ("text",),
                  ("raw_metadata",),
                  ("created_at",),
                  ("updated_at",),
              ]
          )
      if "FROM study_workspaces sw" in query:
          return FakeResult(
              [
                  {
                      "id": WORKSPACE_ID,
                      "user_id": USER_ID,
                      "name": "Fe en Jesucristo",
                      "description": "Alma 32",
                      "source_filters": {"language": "es"},
                      "settings": {"mainReference": "Alma 32", "language": "es", "referenceType": "scripture"},
                      "created_at": None,
                      "updated_at": None,
                  }
              ]
          )
      if "FROM study_workspaces" in query:
          return FakeResult(
              [
                  {
                      "id": WORKSPACE_ID,
                      "user_id": USER_ID,
                      "name": "Fe en Jesucristo",
                      "description": "Alma 32",
                      "source_filters": {"language": "es"},
                      "settings": {"mainReference": "Alma 32", "language": "es", "referenceType": "scripture"},
                      "created_at": None,
                      "updated_at": None,
                  }
              ]
          )
      if "FROM documents d" in query:
          return FakeResult(
              [
                  {
                      "id": "doc-1",
                      "title": "La fe en Jesucristo",
                      "author": "Autor real",
                      "source": "BYU Speeches",
                      "source_type": "byu_speeches_es",
                      "language": "es",
                      "canonical_url": "https://example.com/doc",
                      "source_url": "https://example.com/original",
                      "excerpt": "Alma ensena que la fe no es tener un conocimiento perfecto.",
                      "relevance_score": 2.0,
                  }
              ]
          )
      return FakeResult([])

    def commit(self):
        return None


@contextmanager
def fake_get_conn():
    yield FakeConnection()


class StudyAliasRoutesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = study.get_conn
        self.original_qdrant_points = study._qdrant_points_count
        study.get_conn = fake_get_conn
        study._qdrant_points_count = lambda: 0

    def tearDown(self):
        study.get_conn = self.original_get_conn
        study._qdrant_points_count = self.original_qdrant_points

    def test_study_workspaces_alias_lists_real_rows(self):
        response = study.alias_list_workspaces(user_id=USER_ID)

        self.assertEqual(response["items"][0]["id"], WORKSPACE_ID)
        self.assertEqual(response["items"][0]["name"], "Fe en Jesucristo")

    def test_related_alias_uses_textual_fallback_without_vectors(self):
        response = study.related_documents(workspace_id=WORKSPACE_ID, user_id=USER_ID)

        self.assertEqual(response["mode"], "textual_fallback")
        self.assertEqual(response["warning"], "Busqueda semantica no disponible todavia.")
        self.assertEqual(response["results"][0]["title"], "La fe en Jesucristo")
        self.assertEqual(response["results"][0]["sourceType"], "byu_speeches_es")

    def test_create_workspace_accepts_dict_row_factory_count(self):
        payload = study.WorkspacePayload(
            name="Fe en Jesucristo",
            description="Alma 32",
            sourceFilters={"language": "es"},
            settings={"mainReference": "Alma 32"},
        )

        response = study.create_workspace(payload=payload, user_id=USER_ID)

        self.assertEqual(response["id"], WORKSPACE_ID)
        self.assertEqual(response["name"], "Fe en Jesucristo")


if __name__ == "__main__":
    unittest.main()
