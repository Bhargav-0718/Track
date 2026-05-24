"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Zap, ArrowRight, ArrowLeft } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/store/auth";

export default function RegisterPage() {
  const router = useRouter();
  const { setToken, setUser } = useAuthStore();

  const [form, setForm] = useState({
    display_name: "",
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await authApi.register(form);
      setToken(result.access_token);
      setUser(result.user);
      router.replace("/home");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-dvh bg-background flex flex-col items-center justify-center p-6">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm"
      >
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-text-muted hover:text-text-secondary text-sm mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <div className="flex items-center gap-2 mb-10">
          <div className="w-9 h-9 rounded-xl bg-emerald-gradient flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <span className="text-xl font-semibold tracking-tight">Track</span>
        </div>

        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-1.5">Create account</h1>
          <p className="text-text-secondary text-sm">
            Start building your adaptive fitness memory.
          </p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          {[
            { key: "display_name", label: "Your name", type: "text", placeholder: "Bhargav" },
            { key: "email", label: "Email", type: "email", placeholder: "you@example.com" },
            { key: "password", label: "Password", type: "password", placeholder: "••••••••" },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key}>
              <label className="block text-sm text-text-secondary mb-1.5">{label}</label>
              <input
                type={type}
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-sm
                           placeholder:text-text-muted
                           focus:outline-none focus:border-emerald-500/50 focus:bg-surface-elevated
                           transition-all duration-200"
                placeholder={placeholder}
                required
              />
            </div>
          ))}

          {error && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-red-400 text-sm"
            >
              {error}
            </motion.p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-500 hover:bg-emerald-600
                       text-white font-medium rounded-xl py-3 text-sm
                       flex items-center justify-center gap-2
                       transition-all duration-200 disabled:opacity-50
                       shadow-glow-emerald"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>Get started <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        </form>

        <p className="text-center text-sm text-text-muted mt-6">
          Already have an account?{" "}
          <button
            onClick={() => router.push("/login")}
            className="text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            Sign in
          </button>
        </p>
      </motion.div>
    </div>
  );
}
