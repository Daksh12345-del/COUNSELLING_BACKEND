-- Sarvpratham Education Consultants — Database Schema
-- PostgreSQL
-- Run this once against your database before starting the server:
--   psql "$DATABASE_URL" -f schema.sql

-- ===== ENUMS =====
DO $$ BEGIN
  CREATE TYPE enquiry_status AS ENUM ('New', 'Contacted', 'Enrolled', 'Not interested');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE booking_status AS ENUM ('Confirmed', 'Completed', 'Cancelled', 'No-show');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE session_type AS ENUM ('Phone Call', 'Google Meet', 'WhatsApp');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ===== ADMIN USERS =====
-- No more hardcoded "admin123" in the frontend. Real accounts, hashed passwords.
CREATE TABLE IF NOT EXISTS admin_users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== ENQUIRIES (the "Free Enquiry" form at the bottom of the page) =====
CREATE TABLE IF NOT EXISTS enquiries (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  email VARCHAR(150),
  current_class VARCHAR(50),
  stream VARCHAR(50),
  course VARCHAR(120),
  city VARCHAR(100),
  message VARCHAR(1000),
  status enquiry_status NOT NULL DEFAULT 'New',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_enquiries_created_at ON enquiries (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_enquiries_status ON enquiries (status);
CREATE INDEX IF NOT EXISTS idx_enquiries_phone ON enquiries (phone);

-- ===== BOOKINGS (the "Schedule Free Call" widget) =====
CREATE TABLE IF NOT EXISTS bookings (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  session_type session_type NOT NULL DEFAULT 'Phone Call',
  booking_date DATE NOT NULL,
  day_label VARCHAR(50),
  time_slot VARCHAR(20) NOT NULL,
  stream VARCHAR(50),
  course VARCHAR(120),
  status booking_status NOT NULL DEFAULT 'Confirmed',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings (booking_date);

-- A slot is only "taken" while the booking is active. Cancelling frees it up again.
-- This partial unique index is the real guard against double-booking, enforced at the
-- database level so two near-simultaneous requests can never both succeed.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_slot
  ON bookings (booking_date, time_slot)
  WHERE status <> 'Cancelled';

-- ===== updated_at trigger for enquiries =====
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enquiries_updated_at ON enquiries;
CREATE TRIGGER trg_enquiries_updated_at
  BEFORE UPDATE ON enquiries
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
