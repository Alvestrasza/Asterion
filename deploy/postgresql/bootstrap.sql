-- Run with psql as a cluster administrator after reviewing all variables.
-- Example: psql -v database_name=asterion_dev -v owner_role=asterion_dev_owner -v app_role=asterion_dev_app -f bootstrap.sql

\if :{?database_name}
\else
\error 'database_name is required'
\endif
\if :{?owner_role}
\else
\error 'owner_role is required'
\endif
\if :{?app_role}
\else
\error 'app_role is required'
\endif

SELECT format('CREATE ROLE %I LOGIN', :'owner_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'owner_role')
\gexec

SELECT format('CREATE ROLE %I LOGIN', :'app_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_role')
\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'database_name', :'owner_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'database_name')
\gexec

\connect :database_name

SELECT format('REVOKE CREATE ON SCHEMA public FROM PUBLIC') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO %I', :'app_role') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I', :'owner_role', :'app_role') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %I', :'owner_role', :'app_role') \gexec
