-- Migration 0001 — v1.2 raw-data + full-metrics columns
--
-- Adds the schema-v2 columns to an existing `public.cl_submissions` table.
-- Idempotent: every statement uses IF NOT EXISTS, so it is safe to re-run and
-- safe to apply on top of the original v1 schema.
--
-- Apply via the Supabase SQL editor (or `supabase db push`) once, then deploy
-- the updated edge function:  supabase functions deploy submit
--
-- Background: v1.2 merges the linear-regression / machine-learning paths and
-- auto-selects the higher-R² reconstruction. Every opted-in analysis now
-- persists (a) the raw reference + measured intensity traces, (b) the full
-- reconstruction metrics, and (c) the fit settings used to produce them.

alter table public.cl_submissions
    add column if not exists recon_r2        real,
    add column if not exists recon_rmse      real,
    add column if not exists recon_mae       real,
    add column if not exists recon_mape      real,
    add column if not exists selected_method text,
    add column if not exists fit_config      jsonb,
    add column if not exists raw_reference   jsonb,
    add column if not exists raw_measured    jsonb;

-- Backfill the new reconstruction-metric columns from the legacy ml_* columns
-- so historical rows are not left null where the value is already known.
update public.cl_submissions
   set recon_r2   = coalesce(recon_r2, ml_r2),
       recon_rmse = coalesce(recon_rmse, ml_rmse)
 where recon_r2 is null
    or recon_rmse is null;

-- Quick filter for "submissions that carry the raw input traces".
create index if not exists cl_submissions_has_raw_idx
    on public.cl_submissions ((raw_reference is not null));
