from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "normalize_existing_spanish_content.py"
SPEC = importlib.util.spec_from_file_location("normalize_existing_spanish_content", SCRIPT_PATH)
assert SPEC and SPEC.loader
normalization_script = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = normalization_script
SPEC.loader.exec_module(normalization_script)


TAG_COLUMNS = {
    "id": "uuid",
    "name": "text",
    "slug": "text",
    "normalized_name": "text",
    "language": "character varying",
}


class FakeCursor:
    def __init__(self, *, rows=None, row=None, rowcount=0):
        self._rows = rows or []
        self._row = row
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


class FakeDerivedNameConnection:
    def __init__(self, tag_rows):
        self.tag_rows = tag_rows
        self.executed_updates = []

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, query, params=None):
        if isinstance(query, str) and "information_schema.columns" in query:
            table = params[0]
            columns = TAG_COLUMNS if table == "tags" else {}
            return FakeCursor(
                rows=[
                    {"column_name": column_name, "data_type": data_type}
                    for column_name, data_type in columns.items()
                ]
            )
        if isinstance(params, tuple) and params[0] == "authors":
            return FakeCursor(row={"exists": False}, rows=[])
        if isinstance(params, tuple) and params[0] == "tags":
            return FakeCursor(row={"exists": True}, rows=[])
        if isinstance(params, dict) and "normalized_name" in params:
            self.executed_updates.append(("text", params))
            return FakeCursor(rowcount=1)
        if isinstance(params, dict) and "slug" in params:
            self.executed_updates.append(("slug", params))
            return FakeCursor(rowcount=1)
        if params is None:
            return FakeCursor(rows=self.tag_rows)
        raise AssertionError(f"Consulta inesperada: {query!r} {params!r}")


class SpanishContentNormalizationScriptTest(unittest.TestCase):
    def test_conflicting_tag_slug_is_skipped_without_merging_rows(self):
        rows = [
            {"id": "faith-tag", "name": "Faith", "slug": "faith", "normalized_name": "faith", "language": "en"},
            {"id": "fe-tag", "name": "Fe", "slug": "fe", "normalized_name": "fe", "language": "es"},
        ]

        updates, warnings = normalization_script.plan_tag_derived_updates(rows, TAG_COLUMNS)

        faith_update = next(update for update in updates if update.row_id == "faith-tag")
        self.assertEqual(faith_update.values["name"], "Fe")
        self.assertEqual(faith_update.values["normalized_name"], "fe")
        self.assertIsNone(faith_update.desired_slug)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].table, "tags")
        self.assertEqual(warnings[0].row_id, "faith-tag")
        self.assertEqual(warnings[0].current_slug, "faith")
        self.assertEqual(warnings[0].desired_slug, "fe")
        self.assertEqual(warnings[0].existing_id, "fe-tag")
        self.assertEqual(warnings[0].action, "skipped_slug_update")
        self.assertEqual({row["id"] for row in rows}, {"faith-tag", "fe-tag"})

    def test_dry_run_report_includes_slug_conflict(self):
        report = normalization_script.DerivedNameReport(
            warnings=[
                normalization_script.SlugConflict(
                    table="tags",
                    row_id="faith-tag",
                    current_slug="faith",
                    desired_slug="fe",
                    existing_id="fe-tag",
                )
            ]
        )
        output = io.StringIO()

        with redirect_stdout(output):
            normalization_script.print_report({}, report, apply=False)

        self.assertIn("Modo: dry-run", output.getvalue())
        self.assertIn("slug_conflict", output.getvalue())
        self.assertIn("action=skipped_slug_update", output.getvalue())

    def test_conflict_does_not_stop_other_safe_slug_updates(self):
        rows = [
            {"id": "faith-tag", "name": "Faith", "slug": "faith", "normalized_name": "faith", "language": "en"},
            {"id": "fe-tag", "name": "Fe", "slug": "fe", "normalized_name": "fe", "language": "es"},
            {"id": "hope-tag", "name": "Esperanza", "slug": "hope", "normalized_name": "hope", "language": "en"},
        ]

        updates, warnings = normalization_script.plan_tag_derived_updates(rows, TAG_COLUMNS)

        self.assertEqual(len(warnings), 1)
        hope_update = next(update for update in updates if update.row_id == "hope-tag")
        self.assertEqual(hope_update.desired_slug, "esperanza")

    def test_apply_skips_conflicting_slug_and_continues_with_safe_tag(self):
        rows = [
            {"id": "faith-tag", "name": "Faith", "slug": "faith", "normalized_name": "faith", "language": "en"},
            {"id": "fe-tag", "name": "Fe", "slug": "fe", "normalized_name": "fe", "language": "es"},
            {"id": "hope-tag", "name": "Esperanza", "slug": "hope", "normalized_name": "hope", "language": "en"},
        ]
        conn = FakeDerivedNameConnection(rows)

        report = normalization_script.maintain_derived_names(conn, apply=True)

        self.assertEqual(len(report.warnings), 1)
        self.assertEqual(report.warnings[0].row_id, "faith-tag")
        self.assertEqual(report.modified, 2)
        self.assertIn(("slug", {"id": "hope-tag", "slug": "esperanza"}), conn.executed_updates)
        self.assertNotIn(("slug", {"id": "faith-tag", "slug": "fe"}), conn.executed_updates)

    def test_second_plan_is_idempotent_after_text_is_repaired(self):
        rows = [
            {"id": "faith-tag", "name": "Fe", "slug": "faith", "normalized_name": "fe", "language": "es"},
            {"id": "fe-tag", "name": "Fe", "slug": "fe", "normalized_name": "fe", "language": "es"},
        ]

        updates, warnings = normalization_script.plan_tag_derived_updates(rows, TAG_COLUMNS)

        self.assertEqual(updates, [])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].action, "skipped_slug_update")

    def test_scripture_refs_trim_is_preserved_as_json(self):
        normalized = normalization_script.normalize_value(
            [" Alma 11:36", " Alma 12:32 "],
            normalization_script.ColumnSpec("scripture_refs", "json"),
        )

        self.assertEqual(normalized, ["Alma 11:36", "Alma 12:32"])


if __name__ == "__main__":
    unittest.main()
