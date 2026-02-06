import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import NavBar from "../NavBar/NavBar";

interface AppLayoutProps {
  children: ReactNode;
}

function AppLayout({ children }: AppLayoutProps) {
  const { pathname } = useLocation();
  const showNav = pathname !== "/";

  return (
    <div className="flex min-h-screen flex-col bg-bg-main">
      {showNav && (
        <header className="sticky top-0 z-50 flex items-center justify-center px-4 py-3 sm:px-8 sm:py-4">
          <NavBar />
        </header>
      )}
      <main className="flex flex-1 flex-col px-4 py-4 sm:px-8 sm:py-6">{children}</main>
    </div>
  );
}

export default AppLayout;
