import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import SearchBar from "../SearchBar/SearchBar";
import AuthModal from "../AuthModal/AuthModal";
import { startViewTransition } from "../../utils/viewTransition";
import { useScrollProgress } from "../../hooks/useScrollProgress";
import { useAuth } from "../../contexts/AuthContext";
import type { GeocodeResult } from "../../types";

function NavBar() {
  const navigate = useNavigate();
  const scrollProgress = useScrollProgress(100);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();

  function handleSelect(result: GeocodeResult) {
    startViewTransition(() => {
      navigate(`/property/${encodeURIComponent(result.display_name)}`);
    });
  }

  // Background opacity: 40% at top → 95% fully scrolled
  const bgOpacity = 0.4 + scrollProgress * 0.55;
  // Shadow opacity: 0% at top → 5% fully scrolled (matches --shadow-card)
  const shadowOpacity = scrollProgress * 0.05;

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
          <div className="hidden items-center gap-2 sm:flex">
            <span className="text-sm text-text-sec">{user?.display_name}</span>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg px-3 py-1 text-sm text-text-sec transition-colors hover:text-brand-blue"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setAuthModalOpen(true)}
            className="hidden rounded-lg bg-brand-blue px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-blue-700 sm:block"
          >
            Sign In
          </button>
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
          <div className="flex flex-col gap-2">
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => {
                  logout();
                  setMobileMenuOpen(false);
                }}
                className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
              >
                Sign Out ({user?.display_name})
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setAuthModalOpen(true);
                  setMobileMenuOpen(false);
                }}
                className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-text-sec transition-colors hover:bg-bg-main hover:text-text-pri"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      )}
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
    </div>
  );
}

export default NavBar;
