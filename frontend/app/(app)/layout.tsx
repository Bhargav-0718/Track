"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { BottomNav } from "@/components/layout/BottomNav";
import { FloatingAIButton } from "@/components/shared/FloatingAIButton";
import { useAuthStore } from "@/lib/store/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-dvh">
        <div className="w-8 h-8 rounded-full border-2 border-emerald-500/30 border-t-emerald-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="relative min-h-dvh bg-background">
      {/* Page content */}
      <AnimatePresence mode="wait">
        <motion.main
          key={pathname}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
          className="page-content"
        >
          {children}
        </motion.main>
      </AnimatePresence>

      {/* Floating AI button */}
      <FloatingAIButton />

      {/* Bottom navigation */}
      <BottomNav />
    </div>
  );
}
