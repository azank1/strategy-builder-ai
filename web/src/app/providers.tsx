"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";
import { useState, type ReactNode } from "react";
import { Toaster } from "sonner";
import { config } from "@/lib/wagmi";
import { AuthProvider } from "@/components/auth/auth-provider";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60_000 },
        },
      })
  );

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          {children}
          <Toaster theme="dark" position="bottom-right" />
        </AuthProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
