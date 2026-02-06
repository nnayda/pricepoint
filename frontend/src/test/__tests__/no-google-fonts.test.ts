import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "fs";
import { resolve, extname } from "path";

const GOOGLE_FONTS_PATTERNS = [/fonts\.googleapis\.com/, /fonts\.gstatic\.com/];

const ROOT = resolve(__dirname, "../../..");
const SRC = resolve(__dirname, "../..");

function collectFiles(dir: string, exts: string[]): string[] {
  const results: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = resolve(dir, entry.name);
    if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== "dist") {
      results.push(...collectFiles(full, exts));
    } else if (entry.isFile() && exts.includes(extname(entry.name))) {
      results.push(full);
    }
  }
  return results;
}

describe("no Google Fonts requests", () => {
  it("index.html does not reference Google Fonts", () => {
    const html = readFileSync(resolve(ROOT, "index.html"), "utf-8");
    for (const pattern of GOOGLE_FONTS_PATTERNS) {
      expect(html).not.toMatch(pattern);
    }
  });

  it("index.css does not import Google Fonts", () => {
    const css = readFileSync(resolve(SRC, "index.css"), "utf-8");
    for (const pattern of GOOGLE_FONTS_PATTERNS) {
      expect(css).not.toMatch(pattern);
    }
  });

  it("no source files reference Google Fonts", () => {
    const files = collectFiles(SRC, [".ts", ".tsx", ".css", ".js", ".jsx"]);
    for (const file of files) {
      const content = readFileSync(file, "utf-8");
      for (const pattern of GOOGLE_FONTS_PATTERNS) {
        expect(content, `${file} should not reference Google Fonts`).not.toMatch(pattern);
      }
    }
  });

  it("all @font-face declarations use local woff2 files", () => {
    const css = readFileSync(resolve(SRC, "index.css"), "utf-8");
    const fontFaceBlocks = css.match(/@font-face\s*\{[^}]+\}/g) ?? [];
    expect(fontFaceBlocks.length).toBeGreaterThan(0);
    for (const block of fontFaceBlocks) {
      expect(block).toMatch(/src:\s*url\("\.\/assets\/fonts\//);
      expect(block).toContain('format("woff2")');
    }
  });
});
