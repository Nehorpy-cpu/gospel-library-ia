CREATE TABLE IF NOT EXISTS user_preferences (
  user_id uuid PRIMARY KEY,
  calling_category varchar(120),
  calling_name varchar(200),
  custom_calling_name varchar(200),
  calling_focus_enabled boolean NOT NULL DEFAULT false,
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_calling
  ON user_preferences(calling_category, calling_name);
