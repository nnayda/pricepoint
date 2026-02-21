import type { ReactNode } from "react";

interface AppLayoutProps {
  children: ReactNode;
}

function AppLayout({ children }: AppLayoutProps) {
  // All pages use their own full layout shell (dark theme)
  return <>{children}</>;
}

export default AppLayout;
