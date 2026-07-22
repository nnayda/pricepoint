import { test, expect } from "@playwright/test";

test.describe("Map interactions", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/results?address=123+Main+St&lat=35.7796&lon=-78.6382");

    // Wait for the page to settle — either property map or error state
    await expect(
      page
        .getByRole("region", { name: /property map/i })
        .or(page.getByText(/something went wrong/i)),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should display map tab bar with all layer tabs", async ({ page }) => {
    const tablist = page.getByRole("tablist", { name: /map layers/i });
    await expect(tablist).toBeVisible();

    // Verify all tabs exist
    await expect(page.getByRole("tab", { name: /crime density|density/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /crime incidents|incidents/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /points of interest|pois/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /greenspace|green/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /utilities|utils/i })).toBeVisible();
  });

  test("should switch to POIs tab when clicked", async ({ page }) => {
    const poisTab = page.getByRole("tab", { name: /points of interest|pois/i });
    await poisTab.click();

    await expect(poisTab).toHaveAttribute("aria-selected", "true");

    // The crime density tab should no longer be selected
    const crimeTab = page.getByRole("tab", { name: /crime density|density/i });
    await expect(crimeTab).toHaveAttribute("aria-selected", "false");
  });

  test("should switch to Greenspace tab and show panel", async ({ page }) => {
    const greenTab = page.getByRole("tab", { name: /greenspace|green/i });
    await greenTab.click();

    await expect(greenTab).toHaveAttribute("aria-selected", "true");

    // Verify the tab panel for greenspace is visible
    const panel = page.locator('[id="map-panel-greenspace"]');
    await expect(panel).toBeVisible();
  });

  test("should switch to Utilities tab and show panel", async ({ page }) => {
    const utilsTab = page.getByRole("tab", { name: /utilities|utils/i });
    await utilsTab.click();

    await expect(utilsTab).toHaveAttribute("aria-selected", "true");

    const panel = page.locator('[id="map-panel-utilities"]');
    await expect(panel).toBeVisible();
  });

  test("should have radius selector", async ({ page }) => {
    const radiusSelect = page.getByRole("combobox", { name: /search radius/i });
    await expect(radiusSelect).toBeVisible();
  });

  test("should show crime date range filter on crime tab", async ({ page }) => {
    // Crime density is the default tab, so date range should be visible
    const dateSelect = page.getByRole("combobox", { name: /crime date range/i });
    await expect(dateSelect).toBeVisible();
  });
});
