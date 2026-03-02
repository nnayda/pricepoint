import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import SearchBar from "../SearchBar/SearchBar";
import { startViewTransition } from "../../utils/viewTransition";
import { useScrollProgress } from "../../hooks/useScrollProgress";
import { useAuth } from "../../contexts/AuthContext";
import type { GeocodeResult } from "../../types";

function NavBar() {
  const navigate = useNavigate();
  const scrollProgress = useScrollProgress(100);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const userMenuRef = useRef<HTMLDivElement>(null);

  function handleSelect(result: GeocodeResult) {
    startViewTransition(() => {
      navigate(`/property/${encodeURIComponent(result.display_name)}`);
    });
  }

  function handleLogout() {
    logout();
    setUserMenuOpen(false);
    setMobileMenuOpen(false);
    navigate("/");
  }

  // Close user menu on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    if (userMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [userMenuOpen]);

  // Background opacity: 40% at top → 95% fully scrolled
  const bgOpacity = 0.4 + scrollProgress * 0.55;
  // Shadow opacity: 0% at top → 5% fully scrolled (matches --shadow-card)
  const shadowOpacity = scrollProgress * 0.05;

  const initials = user?.display_name
    ? user.display_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : (user?.email?.charAt(0).toUpperCase() ?? "U");

  return (
    <div className="relative">
      <nav
        aria-label="Main navigation"
        className="flex items-center gap-2 rounded-pill px-3 py-1.5 backdrop-blur-md transition-shadow duration-200 sm:gap-4 sm:px-6"
        style={{
          backgroundColor: `rgba(255, 255, 255, ${bgOpacity})`,
          boxShadow: `0px 10px 30px rgba(0, 0, 0, ${shadowOpacity})`,
        }}
      >
        <Link
          to="/"
          className="whitespace-nowrap text-base font-bold tracking-tight text-text-pri transition-colors hover:text-brand-blue sm:text-lg"
        >
          PricePoint
        </Link>
        <SearchBar onSelect={handleSelect} placeholder="Search address..." />
        {/* Desktop auth */}
        {isAuthenticated ? (
          <div className="relative hidden sm:block" ref={userMenuRef}>
            <button
              type="button"
              onClick={() => setUserMenuOpen((prev) => !prev)}
              aria-expanded={userMenuOpen}
              aria-haspopup="true"
              className="flex items-center gap-2 rounded-full px-1 py-1 transition-colors hover:bg-black/5"
              data-testid="user-menu-button"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-blue text-xs font-semibold text-white">
                {initials}
              </div>
              <span className="max-w-[120px] truncate text-sm text-text-sec">
                {user?.display_name || user?.email}
              </span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className={`h-4 w-4 text-text-sec transition-transform ${userMenuOpen ? "rotate-180" : ""}`}
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
            {userMenuOpen && (
              <div
                className="absolute right-0 top-full z-50 mt-1 w-48 rounded-lg bg-bg-card py-1 shadow-soft"
                role="menu"
                data-testid="user-dropdown"
              >
                <div className="border-b border-black/5 px-3 py-2">
                  <p className="truncate text-sm font-medium text-text-pri">
                    {user?.display_name || "User"}
                  </p>
                  <p className="truncate text-xs text-text-sec">{user?.email}</p>
                </div>
                <Link
                  to="/settings"
                  role="menuitem"
                  onClick={() => setUserMenuOpen(false)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Settings
                </Link>
                <Link
                  to="/upload"
                  role="menuitem"
                  onClick={() => setUserMenuOpen(false)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Upload
                </Link>
                <Link
                  to="/saved"
                  role="menuitem"
                  onClick={() => setUserMenuOpen(false)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5 2a2 2 0 00-2 2v14l7-3.5L17 18V4a2 2 0 00-2-2H5z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Saved
                </Link>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Sign Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="hidden items-center gap-2 sm:flex">
            <Link
              to="/signin"
              className="rounded-lg px-3 py-1 text-sm text-text-sec transition-colors hover:text-brand-blue"
            >
              Sign In
            </Link>
            <Link
              to="/signup"
              className="rounded-lg bg-brand-blue px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              Sign Up
            </Link>
          </div>
        )}
        {/* Mobile hamburger button */}
        <button
          type="button"
          aria-label="Toggle menu"
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          className="ml-auto shrink-0 text-text-sec transition-colors hover:text-brand-blue sm:hidden"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            {mobileMenuOpen ? (
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            ) : (
              <path
                fillRule="evenodd"
                d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
                clipRule="evenodd"
              />
            )}
          </svg>
        </button>
      </nav>
      {/* Mobile dropdown menu */}
      {mobileMenuOpen && (
        <div
          className="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg bg-bg-card p-3 shadow-soft sm:hidden"
          data-testid="mobile-menu"
        >
          <div className="flex flex-col gap-1">
            {isAuthenticated ? (
              <>
                <div className="border-b border-black/5 px-3 py-2">
                  <p className="truncate text-sm font-medium text-text-pri">
                    {user?.display_name || "User"}
                  </p>
                  <p className="truncate text-xs text-text-sec">{user?.email}</p>
                </div>
                <Link
                  to="/settings"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  Settings
                </Link>
                <Link
                  to="/upload"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  Upload
                </Link>
                <Link
                  to="/saved"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  Saved
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/signin"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default NavBar;
