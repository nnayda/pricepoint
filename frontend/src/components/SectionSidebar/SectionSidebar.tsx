import { useActiveSection } from "../../hooks/useActiveSection";

interface SidebarSection {
  id: string;
  icon: string;
  tooltip: string;
}

interface SectionSidebarProps {
  sections: SidebarSection[];
}

function SectionSidebar({ sections }: SectionSidebarProps) {
  const sectionIds = sections.map((s) => s.id);
  const activeSection = useActiveSection(sectionIds);

  const linkClasses = (sectionId: string) =>
    `flex h-9 w-9 items-center justify-center rounded-md text-sm transition-colors flex-shrink-0 ${
      activeSection === sectionId
        ? "bg-brand-blue text-white"
        : "text-text-sec hover:bg-bg-main hover:text-text-pri"
    }`;

  return (
    <>
      {/* Desktop: vertical sidebar */}
      <nav
        className="fixed left-2 top-1/2 z-40 hidden -translate-y-1/2 flex-col gap-2 rounded-lg bg-bg-card/80 p-2 shadow-soft backdrop-blur-md lg:flex"
        aria-label="Page sections"
      >
        {sections.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            aria-label={s.tooltip}
            title={s.tooltip}
            className={linkClasses(s.id)}
          >
            {s.icon}
          </a>
        ))}
      </nav>
      {/* Mobile: fixed bottom navigation bar */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-40 flex overflow-x-auto border-t border-bg-main bg-bg-card/90 px-2 py-1.5 shadow-soft backdrop-blur-md lg:hidden"
        aria-label="Page sections mobile"
        data-testid="mobile-section-bar"
      >
        {sections.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            aria-label={s.tooltip}
            title={s.tooltip}
            className={linkClasses(s.id)}
          >
            {s.icon}
          </a>
        ))}
      </nav>
    </>
  );
}

export default SectionSidebar;
