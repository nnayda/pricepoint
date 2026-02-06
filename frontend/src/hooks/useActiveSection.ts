import { useEffect, useRef, useState } from "react";

export function useActiveSection(sectionIds: string[]): string {
  const [activeSection, setActiveSection] = useState<string>(sectionIds[0] ?? "");
  const idsRef = useRef(sectionIds);
  idsRef.current = sectionIds;

  useEffect(() => {
    const entries = new Map<string, IntersectionObserverEntry>();

    const observer = new IntersectionObserver(
      (observedEntries) => {
        for (const entry of observedEntries) {
          entries.set(entry.target.id, entry);
        }

        let maxRatio = 0;
        let mostVisible = "";
        for (const [id, entry] of entries) {
          if (entry.intersectionRatio > maxRatio) {
            maxRatio = entry.intersectionRatio;
            mostVisible = id;
          }
        }

        if (mostVisible) {
          setActiveSection(mostVisible);
        }
      },
      { rootMargin: "-10% 0px -10% 0px", threshold: [0, 0.25, 0.5, 0.75, 1] },
    );

    for (const id of idsRef.current) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [sectionIds]);

  return activeSection;
}
