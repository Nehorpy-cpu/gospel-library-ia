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
);

CREATE INDEX IF NOT EXISTS idx_beta_access_status ON beta_access(status);
CREATE INDEX IF NOT EXISTS idx_beta_access_user ON beta_access(user_id);

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
);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_status ON beta_feedback(status);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_type ON beta_feedback(type);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_created ON beta_feedback(created_at);

CREATE TABLE IF NOT EXISTS beta_activity_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid,
  kind varchar(80) NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_beta_activity_user_created ON beta_activity_events(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_beta_activity_kind_created ON beta_activity_events(kind, created_at);
