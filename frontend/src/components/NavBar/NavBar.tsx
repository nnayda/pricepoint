import { Link, useLocation } from "react-router-dom";

interface NavItem {
  label: string;
  to: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Home", to: "/" },
  { label: "Dashboard", to: "/dashboard" },
  { label: "Forecast", to: "/forecast" },
];

function NavBar() {
  const { pathname } = useLocation();

  return (
    <nav
      aria-label="Main navigation"
      className="flex items-center gap-1 rounded-pill bg-bg-card/80 px-2 py-1.5 shadow-card backdrop-blur-md"
    >
      {NAV_ITEMS.map(({ label, to }) => {
        const isActive = to === "/" ? pathname === "/" : pathname.startsWith(to);

        return (
          <Link
            key={to}
            to={to}
            aria-current={isActive ? "page" : undefined}
            className={`rounded-pill px-4 py-1.5 text-sm font-semibold transition-colors ${
              isActive ? "bg-brand-blue text-white" : "text-text-sec hover:text-text-pri"
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export default NavBar;
