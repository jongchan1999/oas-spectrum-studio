// OAS Spectrum Studio — continual-learning submission endpoint
// Supabase Edge Function (Deno). Accepts a JSON payload from the Streamlit
// app, hashes user/file identifiers, writes the raw blob to Storage, and
// inserts a row in public.cl_submissions.
//
// Deploy locally:
//   supabase functions deploy submit
//
// Env vars (auto-provided by Supabase runtime):
//   SUPABASE_URL                 — project URL
//   SUPABASE_SERVICE_ROLE_KEY    — service role key
// Custom secret set with `supabase secrets set CL_HASH_SALT=...`:
//   CL_HASH_SALT                 — repo-side salt for sha256 hashing

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const HASH_SALT = Deno.env.get("CL_HASH_SALT") ?? "oas-studio-default-salt-replace-me";
const SUBMIT_BUCKET = "cl-raw";

const SPECIES_REQUIRED = ["HONO", "HONO2", "N2O4", "N2O5", "NO", "NO2", "NO3", "O3"];

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface ClientBlock {
  app_version: string;
  method: "linear_regression" | "machine_learning";
  path_length_cm: number;
}

interface MetadataBlock {
  reference_file: string;
  measured_file: string;
  user_id: string;
  timestamp_utc: string;
  consent: boolean;
}

interface SpectrumBlock {
  wavelength_nm: number[];
  measured_absorbance: number[];
  reconstructed_absorbance: number[];
}

interface PredictionsBlock {
  species: string[];
  number_density: number[];
  ml_metrics?: { r2?: number; rmse?: number };
}

interface SubmissionPayload {
  schema_version: number;
  client: ClientBlock;
  metadata: MetadataBlock;
  spectrum: SpectrumBlock;
  predictions: PredictionsBlock;
}

