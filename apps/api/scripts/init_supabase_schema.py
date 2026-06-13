"""Initialize the PostgreSQL schema required by the production API.

This is a conservative bootstrap tool for an empty or already-compatible
database. It never drops or truncates objects and it does not seed data.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class TableSpec:
    name: str
    required_columns: tuple[str, ...]


TABLE_SPECS = (
    TableSpec(
        "sources",
        (
            "id",
            "key",
            "name",
            "base_url",
            "source_type",
            "language",
            "enabled",
            "crawl_strategy",
            "rate_limit",
            "max_pages_per_run",
            "last_crawled_at",
            "robots_policy_notes",
            "config",
            "created_at",
            "updated_at",
        ),
    ),
    TableSpec(
        "crawl_urls",
        (
            "id",
            "source_id",
            "url",
            "normalized_url",
            "status",
            "depth",
            "attempts",
            "created_at",
            "updated_at",
        ),
    ),
    TableSpec(
        "documents",
        (
            "id",
            "source_id",
            "title",
            "canonical_url",
            "author",
            "published_at",
            "language",
            "category",
            "tags",
            "scripture_refs",
            "text",
            "raw_metadata",
            "content_hash",
            "status",
            "version",
            "is_indexed",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
    ),
    TableSpec(
        "document_assets",
        ("id", "document_id", "asset_type", "storage_key", "checksum", "created_at"),
    ),
    TableSpec(
        "document_chunks",
        (
            "id",
            "document_id",
            "chunk_index",
            "chunker_version",
            "language",
            "section_title",
            "start_char",
            "end_char",
            "token_count",
            "text",
            "text_hash",
            "metadata",
            "search_vector",
            "created_at",
            "updated_at",
        ),
    ),
    TableSpec(
        "ingestion_jobs",
        (
            "id",
            "source_id",
            "source",
            "job_type",
            "status",
            "priority",
            "payload",
            "documents_found",
            "documents_created",
            "documents_updated",
            "documents_skipped",
            "documents_failed",
            "errors",
            "attempts",
            "error",
            "created_at",
            "started_at",
            "finished_at",
        ),
    ),
    TableSpec("authors", ("id", "slug", "display_name", "normalized_name", "metadata", "created_at", "updated_at")),
    TableSpec("tags", ("id", "slug", "name", "normalized_name", "language", "created_at")),
    TableSpec(
        "document_duplicate_relations",
        (
            "id",
            "canonical_document_id",
            "duplicate_document_id",
            "classification",
            "detection_rule",
            "confidence",
            "review_status",
            "evidence",
            "created_at",
            "updated_at",
        ),
    ),
    TableSpec(
        "chat_sessions",
        ("id", "user_id", "title", "language", "mode", "summary", "metadata", "created_at", "updated_at"),
    ),
    TableSpec(
        "chat_messages",
        ("id", "session_id", "role", "content", "citations", "metadata", "created_at"),
    ),
    TableSpec(
        "study_workspaces",
        (
            "id",
            "user_id",
            "name",
            "description",
            "source_filters",
            "settings",
            "client_rev",
            "server_rev",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
    ),
    TableSpec(
        "study_workspace_sources",
        (
            "id",
            "workspace_id",
            "user_id",
            "source_key",
            "language",
            "author",
            "category",
            "tags",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
    ),
    TableSpec(
        "study_notes",
        (
            "id",
            "workspace_id",
            "user_id",
            "document_id",
            "chunk_id",
            "title",
            "content",
            "selected_text",
            "selection_range",
            "scripture_refs",
            "color",
            "position",
            "client_rev",
            "server_rev",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
    ),
    TableSpec(
        "study_highlights",
        (
            "id",
            "workspace_id",
            "user_id",
            "document_id",
            "chunk_id",
            "note_id",
            "start_char",
            "end_char",
            "selected_text",
            "scripture_refs",
            "color",
            "metadata",
            "client_rev",
            "server_rev",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
    ),
    TableSpec(
        "saved_citations",
        (
            "id",
            "workspace_id",
            "user_id",
            "document_id",
            "chunk_id",
            "quote",
            "selected_text",
            "citation_url",
            "source_url",
            "source_title",
            "source_author",
            "location",
            "scripture_refs",
            "metadata",
            "client_rev",
            "server_rev",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
    ),
    TableSpec(
        "post_its",
        (
            "id",
            "workspace_id",
            "user_id",
            "document_id",
            "content",
            "color",
            "position",
            "source_filters",
            "pinned",
            "client_rev",
            "server_rev",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
    ),
    TableSpec(
        "user_preferences",
        (
            "user_id",
            "calling_category",
            "calling_name",
            "custom_calling_name",
            "calling_focus_enabled",
            "settings",
            "created_at",
            "updated_at",
        ),
    ),
    TableSpec(
        "beta_access",
        (
            "id",
            "user_id",
            "email",
            "name",
            "status",
            "study_profile",
            "preferred_language",
            "preferred_sources",
            "request_message",
            "admin_notes",
            "approved_at",
            "onboarding_completed_at",
            "created_at",
            "updated_at",
        ),
    ),
    TableSpec(
        "beta_feedback",
        (
            "id",
            "user_id",
            "email",
            "page",
            "type",
            "message",
            "screenshot_url",
            "status",
            "created_at",
            "updated_at",
        ),
    ),
    TableSpec("beta_activity_events", ("id", "user_id", "kind", "metadata", "created_at")),
)

EXPECTED_TABLES = tuple(spec.name for spec in TABLE_SPECS)
PRIMARY_ENDPOINT_TABLES = (
    "sources",
    "documents",
    "document_chunks",
    "ingestion_jobs",
    "authors",
    "tags",
    "document_duplicate_relations",
)

SCHEMA_STATEMENTS = (
    """
    CREATE EXTENSION IF NOT EXISTS pgcrypto
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      key varchar(100) NOT NULL UNIQUE,
      name varchar(255) NOT NULL,
      base_url text NOT NULL,
      source_type varchar(100),
      language varchar(16),
      default_language varchar(16),
      is_official boolean NOT NULL DEFAULT false,
      trust_level integer NOT NULL DEFAULT 5,
      scraping_enabled boolean NOT NULL DEFAULT true,
      enabled boolean NOT NULL DEFAULT true,
      crawl_strategy varchar(80) NOT NULL DEFAULT 'html_discovery',
      rate_limit integer NOT NULL DEFAULT 30,
      max_pages_per_run integer NOT NULL DEFAULT 25,
      last_crawled_at timestamptz,
      robots_policy_notes text,
      config jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS crawl_urls (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      source_id uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
      url text NOT NULL,
      normalized_url text NOT NULL,
      status varchar(64) NOT NULL DEFAULT 'discovered',
      depth integer NOT NULL DEFAULT 0,
      discovered_from text,
      http_status integer,
      content_type varchar(255),
      content_hash varchar(64),
      etag varchar(255),
      last_modified varchar(255),
      error text,
      attempts integer NOT NULL DEFAULT 0,
      last_crawled_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT uq_crawl_url_source_normalized UNIQUE (source_id, normalized_url)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
      crawl_url_id uuid REFERENCES crawl_urls(id) ON DELETE SET NULL,
      title text NOT NULL,
      canonical_url text NOT NULL,
      author text,
      published_at timestamptz,
      language varchar(16),
      category text,
      tags jsonb NOT NULL DEFAULT '[]'::jsonb,
      scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      text text,
      raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      content_hash varchar(64) NOT NULL,
      status varchar(64) NOT NULL DEFAULT 'READY',
      version integer NOT NULL DEFAULT 1,
      is_indexed boolean NOT NULL DEFAULT false,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz,
      CONSTRAINT uq_documents_canonical_url UNIQUE (canonical_url)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS document_assets (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      asset_type varchar(32) NOT NULL,
      source_url text,
      storage_key text NOT NULL,
      mime_type varchar(255),
      size_bytes bigint,
      checksum varchar(64) NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT uq_document_asset_source UNIQUE (document_id, asset_type, source_url)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      chunk_index integer NOT NULL,
      chunker_version varchar(64) NOT NULL DEFAULT 'smart-v1',
      language varchar(16),
      title text,
      section_title text,
      page_number integer,
      start_char integer NOT NULL,
      end_char integer NOT NULL,
      token_count integer NOT NULL,
      text text NOT NULL,
      text_hash varchar(64) NOT NULL,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      search_vector tsvector,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT uq_chunk_version UNIQUE (document_id, chunk_index, chunker_version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_jobs (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      source_id uuid REFERENCES sources(id) ON DELETE SET NULL,
      source varchar(100),
      job_type varchar(80) NOT NULL,
      status varchar(64) NOT NULL DEFAULT 'queued',
      priority integer NOT NULL DEFAULT 5,
      payload jsonb NOT NULL DEFAULT '{}'::jsonb,
      documents_found integer NOT NULL DEFAULT 0,
      documents_created integer NOT NULL DEFAULT 0,
      documents_updated integer NOT NULL DEFAULT 0,
      documents_skipped integer NOT NULL DEFAULT 0,
      documents_failed integer NOT NULL DEFAULT 0,
      errors jsonb NOT NULL DEFAULT '[]'::jsonb,
      attempts integer NOT NULL DEFAULT 0,
      error text,
      created_at timestamptz NOT NULL DEFAULT now(),
      started_at timestamptz,
      finished_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS authors (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      slug text NOT NULL UNIQUE,
      display_name text NOT NULL,
      sort_name text,
      normalized_name text NOT NULL,
      bio text,
      birth_date date,
      death_date date,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tags (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      slug text NOT NULL UNIQUE,
      name text NOT NULL,
      normalized_name text NOT NULL,
      language varchar(16) NOT NULL DEFAULT 'es',
      description text,
      created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS document_duplicate_relations (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      canonical_document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      duplicate_document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      classification varchar(40) NOT NULL,
      detection_rule varchar(80) NOT NULL,
      confidence double precision NOT NULL,
      review_status varchar(24) NOT NULL DEFAULT 'pending',
      evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      reviewed_at timestamptz,
      CONSTRAINT ck_document_duplicate_distinct CHECK (canonical_document_id <> duplicate_document_id),
      CONSTRAINT uq_document_duplicate_relation_duplicate UNIQUE (duplicate_document_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid,
      title text,
      language varchar(16),
      mode varchar(64) NOT NULL DEFAULT 'doctrinal_assistant',
      summary text,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
      role varchar(32) NOT NULL,
      content text NOT NULL,
      citations jsonb NOT NULL DEFAULT '[]'::jsonb,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS study_workspaces (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid,
      name text NOT NULL,
      description text,
      source_filters jsonb NOT NULL DEFAULT '{}'::jsonb,
      settings jsonb NOT NULL DEFAULT '{}'::jsonb,
      client_rev integer NOT NULL DEFAULT 1,
      server_rev integer NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS study_workspace_sources (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id uuid NOT NULL REFERENCES study_workspaces(id) ON DELETE CASCADE,
      user_id uuid,
      source_key varchar(100),
      language varchar(16),
      author text,
      category text,
      tags jsonb NOT NULL DEFAULT '[]'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS study_notes (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id uuid NOT NULL REFERENCES study_workspaces(id) ON DELETE CASCADE,
      user_id uuid,
      document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
      chunk_id uuid,
      title text,
      content text NOT NULL,
      selected_text text,
      selection_range jsonb NOT NULL DEFAULT '{}'::jsonb,
      scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      color varchar(32) NOT NULL DEFAULT 'yellow',
      position jsonb NOT NULL DEFAULT '{}'::jsonb,
      client_rev integer NOT NULL DEFAULT 1,
      server_rev integer NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz
    )
    """,
    """
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS saved_citations (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id uuid NOT NULL REFERENCES study_workspaces(id) ON DELETE CASCADE,
      user_id uuid,
      document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      chunk_id uuid,
      quote text NOT NULL,
      selected_text text,
      citation_url text,
      source_url text,
      source_title text,
      source_author text,
      location jsonb NOT NULL DEFAULT '{}'::jsonb,
      scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      client_rev integer NOT NULL DEFAULT 1,
      server_rev integer NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS post_its (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id uuid NOT NULL REFERENCES study_workspaces(id) ON DELETE CASCADE,
      user_id uuid,
      document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
      content text NOT NULL,
      color varchar(32) NOT NULL DEFAULT 'yellow',
      position jsonb NOT NULL DEFAULT '{}'::jsonb,
      source_filters jsonb NOT NULL DEFAULT '{}'::jsonb,
      pinned boolean NOT NULL DEFAULT false,
      client_rev integer NOT NULL DEFAULT 1,
      server_rev integer NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_preferences (
      user_id uuid PRIMARY KEY,
      calling_category varchar(120),
      calling_name varchar(200),
      custom_calling_name varchar(200),
      calling_focus_enabled boolean NOT NULL DEFAULT false,
      settings jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beta_access (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid,
      email varchar(320) NOT NULL,
      name text,
      status varchar(32) NOT NULL DEFAULT 'pending',
      study_profile varchar(160),
      preferred_language varchar(16),
      preferred_sources jsonb NOT NULL DEFAULT '[]'::jsonb,
      request_message text,
      admin_notes text,
      approved_at timestamptz,
      onboarding_completed_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT uq_beta_access_email UNIQUE (email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beta_feedback (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid,
      email varchar(320),
      page text NOT NULL,
      type varchar(80) NOT NULL DEFAULT 'other',
      message text NOT NULL,
      screenshot_url text,
      status varchar(40) NOT NULL DEFAULT 'new',
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beta_activity_events (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid,
      kind varchar(80) NOT NULL,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
)

INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_sources_enabled_type ON sources(enabled, source_type)",
    "CREATE INDEX IF NOT EXISTS idx_sources_last_crawled ON sources(last_crawled_at)",
    "CREATE INDEX IF NOT EXISTS idx_crawl_urls_status ON crawl_urls(status)",
    "CREATE INDEX IF NOT EXISTS idx_crawl_urls_hash ON crawl_urls(content_hash)",
    "CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language)",
    "CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash)",
    "CREATE INDEX IF NOT EXISTS idx_documents_status_updated ON documents(status, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_documents_source_status ON documents(source_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_documents_tags_gin ON documents USING gin(tags)",
    "CREATE INDEX IF NOT EXISTS idx_documents_scripture_refs_gin ON documents USING gin(scripture_refs)",
    "CREATE INDEX IF NOT EXISTS idx_documents_raw_metadata_gin ON documents USING gin(raw_metadata)",
    "CREATE INDEX IF NOT EXISTS idx_document_assets_hash ON document_assets(checksum)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_document_index ON document_chunks(document_id, chunk_index)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_language ON document_chunks(language)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON document_chunks USING gin(metadata)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON document_chunks USING gin(search_vector)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_text_hash ON document_chunks(text_hash)",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status_type ON ingestion_jobs(status, job_type)",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_created ON ingestion_jobs(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_source ON ingestion_jobs(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_authors_normalized_name ON authors(normalized_name)",
    "CREATE INDEX IF NOT EXISTS idx_tags_normalized_name ON tags(normalized_name)",
    "CREATE INDEX IF NOT EXISTS idx_document_duplicate_canonical ON document_duplicate_relations(canonical_document_id)",
    "CREATE INDEX IF NOT EXISTS idx_document_duplicate_classification_status ON document_duplicate_relations(classification, review_status)",
    "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_workspaces_user_updated ON study_workspaces(user_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_workspaces_deleted ON study_workspaces(deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_study_workspace_sources_workspace_updated ON study_workspace_sources(workspace_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_workspace_sources_user_updated ON study_workspace_sources(user_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_workspace_sources_source ON study_workspace_sources(source_key)",
    "CREATE INDEX IF NOT EXISTS idx_study_notes_workspace_updated ON study_notes(workspace_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_notes_user_updated ON study_notes(user_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_notes_document ON study_notes(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_study_notes_chunk ON study_notes(chunk_id)",
    "CREATE INDEX IF NOT EXISTS idx_study_notes_deleted ON study_notes(deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_study_highlights_workspace_updated ON study_highlights(workspace_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_highlights_user_updated ON study_highlights(user_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_study_highlights_document ON study_highlights(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_study_highlights_chunk ON study_highlights(chunk_id)",
    "CREATE INDEX IF NOT EXISTS idx_study_highlights_note ON study_highlights(note_id)",
    "CREATE INDEX IF NOT EXISTS idx_study_highlights_deleted ON study_highlights(deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_saved_citations_workspace_updated ON saved_citations(workspace_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_saved_citations_user_updated ON saved_citations(user_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_saved_citations_document ON saved_citations(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_saved_citations_chunk ON saved_citations(chunk_id)",
    "CREATE INDEX IF NOT EXISTS idx_saved_citations_deleted ON saved_citations(deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_post_its_workspace_updated ON post_its(workspace_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_post_its_user_updated ON post_its(user_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_post_its_document ON post_its(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_post_its_deleted ON post_its(deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_user_preferences_calling ON user_preferences(calling_category, calling_name)",
    "CREATE INDEX IF NOT EXISTS idx_beta_access_status ON beta_access(status)",
    "CREATE INDEX IF NOT EXISTS idx_beta_access_user ON beta_access(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_beta_feedback_status ON beta_feedback(status)",
    "CREATE INDEX IF NOT EXISTS idx_beta_feedback_type ON beta_feedback(type)",
    "CREATE INDEX IF NOT EXISTS idx_beta_feedback_created ON beta_feedback(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_beta_activity_user_created ON beta_activity_events(user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_beta_activity_kind_created ON beta_activity_events(kind, created_at DESC)",
)

ALTER_TABLE_STATEMENTS = (
    """
    ALTER TABLE IF EXISTS sources
      ADD COLUMN IF NOT EXISTS source_type varchar(100),
      ADD COLUMN IF NOT EXISTS language varchar(16),
      ADD COLUMN IF NOT EXISTS default_language varchar(16),
      ADD COLUMN IF NOT EXISTS is_official boolean NOT NULL DEFAULT false,
      ADD COLUMN IF NOT EXISTS trust_level integer NOT NULL DEFAULT 5,
      ADD COLUMN IF NOT EXISTS scraping_enabled boolean NOT NULL DEFAULT true,
      ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true,
      ADD COLUMN IF NOT EXISTS crawl_strategy varchar(80) NOT NULL DEFAULT 'html_discovery',
      ADD COLUMN IF NOT EXISTS rate_limit integer NOT NULL DEFAULT 30,
      ADD COLUMN IF NOT EXISTS max_pages_per_run integer NOT NULL DEFAULT 25,
      ADD COLUMN IF NOT EXISTS last_crawled_at timestamptz,
      ADD COLUMN IF NOT EXISTS robots_policy_notes text,
      ADD COLUMN IF NOT EXISTS config jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS crawl_urls
      ADD COLUMN IF NOT EXISTS discovered_from text,
      ADD COLUMN IF NOT EXISTS http_status integer,
      ADD COLUMN IF NOT EXISTS content_type varchar(255),
      ADD COLUMN IF NOT EXISTS content_hash varchar(64),
      ADD COLUMN IF NOT EXISTS etag varchar(255),
      ADD COLUMN IF NOT EXISTS last_modified varchar(255),
      ADD COLUMN IF NOT EXISTS error text,
      ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS last_crawled_at timestamptz,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS documents
      ADD COLUMN IF NOT EXISTS crawl_url_id uuid,
      ADD COLUMN IF NOT EXISTS author text,
      ADD COLUMN IF NOT EXISTS published_at timestamptz,
      ADD COLUMN IF NOT EXISTS language varchar(16),
      ADD COLUMN IF NOT EXISTS category text,
      ADD COLUMN IF NOT EXISTS tags jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS text text,
      ADD COLUMN IF NOT EXISTS raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS content_hash varchar(64),
      ADD COLUMN IF NOT EXISTS status varchar(64) NOT NULL DEFAULT 'READY',
      ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS is_indexed boolean NOT NULL DEFAULT false,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS deleted_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS document_assets
      ADD COLUMN IF NOT EXISTS source_url text,
      ADD COLUMN IF NOT EXISTS mime_type varchar(255),
      ADD COLUMN IF NOT EXISTS size_bytes bigint,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS document_chunks
      ADD COLUMN IF NOT EXISTS chunker_version varchar(64) NOT NULL DEFAULT 'smart-v1',
      ADD COLUMN IF NOT EXISTS language varchar(16),
      ADD COLUMN IF NOT EXISTS title text,
      ADD COLUMN IF NOT EXISTS section_title text,
      ADD COLUMN IF NOT EXISTS page_number integer,
      ADD COLUMN IF NOT EXISTS start_char integer,
      ADD COLUMN IF NOT EXISTS end_char integer,
      ADD COLUMN IF NOT EXISTS token_count integer,
      ADD COLUMN IF NOT EXISTS text_hash varchar(64),
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS search_vector tsvector,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS ingestion_jobs
      ADD COLUMN IF NOT EXISTS source_id uuid,
      ADD COLUMN IF NOT EXISTS source varchar(100),
      ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 5,
      ADD COLUMN IF NOT EXISTS payload jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS documents_found integer NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS documents_created integer NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS documents_updated integer NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS documents_skipped integer NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS documents_failed integer NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS errors jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS error text,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS started_at timestamptz,
      ADD COLUMN IF NOT EXISTS finished_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS authors
      ADD COLUMN IF NOT EXISTS sort_name text,
      ADD COLUMN IF NOT EXISTS normalized_name text,
      ADD COLUMN IF NOT EXISTS bio text,
      ADD COLUMN IF NOT EXISTS birth_date date,
      ADD COLUMN IF NOT EXISTS death_date date,
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS tags
      ADD COLUMN IF NOT EXISTS normalized_name text,
      ADD COLUMN IF NOT EXISTS language varchar(16) NOT NULL DEFAULT 'es',
      ADD COLUMN IF NOT EXISTS description text,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS document_duplicate_relations
      ADD COLUMN IF NOT EXISTS review_status varchar(24) NOT NULL DEFAULT 'pending',
      ADD COLUMN IF NOT EXISTS evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS reviewed_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS chat_sessions
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS title text,
      ADD COLUMN IF NOT EXISTS language varchar(16),
      ADD COLUMN IF NOT EXISTS mode varchar(64) NOT NULL DEFAULT 'doctrinal_assistant',
      ADD COLUMN IF NOT EXISTS summary text,
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS chat_messages
      ADD COLUMN IF NOT EXISTS citations jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS study_workspaces
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS description text,
      ADD COLUMN IF NOT EXISTS source_filters jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS settings jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS deleted_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS study_workspace_sources
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS source_key varchar(100),
      ADD COLUMN IF NOT EXISTS language varchar(16),
      ADD COLUMN IF NOT EXISTS author text,
      ADD COLUMN IF NOT EXISTS category text,
      ADD COLUMN IF NOT EXISTS tags jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS deleted_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS study_notes
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS document_id uuid,
      ADD COLUMN IF NOT EXISTS chunk_id uuid,
      ADD COLUMN IF NOT EXISTS title text,
      ADD COLUMN IF NOT EXISTS selected_text text,
      ADD COLUMN IF NOT EXISTS selection_range jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS color varchar(32) NOT NULL DEFAULT 'yellow',
      ADD COLUMN IF NOT EXISTS position jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS deleted_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS study_highlights
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS chunk_id uuid,
      ADD COLUMN IF NOT EXISTS note_id uuid,
      ADD COLUMN IF NOT EXISTS scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS color varchar(32) NOT NULL DEFAULT 'yellow',
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS deleted_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS saved_citations
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS chunk_id uuid,
      ADD COLUMN IF NOT EXISTS selected_text text,
      ADD COLUMN IF NOT EXISTS citation_url text,
      ADD COLUMN IF NOT EXISTS source_url text,
      ADD COLUMN IF NOT EXISTS source_title text,
      ADD COLUMN IF NOT EXISTS source_author text,
      ADD COLUMN IF NOT EXISTS location jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS scripture_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS deleted_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS post_its
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS document_id uuid,
      ADD COLUMN IF NOT EXISTS color varchar(32) NOT NULL DEFAULT 'yellow',
      ADD COLUMN IF NOT EXISTS position jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS source_filters jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS pinned boolean NOT NULL DEFAULT false,
      ADD COLUMN IF NOT EXISTS client_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS server_rev integer NOT NULL DEFAULT 1,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS deleted_at timestamptz
    """,
    """
    ALTER TABLE IF EXISTS user_preferences
      ADD COLUMN IF NOT EXISTS calling_category varchar(120),
      ADD COLUMN IF NOT EXISTS calling_name varchar(200),
      ADD COLUMN IF NOT EXISTS custom_calling_name varchar(200),
      ADD COLUMN IF NOT EXISTS calling_focus_enabled boolean NOT NULL DEFAULT false,
      ADD COLUMN IF NOT EXISTS settings jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS beta_access
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS name text,
      ADD COLUMN IF NOT EXISTS status varchar(32) NOT NULL DEFAULT 'pending',
      ADD COLUMN IF NOT EXISTS study_profile varchar(160),
      ADD COLUMN IF NOT EXISTS preferred_language varchar(16),
      ADD COLUMN IF NOT EXISTS preferred_sources jsonb NOT NULL DEFAULT '[]'::jsonb,
      ADD COLUMN IF NOT EXISTS request_message text,
      ADD COLUMN IF NOT EXISTS admin_notes text,
      ADD COLUMN IF NOT EXISTS approved_at timestamptz,
      ADD COLUMN IF NOT EXISTS onboarding_completed_at timestamptz,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS beta_feedback
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS email varchar(320),
      ADD COLUMN IF NOT EXISTS type varchar(80) NOT NULL DEFAULT 'other',
      ADD COLUMN IF NOT EXISTS screenshot_url text,
      ADD COLUMN IF NOT EXISTS status varchar(40) NOT NULL DEFAULT 'new',
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """,
    """
    ALTER TABLE IF EXISTS beta_activity_events
      ADD COLUMN IF NOT EXISTS user_id uuid,
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()
    """,
)

TYPE_ALIGNMENT_STATEMENTS = (
    """
    DO $$
    DECLARE current_type text;
    BEGIN
      SELECT udt_name INTO current_type
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'status';
      IF current_type IS NOT NULL AND current_type NOT IN ('varchar', 'text') THEN
        ALTER TABLE documents ALTER COLUMN status DROP DEFAULT;
        ALTER TABLE documents ALTER COLUMN status TYPE varchar(64) USING status::text;
        ALTER TABLE documents ALTER COLUMN status SET DEFAULT 'READY';
      END IF;
    END
    $$
    """,
    """
    DO $$
    DECLARE current_type text;
    BEGIN
      SELECT udt_name INTO current_type
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'ingestion_jobs' AND column_name = 'status';
      IF current_type IS NOT NULL AND current_type NOT IN ('varchar', 'text') THEN
        ALTER TABLE ingestion_jobs ALTER COLUMN status DROP DEFAULT;
        ALTER TABLE ingestion_jobs ALTER COLUMN status TYPE varchar(64) USING status::text;
        ALTER TABLE ingestion_jobs ALTER COLUMN status SET DEFAULT 'queued';
      END IF;
    END
    $$
    """,
    """
    DO $$
    DECLARE current_type text;
    BEGIN
      SELECT udt_name INTO current_type
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'chat_messages' AND column_name = 'role';
      IF current_type IS NOT NULL AND current_type NOT IN ('varchar', 'text') THEN
        ALTER TABLE chat_messages ALTER COLUMN role TYPE varchar(32) USING role::text;
      END IF;
    END
    $$
    """,
)

SEARCH_VECTOR_STATEMENTS = (
    """
    CREATE OR REPLACE FUNCTION update_chunk_search_vector()
    RETURNS trigger AS $$
    BEGIN
      NEW.search_vector :=
        setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(NEW.section_title, '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(NEW.text, '')), 'C');
      RETURN NEW;
    END
    $$ LANGUAGE plpgsql
    """,
    """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_update_chunk_search_vector'
          AND tgrelid = 'public.document_chunks'::regclass
          AND NOT tgisinternal
      ) THEN
        CREATE TRIGGER trg_update_chunk_search_vector
        BEFORE INSERT OR UPDATE ON document_chunks
        FOR EACH ROW EXECUTE FUNCTION update_chunk_search_vector();
      END IF;
    END
    $$
    """,
)

REQUIRED_COLUMN_TYPES = {
    ("sources", "id"): {"uuid"},
    ("sources", "config"): {"jsonb"},
    ("documents", "id"): {"uuid"},
    ("documents", "source_id"): {"uuid"},
    ("documents", "tags"): {"jsonb"},
    ("documents", "scripture_refs"): {"jsonb"},
    ("documents", "raw_metadata"): {"jsonb"},
    ("documents", "is_indexed"): {"bool"},
    ("documents", "status"): {"text", "varchar"},
    ("documents", "created_at"): {"timestamptz"},
    ("documents", "updated_at"): {"timestamptz"},
    ("document_chunks", "id"): {"uuid"},
    ("document_chunks", "document_id"): {"uuid"},
    ("document_chunks", "metadata"): {"jsonb"},
    ("document_chunks", "search_vector"): {"tsvector"},
    ("ingestion_jobs", "id"): {"uuid"},
    ("ingestion_jobs", "status"): {"text", "varchar"},
    ("ingestion_jobs", "payload"): {"jsonb"},
    ("ingestion_jobs", "errors"): {"jsonb"},
    ("document_duplicate_relations", "duplicate_document_id"): {"uuid"},
    ("chat_messages", "role"): {"text", "varchar"},
}


def get_existing_tables(conn) -> set[str]:
    rows = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = ANY(%s)
        """,
        (list(EXPECTED_TABLES),),
    ).fetchall()
    return {row[0] for row in rows}


def validate_required_columns(conn) -> dict[str, tuple[str, ...]]:
    missing: dict[str, tuple[str, ...]] = {}
    for spec in TABLE_SPECS:
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (spec.name,),
        ).fetchall()
        existing_columns = {row[0] for row in rows}
        missing_columns = tuple(column for column in spec.required_columns if column not in existing_columns)
        if missing_columns:
            missing[spec.name] = missing_columns
    return missing


def get_existing_columns(conn) -> dict[str, set[str]]:
    rows = conn.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ANY(%s)
        """,
        (list(EXPECTED_TABLES),),
    ).fetchall()
    columns = {table_name: set() for table_name in EXPECTED_TABLES}
    for table_name, column_name in rows:
        columns[table_name].add(column_name)
    return columns


def validate_required_types(conn) -> dict[str, tuple[str, str, tuple[str, ...]]]:
    rows = conn.execute(
        """
        SELECT table_name, column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ANY(%s)
        """,
        (list(EXPECTED_TABLES),),
    ).fetchall()
    actual_types = {(table_name, column_name): udt_name for table_name, column_name, udt_name in rows}
    incompatible = {}
    for key, expected_types in REQUIRED_COLUMN_TYPES.items():
        actual_type = actual_types.get(key)
        if actual_type is not None and actual_type not in expected_types:
            table_name, column_name = key
            incompatible[f"{table_name}.{column_name}"] = (
                table_name,
                actual_type,
                tuple(sorted(expected_types)),
            )
    return incompatible


def initialize_schema(conn) -> tuple[list[str], list[str], dict[str, list[str]]]:
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("gospel_library_schema_init_v1",))
    existing_before = get_existing_tables(conn)
    columns_before = get_existing_columns(conn)

    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
    for statement in ALTER_TABLE_STATEMENTS:
        conn.execute(statement)
    for statement in TYPE_ALIGNMENT_STATEMENTS:
        conn.execute(statement)

    missing_columns = validate_required_columns(conn)
    if missing_columns:
        details = "; ".join(
            f"{table}: {', '.join(columns)}" for table, columns in sorted(missing_columns.items())
        )
        raise RuntimeError(
            "Existing tables are not compatible with the API schema. "
            f"Missing columns: {details}. No tables or data were removed."
        )

    incompatible_types = validate_required_types(conn)
    if incompatible_types:
        details = "; ".join(
            f"{name}: found {actual}, expected {'/'.join(expected)}"
            for name, (_, actual, expected) in sorted(incompatible_types.items())
        )
        raise RuntimeError(
            "Existing columns use incompatible PostgreSQL types. "
            f"{details}. Types were not changed automatically."
        )

    for statement in INDEX_STATEMENTS:
        conn.execute(statement)
    for statement in SEARCH_VECTOR_STATEMENTS:
        conn.execute(statement)

    existing_after = get_existing_tables(conn)
    missing_tables = sorted(set(EXPECTED_TABLES) - existing_after)
    if missing_tables:
        raise RuntimeError(f"Schema verification failed for tables: {', '.join(missing_tables)}")

    created = sorted(existing_after - existing_before)
    verified = sorted(existing_after & existing_before)
    columns_after = get_existing_columns(conn)
    added_columns = {
        table_name: sorted(columns_after[table_name] - columns_before.get(table_name, set()))
        for table_name in verified
        if columns_after[table_name] - columns_before.get(table_name, set())
    }
    return created, verified, added_columns


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL is not set. Set it and run this script again.", file=sys.stderr)
        return 2

    connect_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    try:
        with psycopg.connect(connect_url) as conn:
            created, verified, added_columns = initialize_schema(conn)
            conn.commit()
    except Exception as exc:
        detail = f" {exc}" if isinstance(exc, RuntimeError) else ""
        print(
            f"ERROR: schema initialization failed ({type(exc).__name__}). "
            f"DATABASE_URL was not printed and no destructive operation was attempted.{detail}",
            file=sys.stderr,
        )
        return 1

    print("Supabase/PostgreSQL schema initialization completed.")
    print(f"Tables created: {len(created)}")
    for table_name in created:
        print(f"  CREATED  {table_name}")
    print(f"Tables already present and verified: {len(verified)}")
    for table_name in verified:
        print(f"  VERIFIED {table_name}")
    print(f"Existing tables extended with missing columns: {len(added_columns)}")
    for table_name, column_names in sorted(added_columns.items()):
        print(f"  ALTERED  {table_name}: {', '.join(column_names)}")
    print(f"Total required tables verified: {len(EXPECTED_TABLES)}")
    print(
        "Primary endpoint schema verified: "
        + ", ".join(PRIMARY_ENDPOINT_TABLES)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
