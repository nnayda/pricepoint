import type { ReactNode } from "react";
import NavBar from "../NavBar/NavBar";

interface AppLayoutProps {
  children: ReactNode;
}

function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center gap-6 px-8 py-4">
        <h1 className="text-xl font-bold text-text-pri">PricePoint</h1>
        <NavBar />
      </header>
      <main className="flex-1 px-8 py-4">{children}</main>
    </div>
  );
}

export default AppLayout;
