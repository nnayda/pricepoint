import { Link, useNavigate } from "react-router-dom";
import SearchBar from "../SearchBar/SearchBar";
import { startViewTransition } from "../../utils/viewTransition";
import type { GeocodeResult } from "../../types";

function NavBar() {
  const navigate = useNavigate();

  function handleSelect(result: GeocodeResult) {
    const url = `/results?address=${encodeURIComponent(result.display_name)}&lat=${result.lat}&lon=${result.lon}`;
    startViewTransition(() => {
      navigate(url);
    });
  }

  return (
    <nav
      aria-label="Main navigation"
      className="flex items-center gap-2 rounded-pill bg-bg-card/80 px-3 py-1.5 shadow-card backdrop-blur-md sm:gap-4 sm:px-6"
    >
      <Link
        to="/"
        className="whitespace-nowrap text-lg font-bold tracking-tight text-text-pri transition-colors hover:text-brand-blue"
      >
        PricePoint
      </Link>
      <SearchBar onSelect={handleSelect} placeholder="Search address..." />
    </nav>
  );
}

export default NavBar;
