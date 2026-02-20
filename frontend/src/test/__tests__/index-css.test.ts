import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const css = readFileSync(resolve(__dirname, "../../index.css"), "utf-8");

describe("index.css design system", () => {
  describe("@font-face declarations", () => {
    const weights = [
      { weight: "400", file: "PlusJakartaSans-Regular.woff2" },
      { weight: "500", file: "PlusJakartaSans-Medium.woff2" },
      { weight: "600", file: "PlusJakartaSans-SemiBold.woff2" },
      { weight: "700", file: "PlusJakartaSans-Bold.woff2" },
    ];

    it.each(weights)("declares Plus Jakarta Sans weight $weight", ({ weight, file }) => {
      expect(css).toContain(`font-weight: ${weight}`);
      expect(css).toContain(file);
    });

    it("uses font-display: swap for all faces", () => {
      const swapCount = (css.match(/font-display:\s*swap/g) || []).length;
      // 4 Plus Jakarta Sans + 4 Inter + 3 JetBrains Mono = 11
      expect(swapCount).toBe(11);
    });

    it("uses woff2 format for all faces", () => {
      const formatCount = (css.match(/format\("woff2"\)/g) || []).length;
      // 4 Plus Jakarta Sans + 4 Inter + 3 JetBrains Mono = 11
      expect(formatCount).toBe(11);
    });
  });

  describe("@theme design tokens", () => {
    it("contains a @theme block", () => {
      expect(css).toContain("@theme");
    });

    it("sets --font-sans to Plus Jakarta Sans", () => {
      expect(css).toMatch(/--font-sans:.*"Plus Jakarta Sans"/);
    });

    describe("color tokens", () => {
      const colors = [
        ["--color-bg-main", "#f2f4f7"],
        ["--color-bg-card", "#ffffff"],
        ["--color-brand-blue", "#4f46e5"],
        ["--color-status-rented", "#ff5c8e"],
        ["--color-status-maint", "#47d1a0"],
        ["--color-status-vacant", "#c4c4c4"],
        ["--color-text-pri", "#1a1a1a"],
        ["--color-text-sec", "#71717a"],
      ];

      it.each(colors)("defines %s as %s", (token, value) => {
        expect(css).toContain(`${token}: ${value}`);
      });
    });

    describe("layout tokens", () => {
      it("defines --radius-lg as 32px", () => {
        expect(css).toContain("--radius-lg: 32px");
      });

      it("defines --radius-md as 20px", () => {
        expect(css).toContain("--radius-md: 20px");
      });

      it("defines --radius-pill as 9999px", () => {
        expect(css).toContain("--radius-pill: 9999px");
      });

      it("defines --shadow-soft", () => {
        expect(css).toContain("--shadow-soft:");
      });

      it("defines --shadow-card", () => {
        expect(css).toContain("--shadow-card:");
      });

      it("defines --spacing-grid as 24px", () => {
        expect(css).toContain("--spacing-grid: 24px");
      });
    });
  });

  describe("page cross-fade transition", () => {
    it("defines fade-in keyframes", () => {
      expect(css).toContain("@keyframes fade-in");
    });

    it("defines fade-out keyframes", () => {
      expect(css).toContain("@keyframes fade-out");
    });

    it("applies fade-out to ::view-transition-old(root)", () => {
      expect(css).toContain("::view-transition-old(root)");
      expect(css).toContain("animation: fade-out");
    });

    it("applies fade-in to ::view-transition-new(root)", () => {
      expect(css).toContain("::view-transition-new(root)");
      expect(css).toContain("animation: fade-in");
    });
  });

  describe("base layer styles", () => {
    it("includes a @layer base block", () => {
      expect(css).toContain("@layer base");
    });

    it("sets body font-family to var(--font-sans)", () => {
      expect(css).toContain("font-family: var(--font-sans)");
    });

    it("sets body background to var(--color-bg-main)", () => {
      expect(css).toContain("background-color: var(--color-bg-main)");
    });

    it("sets body color to var(--color-text-pri)", () => {
      expect(css).toContain("color: var(--color-text-pri)");
    });

    it("enables smooth scrolling", () => {
      expect(css).toContain("scroll-behavior: smooth");
    });

    it("enables font antialiasing", () => {
      expect(css).toContain("-webkit-font-smoothing: antialiased");
    });
  });
});
