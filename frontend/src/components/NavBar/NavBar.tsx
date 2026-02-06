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
    </nav>
  );
}

export default NavBar;
