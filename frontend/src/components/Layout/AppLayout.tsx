import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface AppLayoutProps {
  children: ReactNode;
}

function AppLayout({ children }: AppLayoutProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <header
        style={{
          padding: "1rem 2rem",
          borderBottom: "1px solid #e0e0e0",
          display: "flex",
          gap: "2rem",
          alignItems: "center",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Home Value Forecast</h1>
        <nav style={{ display: "flex", gap: "1rem" }}>
          <Link to="/">Dashboard</Link>
          <Link to="/forecast">Forecast</Link>
        </nav>
      </header>
      <main style={{ flex: 1, padding: "1rem 2rem" }}>{children}</main>
    </div>
  );
}

export default AppLayout;
