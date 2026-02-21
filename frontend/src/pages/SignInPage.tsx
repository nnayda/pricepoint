import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

function SignInPage() {
  const { login, isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="font-db-sans flex min-h-screen items-center justify-center px-4"
      style={{ backgroundColor: "var(--th-bg-base)" }}
    >
      <div
        className="w-full max-w-sm rounded-xl p-8"
        style={{
          backgroundColor: "var(--th-bg-surface)",
          boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
        }}
      >
        <h1
          className="mb-6 text-center text-2xl font-bold"
          style={{ color: "var(--color-db-text-primary)" }}
        >
          Sign In
        </h1>

        {error && (
          <div
            className="mb-4 rounded-lg px-4 py-3 text-sm"
            role="alert"
            style={{
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              color: "#ef4444",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label
              htmlFor="email"
              className="text-sm font-medium"
              style={{ color: "var(--color-db-text-secondary)" }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 outline-none transition-shadow"
              style={{
                height: "36px",
                borderRadius: "8px",
                backgroundColor: "var(--th-bg-elevated, var(--th-bg-base))",
                color: "var(--color-db-text-primary)",
                border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
              }}
              placeholder="you@example.com"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label
              htmlFor="password"
              className="text-sm font-medium"
              style={{ color: "var(--color-db-text-secondary)" }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 outline-none transition-shadow"
              style={{
                height: "36px",
                borderRadius: "8px",
                backgroundColor: "var(--th-bg-elevated, var(--th-bg-base))",
                color: "var(--color-db-text-primary)",
                border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
              }}
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="font-semibold text-white transition-opacity disabled:opacity-60"
            style={{
              height: "34px",
              borderRadius: "7px",
              backgroundColor: "var(--color-db-accent)",
            }}
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm" style={{ color: "var(--color-db-text-secondary)" }}>
          Don&apos;t have an account?{" "}
          <Link to="/signup" className="font-medium" style={{ color: "var(--color-db-accent)" }}>
            Sign Up
          </Link>
        </p>
      </div>
    </div>
  );
}

export default SignInPage;
