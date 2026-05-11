-- Run this as the postgres superuser:
-- sudo -u postgres psql -f scripts/setup_db.sql

-- 1. Create the app user
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agrosense_user') THEN
    CREATE ROLE agrosense_user WITH LOGIN PASSWORD 'yourpassword';
  END IF;
END
$$;

-- 2. Create the database
SELECT 'CREATE DATABASE agrosense_db OWNER agrosense_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agrosense_db')\gexec

-- 3. Connect to the new DB and enable extensions
\c agrosense_db

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- for fuzzy text search later

-- 4. Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE agrosense_db TO agrosense_user;
GRANT ALL ON SCHEMA public TO agrosense_user;

\echo '✅ Database setup complete. PostGIS enabled.'
