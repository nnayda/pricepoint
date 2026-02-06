import type { ReactNode } from "react";
import NavBar from "../NavBar/NavBar";

interface AppLayoutProps {
  children: ReactNode;
}

function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-bg-main">
      <header className="sticky top-0 z-50 flex items-center justify-center px-8 py-4">
        <NavBar />
      </header>
      <main className="flex flex-1 flex-col px-8 py-6">{children}</main>
    </div>
  );
}

export default AppLayout;
