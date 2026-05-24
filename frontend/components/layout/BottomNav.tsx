"use client";

import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Home, Plus, Footprints, TrendingUp, User } from "lucide-react";
import { cn } from "@/lib/utils/format";

const NAV_ITEMS = [
  { href: "/home", icon: Home, label: "Home" },
  { href: "/log", icon: Plus, label: "Log" },
  { href: "/activity", icon: Footprints, label: "Activity" },
  { href: "/progress", icon: TrendingUp, label: "Progress" },
  { href: "/profile", icon: User, label: "Profile" },
] as const;

export function BottomNav() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40">
      {/* Blur backdrop */}
      <div className="absolute inset-0 glass border-t border-border-subtle" />

      <div
        className="relative flex items-center justify-around px-2"
        style={{ paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 0.5rem)", height: "var(--nav-height)" }}
      >
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/");
          const isLog = href === "/log";

          return (
            <button
              key={href}
              onClick={() => router.push(href)}
              className={cn(
                "relative flex flex-col items-center justify-center gap-1",
                "min-w-[3.5rem] h-full",
                "transition-all duration-200"
              )}
            >
              {/* Log button — special treatment */}
              {isLog ? (
                <div
                  className={cn(
                    "w-12 h-12 rounded-2xl flex items-center justify-center",
                    "bg-emerald-500 shadow-glow-emerald",
                    "transition-all duration-200",
                    isActive && "scale-95"
                  )}
                >
                  <Icon className="w-5 h-5 text-white" strokeWidth={2.5} />
                </div>
              ) : (
                <>
                  <div
                    className={cn(
                      "relative w-10 h-10 flex items-center justify-center rounded-xl",
                      "transition-all duration-200",
                      isActive
                        ? "bg-emerald-500/15"
                        : "hover:bg-surface-elevated"
                    )}
                  >
                    <Icon
                      className={cn(
                        "w-5 h-5 transition-colors duration-200",
                        isActive ? "text-emerald-400" : "text-text-muted"
                      )}
                      strokeWidth={isActive ? 2.5 : 2}
                    />
                    {/* Active dot */}
                    {isActive && (
                      <motion.div
                        layoutId="nav-dot"
                        className="absolute -bottom-1 w-1 h-1 rounded-full bg-emerald-400"
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      />
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-[10px] font-medium transition-colors duration-200",
                      isActive ? "text-emerald-400" : "text-text-muted"
                    )}
                  >
                    {label}
                  </span>
                </>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
