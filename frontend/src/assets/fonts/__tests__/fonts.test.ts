import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const FONTS_DIR = resolve(__dirname, "..");

const FONT_FILES = [
  { name: "PlusJakartaSans-Regular.woff2", weight: 400 },
  { name: "PlusJakartaSans-Medium.woff2", weight: 500 },
  { name: "PlusJakartaSans-SemiBold.woff2", weight: 600 },
  { name: "PlusJakartaSans-Bold.woff2", weight: 700 },
];

describe("Plus Jakarta Sans font files", () => {
  it.each(FONT_FILES)("$name exists", ({ name }) => {
    const fontPath = resolve(FONTS_DIR, name);
    expect(existsSync(fontPath)).toBe(true);
  });

  it.each(FONT_FILES)("$name is a valid woff2 file", ({ name }) => {
    const fontPath = resolve(FONTS_DIR, name);
    const buffer = readFileSync(fontPath);
    // wOF2 magic bytes
    const magic = buffer.toString("ascii", 0, 4);
    expect(magic).toBe("wOF2");
  });

  it.each(FONT_FILES)("$name has non-trivial file size", ({ name }) => {
    const fontPath = resolve(FONTS_DIR, name);
    const buffer = readFileSync(fontPath);
    expect(buffer.length).toBeGreaterThan(1000);
  });
});
