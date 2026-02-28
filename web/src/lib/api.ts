const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  token?: string;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, ...fetchOpts } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...fetchOpts, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function getNonce(): Promise<string> {
  const data = await apiFetch<{ nonce: string }>("/auth/nonce");
  return data.nonce;
}

export async function login(
  message: string,
  signature: string
): Promise<{
  access_token: string;
  wallet_address: string;
  tier: string;
  expires_in: number;
}> {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ message, signature }),
  });
}

// ─── User ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  wallet_address: string;
  ens_name: string | null;
  tier: "explorer" | "strategist" | "quant";
  subscription_expires_at: string | null;
  allowed_assets: string[];
  created_at: string;
}

export async function getProfile(token: string): Promise<UserProfile> {
  return apiFetch("/users/me", { token });
}

// ─── Systems ─────────────────────────────────────────────────────────────────

export interface SystemData {
  id: string;
  system_type: "sdca" | "ltpi";
  asset: string;
  name: string;
  description: string | null;
  system_data: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export async function listSystems(token: string): Promise<SystemData[]> {
  return apiFetch("/systems/", { token });
}

export async function createSystem(
  token: string,
  data: {
    system_type: string;
    asset: string;
    name: string;
    description?: string;
    system_data: Record<string, unknown>;
  }
): Promise<SystemData> {
  return apiFetch("/systems/", {
    method: "POST",
    body: JSON.stringify(data),
    token,
  });
}

export async function deleteSystem(
  token: string,
  systemId: string
): Promise<void> {
  await apiFetch(`/systems/${systemId}`, { method: "DELETE", token });
}

// ─── Signals ─────────────────────────────────────────────────────────────────

export interface Signal {
  id: string;
  asset: string;
  sdca_composite_z: number | null;
  ltpi_trend_ratio: number | null;
  signal_strength: string | null;
  allocation_pct: number | null;
  reasoning: string | null;
  computed_at: string;
}

export async function computeSignal(
  token: string,
  systemId: string
): Promise<Signal> {
  return apiFetch(`/signals/${systemId}/compute`, { method: "POST", token });
}

export async function getLatestSignal(
  token: string,
  systemId: string
): Promise<Signal> {
  return apiFetch(`/signals/${systemId}/latest`, { token });
}

export async function getSignalHistory(
  token: string,
  systemId: string,
  limit = 30
): Promise<Signal[]> {
  return apiFetch(`/signals/${systemId}/history?limit=${limit}`, { token });
}

// ─── Health ──────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{
  status: string;
  version: string;
  environment: string;
}> {
  return apiFetch("/health");
}
