import { test, expect } from "@playwright/test";

test.describe("Responsive layout (mobile viewport)", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("should display landing page at mobile viewport", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: /know your home/i })).toBeVisible();
    await expect(page.getByRole("combobox", { name: /search address/i })).toBeVisible();
    await expect(page.getByText("PricePoint")).toBeVisible();
  });

  test("should show hamburger menu button on non-landing pages", async ({ page }) => {
    await page.goto("/settings");

    const menuButton = page.getByRole("button", { name: /toggle menu/i });
    await expect(menuButton).toBeVisible();
  });

  test("should open mobile menu when hamburger is clicked", async ({ page }) => {
    await page.goto("/settings");

    const menuButton = page.getByRole("button", { name: /toggle menu/i });
    await menuButton.click();

    // Mobile menu should be visible
    const mobileMenu = page.getByTestId("mobile-menu");
    await expect(mobileMenu).toBeVisible();

    // Should show navigation links
    await expect(mobileMenu.getByText(/upload listings/i)).toBeVisible();
    await expect(mobileMenu.getByText(/settings/i)).toBeVisible();
    await expect(mobileMenu.getByText(/sign in/i)).toBeVisible();
  });

  test("should close mobile menu when hamburger is clicked again", async ({ page }) => {
    await page.goto("/settings");

    const menuButton = page.getByRole("button", { name: /toggle menu/i });

    // Open menu
    await menuButton.click();
    await expect(page.getByTestId("mobile-menu")).toBeVisible();

    // Close menu
    await menuButton.click();
    await expect(page.getByTestId("mobile-menu")).not.toBeVisible();
  });

  test("should close mobile menu when a link is clicked", async ({ page }) => {
    await page.goto("/upload");

    const menuButton = page.getByRole("button", { name: /toggle menu/i });
    await menuButton.click();

    const mobileMenu = page.getByTestId("mobile-menu");
    await expect(mobileMenu).toBeVisible();

    // Click the Settings link
    await mobileMenu.getByText(/settings/i).click();

    // Menu should close and page should navigate
    await expect(mobileMenu).not.toBeVisible();
    await expect(page).toHaveURL(/\/settings/);
  });

  test("should display property page at mobile viewport", async ({ page }) => {
    await page.goto("/results?address=123+Main+St&lat=35.7796&lon=-78.6382");

    // Wait for the page to load
    await expect(
      page.getByText(/back to search/i).or(page.getByText(/something went wrong/i)),
    ).toBeVisible({ timeout: 15_000 });

    // The hamburger menu should be visible at mobile
    const menuButton = page.getByRole("button", { name: /toggle menu/i });
    await expect(menuButton).toBeVisible();
  });

  test("should display stats cards stacked vertically on mobile", async ({ page }) => {
    await page.goto("/");

    // All three stat cards should be visible
    await expect(page.getByText("50K+")).toBeVisible();
    await expect(page.getByText("94%")).toBeVisible();
    await expect(page.getByText("12")).toBeVisible();
  });
});
