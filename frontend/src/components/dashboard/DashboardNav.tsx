import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTheme } from "../../contexts/ThemeContext";
import { useAuth } from "../../contexts/AuthContext";
import SearchBar from "../SearchBar/SearchBar";
import PricePointLogo from "../ui/PricePointLogo";
import { startViewTransition } from "../../utils/viewTransition";
import type { GeocodeResult } from "../../types";

function DashboardNav() {
  const { resolvedTheme, toggleTheme } = useTheme();
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [menuOpen]);

  function handleLogout() {
    logout();
    setMenuOpen(false);
    navigate("/");
  }

  function handleSearchSelect(result: GeocodeResult) {
    startViewTransition(() => {
      navigate(
        `/property/${encodeURIComponent(result.display_name)}?lat=${result.lat}&lon=${result.lon}`,
      );
    });
  }

  const initials = user?.display_name
    ? user.display_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : (user?.email?.charAt(0).toUpperCase() ?? "U");

  return (
    <nav
      className="fixed top-0 right-0 left-0 z-50 flex h-16 items-center justify-between border-b border-[var(--th-border-subtle)] px-6 font-db-sans"
      style={{
        backgroundColor: "var(--th-nav-bg)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      }}
    >
      <div className="flex items-center gap-6">
        <a href="/" className="transition-opacity hover:opacity-80">
          <PricePointLogo variant="compact" />
        </a>
      </div>

      {/* Centered search bar */}
      <div className="hidden flex-1 justify-center sm:flex">
        <SearchBar
          onSelect={handleSearchSelect}
          placeholder="Search address..."
          variant="landing"
        />
      </div>

      <div className="flex items-center gap-1">
        {/* Upload */}
        <Link
          to="/upload"
          aria-label="Upload listing data"
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
        </Link>

        {/* Saved listings */}
        <Link
          to="/saved"
          aria-label="Saved listings"
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z"
            />
          </svg>
        </Link>

        {/* Theme toggle */}
        <button
          type="button"
          aria-label="Toggle theme"
          onClick={toggleTheme}
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          {resolvedTheme === "dark" ? (
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"
              />
            </svg>
          ) : (
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
              />
            </svg>
          )}
        </button>

        {/* Notifications */}
        <button
          type="button"
          aria-label="Notifications"
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
            />
          </svg>
        </button>

        {/* User avatar menu */}
        {isAuthenticated ? (
          <div className="relative ml-1" ref={menuRef}>
            <button
              type="button"
              aria-label="User menu"
              aria-expanded={menuOpen}
              aria-haspopup="true"
              onClick={() => setMenuOpen((prev) => !prev)}
              data-testid="dashboard-user-menu-button"
            >
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[var(--color-db-accent)] to-[var(--color-db-cyan)] p-[2px]">
                <div className="flex h-full w-full items-center justify-center rounded-full bg-[var(--color-db-surface)]">
                  <span className="text-xs font-semibold text-[var(--color-db-text-primary)]">
                    {initials}
                  </span>
                </div>
              </div>
            </button>
            {menuOpen && (
              <div
                className="absolute right-0 top-full z-50 mt-1 w-48 overflow-hidden rounded-lg"
                style={{
                  backgroundColor: "var(--color-db-surface)",
                  border: "1px solid var(--color-db-border)",
                  boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
                }}
                role="menu"
                data-testid="dashboard-user-dropdown"
              >
                <div className="border-b border-[var(--color-db-border-subtle)] px-3 py-2">
                  <p className="truncate text-sm font-medium text-[var(--color-db-text-primary)]">
                    {user?.display_name || "User"}
                  </p>
                  <p className="truncate text-xs text-[var(--color-db-text-secondary)]">
                    {user?.email}
                  </p>
                </div>
                <Link
                  to="/settings"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-primary)]"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                  Settings
                </Link>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-primary)]"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9"
                    />
                  </svg>
                  Sign Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="ml-1 flex items-center gap-2">
            <Link
              to="/signin"
              className="rounded-[var(--radius-db-sm)] px-3 py-1.5 text-sm text-[var(--color-db-text-secondary)] transition-colors hover:text-[var(--color-db-text-primary)]"
            >
              Sign In
            </Link>
            <Link
              to="/signup"
              className="rounded-[var(--radius-db-sm)] bg-[var(--color-db-accent)] px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-db-accent-hover)]"
            >
              Sign Up
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}

export default DashboardNav;
