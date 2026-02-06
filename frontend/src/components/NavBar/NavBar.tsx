import { Link, useNavigate } from "react-router-dom";
import SearchBar from "../SearchBar/SearchBar";
import { startViewTransition } from "../../utils/viewTransition";
import { useScrollProgress } from "../../hooks/useScrollProgress";
import type { GeocodeResult } from "../../types";

function NavBar() {
  const navigate = useNavigate();
  const scrollProgress = useScrollProgress(100);

  function handleSelect(result: GeocodeResult) {
    const url = `/results?address=${encodeURIComponent(result.display_name)}&lat=${result.lat}&lon=${result.lon}`;
    startViewTransition(() => {
      navigate(url);
    });
  }

  // Background opacity: 40% at top → 95% fully scrolled
  const bgOpacity = 0.4 + scrollProgress * 0.55;
  // Shadow opacity: 0% at top → 5% fully scrolled (matches --shadow-card)
  const shadowOpacity = scrollProgress * 0.05;

  return (
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
      <Link
        to="/settings"
        aria-label="Settings"
        className="ml-auto shrink-0 text-text-sec transition-colors hover:text-brand-blue"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
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
      </Link>
    </nav>
  );
}

export default NavBar;
