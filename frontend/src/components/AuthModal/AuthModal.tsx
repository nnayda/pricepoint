import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../../contexts/AuthContext";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type AuthTab = "signin" | "register";

function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const { login, register, error } = useAuth();
  const [activeTab, setActiveTab] = useState<AuthTab>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const displayError = localError || error;

  function resetForm() {
    setEmail("");
    setPassword("");
    setDisplayName("");
    setConfirmPassword("");
    setLocalError(null);
  }

  function handleTabSwitch(tab: AuthTab) {
    setActiveTab(tab);
    resetForm();
  }

  async function handleSignIn(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      resetForm();
      onClose();
    } catch {
      // error is set in context
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRegister(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);

    if (password !== confirmPassword) {
      setLocalError("Passwords do not match");
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email, password, displayName);
      resetForm();
      onClose();
    } catch {
      // error is set in context
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      data-testid="auth-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={() => {}}
      role="presentation"
    >
      <div
        className="w-full max-w-md rounded-xl bg-bg-card p-6 shadow-lg"
        role="dialog"
        aria-label="Authentication"
        aria-modal="true"
      >
        {/* Tab buttons */}
        <div className="mb-6 flex border-b border-border-main">
          <button
            type="button"
            className={`flex-1 pb-2 text-sm font-medium transition-colors ${
              activeTab === "signin"
                ? "border-b-2 border-brand-blue text-brand-blue"
                : "text-text-sec hover:text-text-pri"
            }`}
            onClick={() => handleTabSwitch("signin")}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`flex-1 pb-2 text-sm font-medium transition-colors ${
              activeTab === "register"
                ? "border-b-2 border-brand-blue text-brand-blue"
                : "text-text-sec hover:text-text-pri"
            }`}
            onClick={() => handleTabSwitch("register")}
          >
            Register
          </button>
        </div>

        {/* Error display */}
        {displayError && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600" role="alert">
            {displayError}
          </div>
        )}

        {/* Sign In form */}
        {activeTab === "signin" && (
          <form onSubmit={handleSignIn} aria-label="Sign in form">
            <div className="mb-4">
              <label
                htmlFor="signin-email"
                className="mb-1 block text-sm font-medium text-text-pri"
              >
                Email
              </label>
              <input
                id="signin-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-border-main px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
                placeholder="you@example.com"
              />
            </div>
            <div className="mb-6">
              <label
                htmlFor="signin-password"
                className="mb-1 block text-sm font-medium text-text-pri"
              >
                Password
              </label>
              <input
                id="signin-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border-main px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
                placeholder="Enter your password"
              />
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-lg bg-brand-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? "Signing in..." : "Sign In"}
            </button>
          </form>
        )}

        {/* Register form */}
        {activeTab === "register" && (
          <form onSubmit={handleRegister} aria-label="Register form">
            <div className="mb-4">
              <label
                htmlFor="register-email"
                className="mb-1 block text-sm font-medium text-text-pri"
              >
                Email
              </label>
              <input
                id="register-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-border-main px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
                placeholder="you@example.com"
              />
            </div>
            <div className="mb-4">
              <label
                htmlFor="register-display-name"
                className="mb-1 block text-sm font-medium text-text-pri"
              >
                Display Name
              </label>
              <input
                id="register-display-name"
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full rounded-lg border border-border-main px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
                placeholder="Your name"
              />
            </div>
            <div className="mb-4">
              <label
                htmlFor="register-password"
                className="mb-1 block text-sm font-medium text-text-pri"
              >
                Password
              </label>
              <input
                id="register-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border-main px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
                placeholder="Create a password"
              />
            </div>
            <div className="mb-6">
              <label
                htmlFor="register-confirm-password"
                className="mb-1 block text-sm font-medium text-text-pri"
              >
                Confirm Password
              </label>
              <input
                id="register-confirm-password"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-lg border border-border-main px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
                placeholder="Confirm your password"
              />
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-lg bg-brand-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? "Creating account..." : "Create Account"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default AuthModal;
