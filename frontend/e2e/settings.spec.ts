import { test, expect } from "@playwright/test";

test.describe("Settings persistence", () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test for a clean state
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
  });

  test("should display settings page with POI preferences and mortgage defaults", async ({
    page,
  }) => {
    await page.goto("/settings");

    await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible();
    await expect(page.getByRole("region", { name: /poi preferences/i })).toBeVisible();
    await expect(page.getByRole("region", { name: /mortgage defaults/i })).toBeVisible();
  });

  test("should toggle a POI preference switch", async ({ page }) => {
    await page.goto("/settings");

    // Find the first POI toggle switch
    const poiSection = page.getByRole("region", { name: /poi preferences/i });
    const firstSwitch = poiSection.getByRole("switch").first();

    // Get initial state
    const initialChecked = await firstSwitch.getAttribute("aria-checked");

    // Toggle it
    await firstSwitch.click();

    // Verify state changed
    const newChecked = await firstSwitch.getAttribute("aria-checked");
    expect(newChecked).not.toBe(initialChecked);
  });

  test("should persist POI preferences after navigation", async ({ page }) => {
    await page.goto("/settings");

    const poiSection = page.getByRole("region", { name: /poi preferences/i });
    const firstSwitch = poiSection.getByRole("switch").first();

    // Get initial state and toggle
    const initialChecked = await firstSwitch.getAttribute("aria-checked");
    await firstSwitch.click();
    const toggledState = await firstSwitch.getAttribute("aria-checked");
    expect(toggledState).not.toBe(initialChecked);

    // Navigate away to home page
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /know your home/i })).toBeVisible();

    // Navigate back to settings
    await page.goto("/settings");

    // Verify the preference was persisted
    const persistedState = await poiSection.getByRole("switch").first().getAttribute("aria-checked");
    expect(persistedState).toBe(toggledState);
  });

  test("should update mortgage default values", async ({ page }) => {
    await page.goto("/settings");

    const mortgageSection = page.getByRole("region", { name: /mortgage defaults/i });
    const downPaymentInput = mortgageSection.getByLabel(/down payment/i);

    await downPaymentInput.fill("25");
    expect(await downPaymentInput.inputValue()).toBe("25");
  });

  test("should persist mortgage defaults after navigation", async ({ page }) => {
    await page.goto("/settings");

    const mortgageSection = page.getByRole("region", { name: /mortgage defaults/i });
    const downPaymentInput = mortgageSection.getByLabel(/down payment/i);

    // Set a custom down payment
    await downPaymentInput.fill("25");

    // Navigate away
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /know your home/i })).toBeVisible();

    // Navigate back
    await page.goto("/settings");

    // Verify persistence
    const persistedValue = await page
      .getByRole("region", { name: /mortgage defaults/i })
      .getByLabel(/down payment/i)
      .inputValue();
    expect(persistedValue).toBe("25");
  });

  test("should add a custom POI", async ({ page }) => {
    await page.goto("/settings");

    const poiSection = page.getByRole("region", { name: /poi preferences/i });

    // Fill in a custom POI name
    await poiSection.getByLabel(/name/i).fill("Trader Joe's");
    await poiSection.getByRole("button", { name: /add/i }).click();

    // Verify the custom POI appears
    await expect(poiSection.getByText("Trader Joe's")).toBeVisible();
  });
});
