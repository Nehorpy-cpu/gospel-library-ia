DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'SyncEntity') THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_enum e
      JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'SyncEntity' AND e.enumlabel = 'STUDY_WORKSPACE'
    ) THEN
      ALTER TYPE "SyncEntity" ADD VALUE 'STUDY_WORKSPACE';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'SyncEntity' AND e.enumlabel = 'STUDY_NOTE'
    ) THEN
      ALTER TYPE "SyncEntity" ADD VALUE 'STUDY_NOTE';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'SyncEntity' AND e.enumlabel = 'STUDY_HIGHLIGHT'
    ) THEN
      ALTER TYPE "SyncEntity" ADD VALUE 'STUDY_HIGHLIGHT';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'SyncEntity' AND e.enumlabel = 'SAVED_CITATION'
    ) THEN
      ALTER TYPE "SyncEntity" ADD VALUE 'SAVED_CITATION';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'SyncEntity' AND e.enumlabel = 'POST_IT'
    ) THEN
      ALTER TYPE "SyncEntity" ADD VALUE 'POST_IT';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'SyncEntity' AND e.enumlabel = 'STUDY_WORKSPACE_SOURCE'
    ) THEN
      ALTER TYPE "SyncEntity" ADD VALUE 'STUDY_WORKSPACE_SOURCE';
    END IF;
  END IF;
END $$;

ALTER TABLE IF EXISTS study_workspaces
  ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

DO $$
BEGIN
  IF to_regclass('public.study_workspaces') IS NOT NULL THEN
    CREATE INDEX IF NOT EXISTS idx_study_workspaces_user_updated ON study_workspaces(user_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_study_workspaces_deleted ON study_workspaces(deleted_at);
  END IF;
END $$;

ALTER TABLE IF EXISTS study_workspace_sources
  ADD COLUMN IF NOT EXISTS user_id uuid,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

DO $$
BEGIN
  IF to_regclass('public.study_workspace_sources') IS NOT NULL
     AND to_regclass('public.study_workspaces') IS NOT NULL
  THEN
    UPDATE study_workspace_sources sws
    SET user_id = sw.user_id
    FROM study_workspaces sw
    WHERE sws.workspace_id = sw.id AND sws.user_id IS NULL;

    CREATE INDEX IF NOT EXISTS idx_study_workspace_sources_workspace_updated ON study_workspace_sources(workspace_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_study_workspace_sources_user_updated ON study_workspace_sources(user_id, updated_at);
  END IF;
END $$;

ALTER TABLE IF EXISTS study_notes
  ADD COLUMN IF NOT EXISTS user_id uuid,
  ADD COLUMN IF NOT EXISTS selected_text text,
  ADD COLUMN IF NOT EXISTS selection_range jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1;

DO $$
BEGIN
  IF to_regclass('public.study_notes') IS NOT NULL
     AND to_regclass('public.study_workspaces') IS NOT NULL
  THEN
    UPDATE study_notes sn
    SET user_id = sw.user_id
    FROM study_workspaces sw
    WHERE sn.workspace_id = sw.id AND sn.user_id IS NULL;

    CREATE INDEX IF NOT EXISTS idx_study_notes_user_updated ON study_notes(user_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_study_notes_chunk ON study_notes(chunk_id);
    CREATE INDEX IF NOT EXISTS idx_study_notes_deleted ON study_notes(deleted_at);
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.study_workspaces') IS NOT NULL
     AND to_regclass('public.documents') IS NOT NULL
     AND to_regclass('public.study_notes') IS NOT NULL
  THEN
    CREATE TABLE IF NOT EXISTS study_highlights (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id uuid NOT NULL REFERENCES study_workspaces(id) ON DELETE CASCADE,
      user_id uuid,
      document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      chunk_id uuid,
      note_id uuid REFERENCES study_notes(id) ON DELETE SET NULL,
      start_char integer NOT NULL,
      end_char integer NOT NULL,
      selected_text text NOT NULL,
      scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      color varchar(32) NOT NULL DEFAULT 'yellow',
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      client_rev integer NOT NULL DEFAULT 1,
      server_rev integer NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz
    );
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.study_highlights') IS NOT NULL THEN
    CREATE INDEX IF NOT EXISTS idx_study_highlights_workspace_updated ON study_highlights(workspace_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_study_highlights_user_updated ON study_highlights(user_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_study_highlights_document ON study_highlights(document_id);
    CREATE INDEX IF NOT EXISTS idx_study_highlights_chunk ON study_highlights(chunk_id);
    CREATE INDEX IF NOT EXISTS idx_study_highlights_note ON study_highlights(note_id);
    CREATE INDEX IF NOT EXISTS idx_study_highlights_deleted ON study_highlights(deleted_at);
  END IF;
END $$;

ALTER TABLE IF EXISTS saved_citations
  ADD COLUMN IF NOT EXISTS user_id uuid,
  ADD COLUMN IF NOT EXISTS selected_text text,
  ADD COLUMN IF NOT EXISTS source_url text,
  ADD COLUMN IF NOT EXISTS source_title text,
  ADD COLUMN IF NOT EXISTS source_author text,
  ADD COLUMN IF NOT EXISTS location jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

DO $$
BEGIN
  IF to_regclass('public.saved_citations') IS NOT NULL
     AND to_regclass('public.study_workspaces') IS NOT NULL
  THEN
    UPDATE saved_citations sc
    SET user_id = sw.user_id
    FROM study_workspaces sw
    WHERE sc.workspace_id = sw.id AND sc.user_id IS NULL;

    CREATE INDEX IF NOT EXISTS idx_saved_citations_workspace_updated ON saved_citations(workspace_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_saved_citations_user_updated ON saved_citations(user_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_saved_citations_chunk ON saved_citations(chunk_id);
    CREATE INDEX IF NOT EXISTS idx_saved_citations_deleted ON saved_citations(deleted_at);
  END IF;
END $$;

ALTER TABLE IF EXISTS post_its
  ADD COLUMN IF NOT EXISTS user_id uuid,
  ADD COLUMN IF NOT EXISTS source_filters jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1;

DO $$
BEGIN
  IF to_regclass('public.post_its') IS NOT NULL
     AND to_regclass('public.study_workspaces') IS NOT NULL
  THEN
    UPDATE post_its pi
    SET user_id = sw.user_id
    FROM study_workspaces sw
    WHERE pi.workspace_id = sw.id AND pi.user_id IS NULL;

    CREATE INDEX IF NOT EXISTS idx_post_its_user_updated ON post_its(user_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_post_its_deleted ON post_its(deleted_at);
  END IF;
END $$;
