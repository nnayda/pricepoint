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

  return (
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
          className={`flex h-9 w-9 items-center justify-center rounded-md text-sm transition-colors ${
            activeSection === s.id
              ? "bg-brand-blue text-white"
              : "text-text-sec hover:bg-bg-main hover:text-text-pri"
          }`}
        >
          {s.icon}
        </a>
      ))}
    </nav>
  );
}

export default SectionSidebar;
