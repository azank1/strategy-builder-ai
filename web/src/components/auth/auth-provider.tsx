"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useAccount, useSignMessage } from "wagmi";
import * as api from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

/**
 * Build an EIP-4361 (SIWE) message string without pulling in `siwe` + ethers.
 * Reference: https://eips.ethereum.org/EIPS/eip-4361
 */
function buildSiweMessage(params: {
  domain: string;
  address: string;
  statement: string;
  uri: string;
  version: string;
  chainId: number;
  nonce: string;
}): string {
  const now = new Date().toISOString();
  return [
    `${params.domain} wants you to sign in with your Ethereum account:`,
    params.address,
    "",
    params.statement,
    "",
    `URI: ${params.uri}`,
    `Version: ${params.version}`,
    `Chain ID: ${params.chainId}`,
    `Nonce: ${params.nonce}`,
    `Issued At: ${now}`,
  ].join("\n");
}

interface AuthUser {
  id: string;
  wallet_address: string;
  ens_name: string | null;
  tier: "explorer" | "strategist" | "quant";
  subscription_expires_at: string | null;
  allowed_assets: string[];
  created_at: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  login: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: false,
  isAdmin: false,
  login: async () => {},
  logout: () => {},
});

// ─── Storage helpers ─────────────────────────────────────────────────────────

const TOKEN_KEY = "sbai_token";

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

function setStoredToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ─── Provider ────────────────────────────────────────────────────────────────

const ADMIN_WALLETS = (
  process.env.NEXT_PUBLIC_ADMIN_WALLETS || ""
)
  .split(",")
  .map((w) => w.trim().toLowerCase())
  .filter(Boolean);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { address, isConnected, chainId } = useAccount();
  const { signMessageAsync } = useSignMessage();

  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const stored = getStoredToken();
    if (stored && isConnected) {
      setToken(stored);
      api
        .getProfile(stored)
        .then((profile) => setUser(profile as unknown as AuthUser))
        .catch(() => {
          clearStoredToken();
          setToken(null);
        });
    }
  }, [isConnected]);

  // Clear auth when wallet disconnects
  useEffect(() => {
    if (!isConnected) {
      setToken(null);
      setUser(null);
      clearStoredToken();
    }
  }, [isConnected]);

  const login = useCallback(async () => {
    if (!address || !chainId) return;
    setIsLoading(true);
    try {
      const nonce = await api.getNonce();
      const messageStr = buildSiweMessage({
        domain: window.location.host,
        address,
        statement: "Sign in to Strategy Builder AI",
        uri: window.location.origin,
        version: "1",
        chainId,
        nonce,
      });
      const signature = await signMessageAsync({ message: messageStr });
      const res = await api.login(messageStr, signature);
      setStoredToken(res.access_token);
      setToken(res.access_token);

      const profile = await api.getProfile(res.access_token);
      setUser(profile as unknown as AuthUser);
    } catch (err) {
      console.error("Login failed:", err);
      clearStoredToken();
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [address, chainId, signMessageAsync]);

  const logout = useCallback(() => {
    clearStoredToken();
    setToken(null);
    setUser(null);
  }, []);

  const isAdmin = useMemo(
    () =>
      !!user &&
      ADMIN_WALLETS.includes(user.wallet_address.toLowerCase()),
    [user]
  );

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      isAuthenticated: !!token && !!user,
      isLoading,
      isAdmin,
      login,
      logout,
    }),
    [token, user, isLoading, isAdmin, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useAuth() {
  return useContext(AuthContext);
}
