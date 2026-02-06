import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

describe("index.html", () => {
  it("has PricePoint as the page title", () => {
    const html = readFileSync(resolve(__dirname, "../../../index.html"), "utf-8");
    expect(html).toContain("<title>PricePoint</title>");
  });
});
