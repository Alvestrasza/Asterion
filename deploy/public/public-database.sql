-- Invoke through the matching reviewed provision-public-database.sh wrapper.
-- All identifiers are psql identifier-quoted, and all comparisons use literals.
\set ON_ERROR_STOP on
\set ECHO none
\set ECHO_HIDDEN off
\set QUIET on

-- A failed guard deliberately causes a SQL error, so PostgreSQL 16 psql exits
-- nonzero with ON_ERROR_STOP rather than treating an early \quit as success.
SELECT current_setting('server_version_num')::integer >= 160000
   AND NOT pg_is_in_recovery()
   AND inet_server_addr() IS NULL
   AND (SELECT rolsuper FROM pg_roles WHERE rolname = current_user)
   AS local_leader_ready
\gset
\if :local_leader_ready
\else
  \warn 'Refused: a local PostgreSQL 16+ leader and a superuser are required; no DDL was attempted.'
  SELECT 1 / 0;
\endif

SELECT bool_and(value ~ '^[a-z][a-z0-9_]{0,62}$'
                AND value !~ '^pg_'
                AND value <> 'postgres'
                AND value !~ '^template'
                AND value !~ '(^|_)(internal|test|testing|dev|development)(_|$)')
       AND count(DISTINCT value) = 3 AS names_ready
FROM (VALUES (:'database_name'), (:'owner_role'), (:'runtime_role')) AS names(value)
\gset
\if :names_ready
\else
  \warn 'Refused: the three names must be distinct, new public identifiers.'
  SELECT 1 / 0;
\endif

SELECT NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'database_name')
   AND NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN (:'owner_role', :'runtime_role'))
   AS targets_absent
\gset
\if :targets_absent
\else
  \warn 'Refused: a selected database or role already exists; no existing object will be modified.'
  SELECT 1 / 0;
\endif

-- Phase 1: both new roles and their password changes are atomic. NOLOGIN is
-- retained until all database and schema privileges have been configured.
BEGIN;
SET LOCAL password_encryption = 'scram-sha-256';
CREATE ROLE :"owner_role" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE :"runtime_role" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\echo 'Set the new migration-owner password (entered twice):'
\password :"owner_role"
\echo 'Set the new runtime-role password (entered twice; use a different secret):'
\password :"runtime_role"
SELECT count(*) = 2 AND bool_and(rolpassword LIKE 'SCRAM-SHA-256$%') AS passwords_ready
FROM pg_authid WHERE rolname IN (:'owner_role', :'runtime_role')
\gset
\if :passwords_ready
\else
  \warn 'Refused: both new roles require nonempty SCRAM passwords; the role transaction will roll back.'
  SELECT 1 / 0;
\endif
COMMIT;

-- Phase 2: PostgreSQL forbids CREATE DATABASE inside a transaction. Start with
-- connections disabled, then remove PUBLIC privileges before enabling them.
CREATE DATABASE :"database_name" OWNER :"owner_role" TEMPLATE template0 ALLOW_CONNECTIONS false;
BEGIN;
REVOKE ALL PRIVILEGES ON DATABASE :"database_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database_name" TO :"owner_role", :"runtime_role";
ALTER DATABASE :"database_name" ALLOW_CONNECTIONS true;
COMMIT;

-- Reuse the same explicit local connection parameters, changing only database.
\connect -reuse-previous=on :"database_name"
SELECT current_database() = :'database_name' AND NOT pg_is_in_recovery()
   AND inet_server_addr() IS NULL AS target_ready
\gset
\if :target_ready
\else
  \warn 'Refused: the expected local writable target was not reached; application roles remain NOLOGIN.'
  SELECT 1 / 0;
\endif

-- Phase 3: only this fresh database's public schema is changed. The owner owns
-- migrations; the runtime role receives DML only, including future owner objects.
BEGIN;
ALTER SCHEMA public OWNER TO :"owner_role";
REVOKE ALL PRIVILEGES ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"runtime_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"runtime_role";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"runtime_role";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"runtime_role";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"runtime_role";
ALTER ROLE :"owner_role" LOGIN;
ALTER ROLE :"runtime_role" LOGIN;
COMMIT;

\echo 'Fresh public database, roles, and default privileges prepared; no application migration or HBA change was performed.'
