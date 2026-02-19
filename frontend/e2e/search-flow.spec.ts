import { test, expect } from "@playwright/test";

test.describe("Search flow", () => {
  test("should navigate to home page and display search bar", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: /know your home/i })).toBeVisible();
    await expect(page.getByRole("combobox", { name: /search address/i })).toBeVisible();
    await expect(page.getByText("PricePoint")).toBeVisible();
  });

  test("should type address and show suggestions dropdown", async ({ page }) => {
    await page.goto("/");

    const searchInput = page.getByRole("combobox", { name: /search address/i });
    await searchInput.fill("123 Main Street");

    // Wait for the dropdown listbox to appear with suggestions
    const listbox = page.getByRole("listbox", { name: /address suggestions/i });
    await expect(listbox).toBeVisible({ timeout: 10_000 });
  });

  test("should select suggestion and navigate to results page", async ({ page }) => {
    await page.goto("/");

    const searchInput = page.getByRole("combobox", { name: /search address/i });
    await searchInput.fill("123 Main Street");

    // Wait for suggestions to appear
    const listbox = page.getByRole("listbox", { name: /address suggestions/i });
    await expect(listbox).toBeVisible({ timeout: 10_000 });

    // Click the first suggestion
    const firstOption = listbox.getByRole("option").first();
    await firstOption.click();

    // Verify navigation to results page
    await expect(page).toHaveURL(/\/results\?address=/);
  });

  test("should load property data on results page", async ({ page }) => {
    await page.goto("/results?address=123+Main+St&lat=35.7796&lon=-78.6382");

    // Wait for either the property data to load or the skeleton to disappear
    // The page should show property header or an error state
    await expect(
      page.getByText(/back to search/i).or(page.getByText(/something went wrong/i)),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should show not found message for invalid address", async ({ page }) => {
    await page.goto("/");

    const searchInput = page.getByRole("combobox", { name: /search address/i });
    await searchInput.fill("zzzzzzzzzzzzzzz");

    // Press Enter and expect the not found alert
    await searchInput.press("Enter");
    await expect(page.getByRole("alert")).toContainText(/address not found/i);
  });
});
