-- ============================================
-- PostgreSQL Database Initialization Script
-- ============================================
-- Creates all required databases for MLOps services:
-- - mlflow: MLflow experiment tracking
-- - airflow: Airflow metadata store
-- - monitoring: Monitoring metrics (Evidently)
-- - serving: Serving API/UI logs and metrics
-- ============================================
-- This script is idempotent - safe to run multiple times
-- ============================================

-- Create mlflow database if it doesn't exist
SELECT 'CREATE DATABASE mlflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec

-- Create airflow database if it doesn't exist
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

-- Create monitoring database if it doesn't exist
SELECT 'CREATE DATABASE monitoring'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'monitoring')\gexec

-- Create serving database if it doesn't exist
SELECT 'CREATE DATABASE serving'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'serving')\gexec

-- Note: The user is created automatically by PostgreSQL from POSTGRES_USER env var
-- Since the user is the superuser, it already has all privileges on all databases
