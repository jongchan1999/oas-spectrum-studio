-- OAS Spectrum Studio — Continual Learning corpus schema (v1)
-- Apply via Supabase SQL editor *once* after creating the project.
-- Idempotent: safe to re-run; uses IF NOT EXISTS / DO $$ blocks.

-- ────────────────────────────────────────────────────────────────────────────
-- 1) Extensions
-- ────────────────────────────────────────────────────────────────────────────

create extension if not exists "pgcrypto";   -- for gen_random_uuid()

-- ────────────────────────────────────────────────────────────────────────────
-- 2) Public corpus table — `cl_submissions`
--
-- Holds one row per accepted continual-learning sample. The raw spectrum +
-- prediction JSON lives in Supabase Storage; this table just indexes it
-- with hashed identifiers and quick filters for the curation worker.
-- ────────────────────────────────────────────────────────────────────────────

create table if not exists public.cl_submissions (
    id                  uuid primary key default gen_random_uuid(),
    schema_version      smallint      not null default 1,
    submitted_at        timestamptz   not null default now(),

    -- Client / runtime context
    app_version         text          not null,
    method              text          not null check (method in ('linear_regression','machine_learning')),
    path_length_cm      real          not null check (path_length_cm > 0),

    -- Hashed identity (never stores plaintext username or filename)
    user_hash           text          not null,            -- sha256(username + salt)
    reference_hash      text          not null,            -- sha256(reference filename + bytes)
    measured_hash       text          not null,            -- sha256(measured filename + bytes)

    -- Storage pointer to the raw JSON payload
    storage_key         text          not null unique,     -- e.g. raw/2026/05/<uuid>.json

    -- Quick-filter fields the curation worker uses without fetching the blob
    wavelength_min_nm   real          not null,
    wavelength_max_nm   real          not null,
    n_points            integer       not null check (n_points >= 10),
    ml_r2               real,                              -- nullable: only set for ML submissions
    ml_rmse             real,

    -- Curation lifecycle
    status              text          not null default 'raw'
                                           check (status in ('raw','accepted','rejected','training')),
    rejection_reason    text,
    accepted_at         timestamptz,

    -- Release attribution (set when this row enters a training release)
    release_id          text                              -- e.g. 'v2' once promoted
);

create index if not exists cl_submissions_status_idx       on public.cl_submissions(status);
create index if not exists cl_submissions_submitted_idx    on public.cl_submissions(submitted_at desc);
create index if not exists cl_submissions_user_hash_idx    on public.cl_submissions(user_hash);
create index if not exists cl_submissions_release_idx      on public.cl_submissions(release_id);

-- ────────────────────────────────────────────────────────────────────────────
-- 3) Per-species number-density preview, joined to a submission
-- ────────────────────────────────────────────────────────────────────────────

create table if not exists public.cl_submission_species (
    submission_id uuid    not null references public.cl_submissions(id) on delete cascade,
    species       text    not null,
    number_density double precision not null,
    primary key (submission_id, species)
);

-- ────────────────────────────────────────────────────────────────────────────
-- 4) Owner-only filename mapping (kept private under a separate schema)
--
-- Lets us reconstruct the original filenames for the contributor's own
-- submissions only — used for revocation requests / audit. The corpus
-- itself never references plaintext filenames.
-- ────────────────────────────────────────────────────────────────────────────

create schema if not exists owner_only;

create table if not exists owner_only.filename_map (
    submission_id        uuid primary key references public.cl_submissions(id) on delete cascade,
    user_hash            text not null,
    reference_filename   text not null,
    measured_filename    text not null,
    created_at           timestamptz not null default now()
);

create index if not exists filename_map_user_hash_idx
    on owner_only.filename_map(user_hash);

-- ────────────────────────────────────────────────────────────────────────────
-- 5) Row-level security (RLS)
--
-- Inserts come exclusively from the edge function, which uses the
-- service-role key and therefore bypasses RLS. Public reads are blocked.
-- ────────────────────────────────────────────────────────────────────────────

alter table public.cl_submissions       enable row level security;
alter table public.cl_submission_species enable row level security;

-- No SELECT/INSERT/UPDATE/DELETE policy for anon — table is effectively
-- service-role-only until we add a dashboard. Curation worker uses the
-- service role; the app posts through the edge function (also service role).
-- (Intentionally no policies created; default-deny is what we want.)

-- ────────────────────────────────────────────────────────────────────────────
-- 5b) Explicit GRANTs to service_role
--
-- service_role bypasses RLS, but it still needs table-level GRANTs. In
-- Supabase those are normally provided by the "Automatically expose new
-- tables" project setting; when that setting is OFF, the GRANTs never get
-- applied and the edge function fails with `permission denied for table`.
-- Make the GRANTs explicit so the schema is self-sufficient regardless of
-- project-level toggles.
-- ────────────────────────────────────────────────────────────────────────────

grant usage on schema public      to service_role;
grant usage on schema owner_only  to service_role;

grant all privileges on table public.cl_submissions        to service_role;
grant all privileges on table public.cl_submission_species to service_role;
grant all privileges on table owner_only.filename_map      to service_role;

grant all privileges on all sequences in schema public     to service_role;
grant all privileges on all sequences in schema owner_only to service_role;

alter default privileges in schema public
    grant all privileges on tables to service_role;
alter default privileges in schema owner_only
    grant all privileges on tables to service_role;

-- ────────────────────────────────────────────────────────────────────────────
-- 6) Storage bucket sanity (run separately via Supabase dashboard or CLI)
-- ────────────────────────────────────────────────────────────────────────────
--
-- Storage buckets are not created via SQL. In the Supabase dashboard:
--   Storage → New bucket → name = "cl-raw" → Public = OFF
-- Or via CLI:
--   supabase storage create cl-raw --private
--
-- The edge function uploads raw payloads to:
--   cl-raw/YYYY/MM/<uuid>.json
