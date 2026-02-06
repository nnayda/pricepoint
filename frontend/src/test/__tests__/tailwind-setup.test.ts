import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

describe("Tailwind CSS setup", () => {
  it("index.css imports tailwindcss", () => {
    const css = readFileSync(
      resolve(__dirname, "../../index.css"),
      "utf-8",
    );
    expect(css).toContain('@import "tailwindcss"');
  });

  it("vite.config.ts includes @tailwindcss/vite plugin", () => {
    const config = readFileSync(
      resolve(__dirname, "../../../vite.config.ts"),
      "utf-8",
    );
    expect(config).toContain('@tailwindcss/vite');
    expect(config).toMatch(/tailwindcss\(\)/);
  });

  it("main.tsx imports index.css", () => {
    const main = readFileSync(
      resolve(__dirname, "../../main.tsx"),
      "utf-8",
    );
    expect(main).toContain('./index.css');
  });
});
