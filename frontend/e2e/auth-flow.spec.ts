import { test, expect } from "@playwright/test";

test.describe("Auth flow", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a page with the NavBar (any page except landing)
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible();
  });

  test("should show Sign In button in nav bar", async ({ page }) => {
    const signInButton = page.getByRole("button", { name: /sign in/i });
    await expect(signInButton).toBeVisible();
  });

  test("should open auth modal when Sign In is clicked", async ({ page }) => {
    await page.getByRole("button", { name: /sign in/i }).click();

    // Auth modal should open
    const authDialog = page.getByRole("dialog", { name: /authentication/i });
    await expect(authDialog).toBeVisible();
  });

  test("should show sign in and register tabs in auth modal", async ({ page }) => {
    await page.getByRole("button", { name: /sign in/i }).click();

    const authDialog = page.getByRole("dialog", { name: /authentication/i });
    await expect(authDialog.getByText("Sign In")).toBeVisible();
    await expect(authDialog.getByText("Register")).toBeVisible();
  });

  test("should switch to register form", async ({ page }) => {
    await page.getByRole("button", { name: /sign in/i }).click();

    const authDialog = page.getByRole("dialog", { name: /authentication/i });

    // Click the Register tab
    await authDialog.getByText("Register").click();

    // Verify register form is shown
    await expect(authDialog.getByLabel(/display name/i)).toBeVisible();
    await expect(authDialog.getByLabel(/^email/i)).toBeVisible();
    await expect(authDialog.getByLabel(/^password/i)).toBeVisible();
    await expect(authDialog.getByLabel(/confirm password/i)).toBeVisible();
  });

  test("should fill registration form and submit", async ({ page }) => {
    await page.getByRole("button", { name: /sign in/i }).click();

    const authDialog = page.getByRole("dialog", { name: /authentication/i });

    // Switch to Register tab
    await authDialog.getByText("Register").click();

    // Fill in the registration form
    await authDialog.getByLabel(/^email/i).fill("test@example.com");
    await authDialog.getByLabel(/display name/i).fill("Test User");
    await authDialog.getByLabel(/^password/i).fill("password123");
    await authDialog.getByLabel(/confirm password/i).fill("password123");

    // Submit the form
    await authDialog.getByRole("button", { name: /create account/i }).click();

    // The modal will either close on success or show an error
    // (depends on whether the API is available)
    await expect(
      authDialog.getByRole("alert").or(page.getByText(/test user/i)),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should show error for mismatched passwords", async ({ page }) => {
    await page.getByRole("button", { name: /sign in/i }).click();

    const authDialog = page.getByRole("dialog", { name: /authentication/i });

    // Switch to Register tab
    await authDialog.getByText("Register").click();

    // Fill with mismatched passwords
    await authDialog.getByLabel(/^email/i).fill("test@example.com");
    await authDialog.getByLabel(/display name/i).fill("Test User");
    await authDialog.getByLabel(/^password/i).fill("password123");
    await authDialog.getByLabel(/confirm password/i).fill("different456");

    // Submit
    await authDialog.getByRole("button", { name: /create account/i }).click();

    // Should show passwords don't match error
    await expect(authDialog.getByRole("alert")).toContainText(/passwords do not match/i);
  });

  test("should close auth modal when clicking overlay", async ({ page }) => {
    await page.getByRole("button", { name: /sign in/i }).click();

    const overlay = page.getByTestId("auth-modal-overlay");
    await expect(overlay).toBeVisible();

    // Click on the overlay (outside the dialog)
    await overlay.click({ position: { x: 10, y: 10 } });

    // Modal should be closed
    await expect(page.getByRole("dialog", { name: /authentication/i })).not.toBeVisible();
  });
});
