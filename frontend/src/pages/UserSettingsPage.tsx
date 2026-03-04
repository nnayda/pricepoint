import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import DashboardNav from "../components/dashboard/DashboardNav";
import SavedPlacesSection from "../components/settings/SavedPlacesSection";
import { useSavedPois } from "../hooks/useSavedPois";
import axios from "axios";

function UserSettingsPage() {
  const { user, isAuthenticated, isLoading, refreshAuth } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { pois: savedPois, add: addPoi, remove: removePoi } = useSavedPois();

  if (isLoading) return null;
  if (!isAuthenticated) return <Navigate to="/signin" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setSaving(true);
    try {
      const token = localStorage.getItem("pricepoint-auth-token");
      await axios.put(
        "/api/auth/me",
        { display_name: displayName },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      await refreshAuth();
      setSuccess(true);
    } catch {
      setError("Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="font-db-sans min-h-screen" style={{ backgroundColor: "var(--color-db-bg)" }}>
      <DashboardNav />
      <div className="flex min-h-screen flex-col items-center gap-6 px-4 pt-20 pb-12">
        <div
          className="w-full max-w-md rounded-xl p-8"
          style={{
            backgroundColor: "var(--th-bg-surface)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
          }}
        >
          <h1 className="mb-6 text-2xl font-bold" style={{ color: "var(--color-db-text-primary)" }}>
            Account Settings
          </h1>

          {success && (
            <div
              className="mb-4 rounded-lg px-4 py-3 text-sm"
              role="status"
              style={{
                backgroundColor: "rgba(34, 197, 94, 0.1)",
                color: "#16a34a",
              }}
            >
              Profile updated successfully
            </div>
          )}

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

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="flex flex-col gap-1">
              <label
                htmlFor="settings-email"
                className="text-sm font-medium"
                style={{ color: "var(--color-db-text-secondary)" }}
              >
                Email
              </label>
              <input
                id="settings-email"
                type="email"
                disabled
                value={user?.email ?? ""}
                className="w-full px-3 opacity-60"
                style={{
                  height: "36px",
                  borderRadius: "8px",
                  backgroundColor: "var(--th-bg-elevated, var(--th-bg-base))",
                  color: "var(--color-db-text-primary)",
                  border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
                }}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label
                htmlFor="settings-display-name"
                className="text-sm font-medium"
                style={{ color: "var(--color-db-text-secondary)" }}
              >
                Display Name
              </label>
              <input
                id="settings-display-name"
                type="text"
                value={displayName}
                onChange={(e) => {
                  setDisplayName(e.target.value);
                  setSuccess(false);
                }}
                className="w-full px-3 outline-none transition-shadow"
                style={{
                  height: "36px",
                  borderRadius: "8px",
                  backgroundColor: "var(--th-bg-elevated, var(--th-bg-base))",
                  color: "var(--color-db-text-primary)",
                  border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
                }}
                placeholder="Your display name"
              />
            </div>

            <div className="flex flex-col gap-1">
              <span
                className="text-sm font-medium"
                style={{ color: "var(--color-db-text-secondary)" }}
              >
                Account Type
              </span>
              <p className="text-sm" style={{ color: "var(--color-db-text-primary)" }}>
                {user?.is_admin ? "Administrator" : "Standard User"}
              </p>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="font-semibold text-white transition-opacity disabled:opacity-60"
              style={{
                height: "34px",
                borderRadius: "7px",
                backgroundColor: "var(--color-db-accent)",
              }}
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </form>
        </div>

        {/* Saved Places section */}
        <div
          className="w-full max-w-md rounded-xl p-8"
          style={{
            backgroundColor: "var(--th-bg-surface)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
          }}
        >
          <SavedPlacesSection pois={savedPois} onAdd={addPoi} onRemove={removePoi} />
        </div>
      </div>
    </div>
  );
}

export default UserSettingsPage;
