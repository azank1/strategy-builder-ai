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
  system_type: "valuation" | "trend" | "momentum" | "rotation";
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
  valuation_score: number | null;
  trend_score: number | null;
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

// ─── Additional system operations ────────────────────────────────────────────

export async function updateSystem(
  token: string,
  systemId: string,
  data: {
    name?: string;
    description?: string;
    system_data?: Record<string, unknown>;
    is_active?: boolean;
  }
): Promise<SystemData> {
  return apiFetch(`/systems/${systemId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
    token,
  });
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export async function getDashboardSignals(token: string): Promise<Signal[]> {
  return apiFetch("/signals/dashboard", { token });
}

export interface PortfolioResponse {
  signals: Signal[];
  total_allocation: number;
  computed_at: string;
}

export async function computePortfolio(
  token: string
): Promise<PortfolioResponse> {
  return apiFetch("/signals/portfolio", { method: "POST", token });
}

// ─── Admin ───────────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string;
  wallet_address: string;
  ens_name: string | null;
  tier: "explorer" | "strategist" | "quant";
  subscription_expires_at: string | null;
  system_count: number;
  signal_count: number;
  created_at: string;
}

export interface AdminUsersResponse {
  users: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface PlatformStats {
  total_users: number;
  users_by_tier: Record<string, number>;
  total_systems: number;
  total_signals: number;
  signals_last_24h: number;
}

export async function getAdminUsers(
  token: string,
  page = 1,
  pageSize = 50
): Promise<AdminUsersResponse> {
  return apiFetch(`/admin/users?page=${page}&page_size=${pageSize}`, { token });
}

export async function updateUserTier(
  token: string,
  userId: string,
  tier: string,
  subscriptionExpiresAt?: string
): Promise<{ ok: boolean; tier: string }> {
  return apiFetch(`/admin/users/${userId}/tier`, {
    method: "PATCH",
    body: JSON.stringify({
      tier,
      subscription_expires_at: subscriptionExpiresAt ?? null,
    }),
    token,
  });
}

export async function getPlatformStats(
  token: string
): Promise<PlatformStats> {
  return apiFetch("/admin/stats", { token });
}

// ─── Analysis (Builder endpoints) ────────────────────────────────────────────

export interface ValidationIssue {
  rule: string;
  message: string;
  severity: "error" | "warning";
  indicator_name: string | null;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  error_count: number;
  warning_count: number;
  summary: string;
}

export async function validateSystem(
  token: string,
  systemType: string,
  systemData: Record<string, unknown>
): Promise<ValidationResult> {
  return apiFetch("/analysis/validate", {
    method: "POST",
    body: JSON.stringify({ system_type: systemType, system_data: systemData }),
    token,
  });
}

export interface ZScoreResult {
  z_score: number;
  mean: number;
  std: number;
  raw_value: number;
  data_points_used: number;
  outliers_removed: number;
  method: string;
}

export async function computeZScore(
  token: string,
  values: number[],
  currentValue: number,
  outlierMethod = "iqr",
  useLogTransform = false
): Promise<ZScoreResult> {
  return apiFetch("/analysis/zscore", {
    method: "POST",
    body: JSON.stringify({
      values,
      current_value: currentValue,
      outlier_method: outlierMethod,
      use_log_transform: useLogTransform,
    }),
    token,
  });
}

export interface CoherencyResult {
  agreement_ratio: number;
  constructive_ratio: number;
  destructive_ratio: number;
  mixed_ratio: number;
  per_indicator_alignment: Record<string, number>;
  avg_pairwise_correlation: number;
  is_coherent: boolean;
  summary: string;
  outlier_indicators: string[];
}

export async function analyzeCoherency(
  token: string,
  signals: Record<string, number[]>
): Promise<CoherencyResult> {
  return apiFetch("/analysis/coherency", {
    method: "POST",
    body: JSON.stringify({ signals }),
    token,
  });
}

export interface RegimeResult {
  current_regime: string;
  confidence: number;
  regimes: { date: string; regime: string }[];
  description: string;
}

export async function detectRegime(
  token: string,
  asset: string
): Promise<RegimeResult> {
  return apiFetch(`/analysis/regime/${asset}`, { token });
}

export interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface PriceData {
  asset: string;
  frequency: string;
  data: PricePoint[];
  count: number;
}

export async function getPriceData(
  token: string,
  asset: string,
  start?: string,
  end?: string,
  frequency = "1D"
): Promise<PriceData> {
  const params = new URLSearchParams({ frequency });
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  return apiFetch(`/analysis/prices/${asset}?${params}`, { token });
}
