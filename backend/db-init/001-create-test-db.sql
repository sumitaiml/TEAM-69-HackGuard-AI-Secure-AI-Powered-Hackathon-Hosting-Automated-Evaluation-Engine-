-- Runs automatically on first container startup (empty data volume only).
-- The main app DB (hackeval_db) is created via POSTGRES_DB; the test
-- suite needs a separate database so it can freely drop/recreate tables
-- without touching dev data.
CREATE DATABASE hackeval_test;
