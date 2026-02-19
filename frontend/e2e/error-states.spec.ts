import { test, expect } from "@playwright/test";

test.describe("Error states", () => {
  test("should display 404 page for non-existent route", async ({ page }) => {
    await page.goto("/this-page-does-not-exist");

    await expect(page.getByRole("heading", { name: /404/i })).toBeVisible();
    await expect(page.getByText(/page not found/i)).toBeVisible();
    await expect(page.getByText(/does not exist or has been moved/i)).toBeVisible();
  });

  test("should show Back to Home link on 404 page", async ({ page }) => {
    await page.goto("/nonexistent-route");

    const backLink = page.getByRole("link", { name: /back to home/i });
    await expect(backLink).toBeVisible();
    await expect(backLink).toHaveAttribute("href", "/");
  });

  test("should navigate back to home from 404 page", async ({ page }) => {
    await page.goto("/some/random/route");

    await expect(page.getByRole("heading", { name: /404/i })).toBeVisible();

    // Click the back to home link
    await page.getByRole("link", { name: /back to home/i }).click();

    // Should be on the home page
    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { name: /know your home/i })).toBeVisible();
  });

  test("should show no address state on results page without query params", async ({ page }) => {
    await page.goto("/results");

    await expect(page.getByText(/no address provided/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /go to search/i })).toBeVisible();
  });

  test("should navigate from empty results back to search", async ({ page }) => {
    await page.goto("/results");

    await page.getByRole("link", { name: /go to search/i }).click();

    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { name: /know your home/i })).toBeVisible();
  });
});
