import { useEffect, useState } from "react";

/**
 * Returns a value from 0 to 1 representing scroll progress over the
 * first `threshold` pixels of vertical scroll. Useful for gradually
 * fading in nav background opacity and shadow on scroll.
 */
export function useScrollProgress(threshold = 100): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    function handleScroll() {
      const y = window.scrollY;
      setProgress(Math.min(y / threshold, 1));
    }

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [threshold]);

  return progress;
}
