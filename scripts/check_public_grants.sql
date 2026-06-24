-- List current table grants for Supabase browser-facing roles.
-- Run in Supabase SQL Editor. This script is read-only.

select
  grantee,
  table_name,
  privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
order by grantee, table_name, privilege_type;
