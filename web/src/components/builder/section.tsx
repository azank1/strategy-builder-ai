"use client";

import { cn } from "@/lib/utils";

interface SectionProps {
  title: string;
  description?: string;
  badge?: string;
  badgeColor?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export function Section({
  title,
  description,
  badge,
  badgeColor = "bg-zinc-700 text-zinc-300",
  defaultOpen = true,
  children,
}: SectionProps) {
  return (
    <details open={defaultOpen} className="group rounded-xl border border-zinc-800 bg-zinc-900/50">
      <summary className="flex cursor-pointer items-center justify-between px-5 py-4 select-none">
        <div className="flex items-center gap-3">
          <span className="text-zinc-500 transition-transform group-open:rotate-90">▶</span>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {badge && (
            <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", badgeColor)}>
              {badge}
            </span>
          )}
        </div>
        {description && (
          <p className="hidden text-sm text-zinc-500 sm:block">{description}</p>
        )}
      </summary>
      <div className="border-t border-zinc-800 px-5 py-5">{children}</div>
    </details>
  );
}
