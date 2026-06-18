from contextlib import contextmanager
from pathlib import Path
import sys
import unittest

from pydantic import ValidationError

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


class PersonalWorkspaceFakeConnection:
    row_factory = None
    workspaces: dict[str, dict] = {}
    notes: dict[str, dict] = {}
    post_its: dict[str, dict] = {}
    next_note_id = 1

    def execute(self, sql, params=None):
        query = str(sql)
        params = params or {}
        if "SELECT count(*)::int AS workspace_count" in query:
            return FakeResult([{"workspace_count": len(self.workspaces)}])
        if "INSERT INTO study_workspaces" in query:
            row = {
                "id": WORKSPACE_ID,
                "user_id": USER_ID,
                "name": params["name"],
                "description": params["description"],
                "source_filters": params["source_filters"].obj,
                "settings": params["settings"].obj,
                "created_at": None,
                "updated_at": None,
            }
            self.workspaces[WORKSPACE_ID] = row
            return FakeResult([row])
        if "FROM study_workspaces sw" in query:
            return FakeResult(list(self.workspaces.values()))
        if "FROM study_workspaces" in query:
            return FakeResult([self.workspaces[params["workspace_id"]]] if params.get("workspace_id") in self.workspaces else [])
        if "INSERT INTO study_notes" in query:
            note_id = f"note-{self.next_note_id}"
            self.__class__.next_note_id += 1
            if isinstance(params, tuple):
                workspace_id, user_id, content, position = params
                title = "Mi pensamiento"
                selected_text = None
            else:
                workspace_id = params.get("workspace_id") or WORKSPACE_ID
                user_id = params.get("user_id") or USER_ID
                title = params.get("title")
                content = params.get("content")
                selected_text = params.get("selected_text")
                position = params.get("position")
            row = {
                "id": note_id,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "document_id": None,
                "chunk_id": None,
                "title": title,
                "content": content,
                "selected_text": selected_text,
                "selection_range": {},
                "scripture_refs": [],
                "color": "yellow",
                "position": position.obj if hasattr(position, "obj") else {},
                "created_at": None,
                "updated_at": None,
                "deleted_at": None,
            }
            self.notes[note_id] = row
            return FakeResult([row])
        if "FROM study_notes" in query:
            rows = [
                row
                for row in self.notes.values()
                if row["workspace_id"] == params.get("workspace_id")
                and row["user_id"] == params.get("user_id")
                and row.get("deleted_at") is None
                and (not params.get("block_id") or row["id"] == params.get("block_id"))
            ]
            return FakeResult(rows)
        if "UPDATE study_notes" in query:
            row = self.notes[params["block_id"]]
            if "deleted_at = now()" in query:
                row["deleted_at"] = "deleted"
                return FakeResult([])
            row["title"] = params["title"]
            row["content"] = params["content"]
            row["selected_text"] = params["selected_text"]
            row["position"] = params["position"].obj
            return FakeResult([row])
        if "FROM post_its" in query:
            return FakeResult([])
        return FakeResult([])

    def commit(self):
        return None


@contextmanager
def personal_workspace_get_conn():
    yield PersonalWorkspaceFakeConnection()


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

    def test_workspace_payload_rejects_empty_name(self):
        with self.assertRaises(ValidationError):
            study.WorkspacePayload(name="")


class PersonalWorkspaceRoutesTest(unittest.TestCase):
    def setUp(self):
        self.original_get_conn = study.get_conn
        study.get_conn = personal_workspace_get_conn
        PersonalWorkspaceFakeConnection.workspaces = {}
        PersonalWorkspaceFakeConnection.notes = {}
        PersonalWorkspaceFakeConnection.post_its = {}
        PersonalWorkspaceFakeConnection.next_note_id = 1

    def tearDown(self):
        study.get_conn = self.original_get_conn

    def test_create_list_and_read_personal_workspace(self):
        response = study.create_workspace(
            payload=study.WorkspacePayload(
                name="Los nombres en Helaman 5:6",
                title="Los nombres en Helaman 5:6",
                scriptureReference="Helaman 5:6",
                personalThought="Recordar convenios familiares.",
                topic="Convenios",
            ),
            user_id=USER_ID,
        )

        self.assertEqual(response["title"], "Los nombres en Helaman 5:6")
        self.assertEqual(response["scriptureReference"], "Helaman 5:6")

        listed = study.list_workspaces(user_id=USER_ID)
        self.assertEqual(listed["items"][0]["id"], WORKSPACE_ID)

        detail = study.get_workspace(workspace_id=WORKSPACE_ID, user_id=USER_ID)
        self.assertEqual(detail["blocks"][0]["type"], "personal_note")

    def test_create_update_and_delete_workspace_block(self):
        study.create_workspace(payload=study.WorkspacePayload(name="Estudio", title="Estudio"), user_id=USER_ID)

        block = study.create_block(
            workspace_id=WORKSPACE_ID,
            payload=study.BlockPayload(type="reflection", title="Reflexion", content="Primera idea"),
            user_id=USER_ID,
        )
        self.assertEqual(block["type"], "reflection")

        updated = study.update_block(
            workspace_id=WORKSPACE_ID,
            block_id=block["id"],
            payload=study.BlockUpdatePayload(title="Reflexion editada", content="Idea editada"),
            user_id=USER_ID,
        )
        self.assertEqual(updated["title"], "Reflexion editada")
        self.assertEqual(updated["content"], "Idea editada")

        deleted = study.delete_block(workspace_id=WORKSPACE_ID, block_id=block["id"], user_id=USER_ID)
        self.assertTrue(deleted["deleted"])


if __name__ == "__main__":
    unittest.main()