async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input + HASH_SALT);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function badRequest(reason: string): Response {
  return new Response(JSON.stringify({ ok: false, error: reason }), {
    status: 400,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

function isFiniteArray(arr: unknown, minLen = 10): arr is number[] {
  if (!Array.isArray(arr) || arr.length < minLen) return false;
  for (const v of arr) {
    if (typeof v !== "number" || !Number.isFinite(v)) return false;
  }
  return true;
}

function validatePayload(p: SubmissionPayload): string | null {
  if (p?.schema_version !== 1) return "schema_version must be 1";
  if (!p.client?.app_version) return "client.app_version is required";
  if (!["linear_regression", "machine_learning"].includes(p.client?.method))
    return "client.method must be linear_regression or machine_learning";
  if (!(p.client?.path_length_cm > 0)) return "client.path_length_cm must be > 0";

  if (!p.metadata?.consent) return "metadata.consent must be true";
  if (!p.metadata?.user_id) return "metadata.user_id is required";
  if (!p.metadata?.reference_file || !p.metadata?.measured_file)
    return "metadata.reference_file and metadata.measured_file are required";

  if (!isFiniteArray(p.spectrum?.wavelength_nm)) return "spectrum.wavelength_nm invalid";
  if (!isFiniteArray(p.spectrum?.measured_absorbance)) return "spectrum.measured_absorbance invalid";
  if (!isFiniteArray(p.spectrum?.reconstructed_absorbance))
    return "spectrum.reconstructed_absorbance invalid";

  const n = p.spectrum.wavelength_nm.length;
  if (p.spectrum.measured_absorbance.length !== n) return "measured_absorbance length mismatch";
  if (p.spectrum.reconstructed_absorbance.length !== n) return "reconstructed_absorbance length mismatch";

  const wmin = Math.min(...p.spectrum.wavelength_nm);
  const wmax = Math.max(...p.spectrum.wavelength_nm);
  if (!(wmin >= 100 && wmax <= 900 && wmin < wmax)) return "wavelength range out of bounds";

  if (!Array.isArray(p.predictions?.species) || p.predictions.species.length !== SPECIES_REQUIRED.length)
    return "predictions.species must list 8 species";
  if (!Array.isArray(p.predictions?.number_density) ||
      p.predictions.number_density.length !== p.predictions.species.length)
    return "predictions.number_density length mismatch";
  for (const v of p.predictions.number_density) {
    if (typeof v !== "number" || !Number.isFinite(v) || v < 0)
      return "predictions.number_density must be finite and non-negative";
  }

  return null;
}

function storageKey(submissionId: string, submittedAt: Date): string {
  const yyyy = submittedAt.getUTCFullYear();
  const mm = String(submittedAt.getUTCMonth() + 1).padStart(2, "0");
  return `raw/${yyyy}/${mm}/${submissionId}.json`;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: CORS_HEADERS });
  }
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", {
      status: 405,
      headers: CORS_HEADERS,
    });
  }

  let payload: SubmissionPayload;
  try {
    payload = (await req.json()) as SubmissionPayload;
  } catch {
    return badRequest("body must be valid JSON");
  }

  const reason = validatePayload(payload);
  if (reason) return badRequest(reason);

  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: { persistSession: false },
  });

  const submittedAt = new Date();
  const submissionId = crypto.randomUUID();

  const userHash = await sha256Hex(`user:${payload.metadata.user_id}`);
  const refHash = await sha256Hex(
    `file:${payload.metadata.reference_file}:${payload.spectrum.wavelength_nm[0]}:${payload.spectrum.measured_absorbance[0]}`
  );
  const measHash = await sha256Hex(
    `file:${payload.metadata.measured_file}:${payload.spectrum.wavelength_nm[0]}:${payload.spectrum.measured_absorbance[0]}`
  );
  const key = storageKey(submissionId, submittedAt);

  // 1) Upload raw blob
  const uploadRes = await supabase.storage
    .from(SUBMIT_BUCKET)
    .upload(key, new Blob([JSON.stringify(payload)], { type: "application/json" }), {
      contentType: "application/json",
      upsert: false,
    });
  if (uploadRes.error) {
    return new Response(
      JSON.stringify({ ok: false, error: `storage: ${uploadRes.error.message}` }),
      { status: 500, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
    );
  }

  // 2) Insert metadata row in public.cl_submissions
  const wmin = Math.min(...payload.spectrum.wavelength_nm);
  const wmax = Math.max(...payload.spectrum.wavelength_nm);
  const r2 = payload.predictions.ml_metrics?.r2 ?? null;
  const rmse = payload.predictions.ml_metrics?.rmse ?? null;

  const insertSub = await supabase.from("cl_submissions").insert({
    id: submissionId,
    schema_version: payload.schema_version,
    submitted_at: submittedAt.toISOString(),
    app_version: payload.client.app_version,
    method: payload.client.method,
    path_length_cm: payload.client.path_length_cm,
    user_hash: userHash,
    reference_hash: refHash,
    measured_hash: measHash,
    storage_key: key,
    wavelength_min_nm: wmin,
    wavelength_max_nm: wmax,
    n_points: payload.spectrum.wavelength_nm.length,
    ml_r2: r2,
    ml_rmse: rmse,
    status: "raw",
  });
  if (insertSub.error) {
    // Best-effort cleanup of the uploaded blob.
    await supabase.storage.from(SUBMIT_BUCKET).remove([key]);
    return new Response(
      JSON.stringify({ ok: false, error: `db: ${insertSub.error.message}` }),
      { status: 500, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
    );
  }

  // 3) Insert per-species rows
  const speciesRows = payload.predictions.species.map((sp, idx) => ({
    submission_id: submissionId,
    species: sp,
    number_density: payload.predictions.number_density[idx],
  }));
  await supabase.from("cl_submission_species").insert(speciesRows);

  // 4) Insert filename map into the owner-only schema (best-effort)
  await supabase.from("filename_map" as never).insert({
    submission_id: submissionId,
    user_hash: userHash,
    reference_filename: payload.metadata.reference_file,
    measured_filename: payload.metadata.measured_file,
  });
  // (If the owner_only schema is enforced via search_path, we may need to
  // call .schema('owner_only').from('filename_map') in a future Supabase
  // client version. For now relying on the search_path includes 'owner_only'.)

  return new Response(
    JSON.stringify({
      ok: true,
      submission_id: submissionId,
      storage_key: key,
    }),
    { status: 201, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
  );
});
