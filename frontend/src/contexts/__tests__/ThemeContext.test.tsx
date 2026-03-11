import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider, useTheme } from "../ThemeContext";

function TestConsumer() {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button data-testid="set-light" onClick={() => setTheme("light")}>
        Set Light
      </button>
      <button data-testid="set-dark" onClick={() => setTheme("dark")}>
        Set Dark
      </button>
      <button data-testid="set-system" onClick={() => setTheme("system")}>
        Set System
      </button>
      <button data-testid="toggle" onClick={toggleTheme}>
        Toggle
      </button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <ThemeProvider>
      <TestConsumer />
    </ThemeProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-color-scheme: dark)",
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

describe("ThemeContext", () => {
  it("defaults to system when nothing stored", () => {
    renderWithProvider();
    expect(screen.getByTestId("theme").textContent).toBe("system");
  });

  it("resolves system to dark when prefers-color-scheme is dark", () => {
    renderWithProvider();
    expect(screen.getByTestId("resolved").textContent).toBe("dark");
  });

  it("reads stored preference from localStorage", () => {
    localStorage.setItem("pricepoint-theme", "light");
    renderWithProvider();
    expect(screen.getByTestId("theme").textContent).toBe("light");
    expect(screen.getByTestId("resolved").textContent).toBe("light");
  });

  it("persists theme to localStorage on change", async () => {
    const user = userEvent.setup();
    renderWithProvider();
    await user.click(screen.getByTestId("set-light"));
    expect(localStorage.getItem("pricepoint-theme")).toBe("light");
  });

  it("sets data-theme attribute on html element", () => {
    localStorage.setItem("pricepoint-theme", "light");
    renderWithProvider();
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("toggleTheme switches between light and dark based on resolved theme", async () => {
    localStorage.setItem("pricepoint-theme", "dark");
    const user = userEvent.setup();
    renderWithProvider();
    expect(screen.getByTestId("theme").textContent).toBe("dark");

    await user.click(screen.getByTestId("toggle"));
    expect(screen.getByTestId("theme").textContent).toBe("light");
    expect(screen.getByTestId("resolved").textContent).toBe("light");

    await user.click(screen.getByTestId("toggle"));
    expect(screen.getByTestId("theme").textContent).toBe("dark");
    expect(screen.getByTestId("resolved").textContent).toBe("dark");
  });

  it("toggleTheme from system (dark) goes directly to light", async () => {
    // system resolves to dark (matchMedia mock), so toggle should go to light
    const user = userEvent.setup();
    renderWithProvider();
    expect(screen.getByTestId("theme").textContent).toBe("system");
    expect(screen.getByTestId("resolved").textContent).toBe("dark");

    await user.click(screen.getByTestId("toggle"));
    expect(screen.getByTestId("theme").textContent).toBe("light");
    expect(screen.getByTestId("resolved").textContent).toBe("light");
  });

  it("setTheme allows setting any valid preference", async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await user.click(screen.getByTestId("set-dark"));
    expect(screen.getByTestId("theme").textContent).toBe("dark");
    expect(screen.getByTestId("resolved").textContent).toBe("dark");

    await user.click(screen.getByTestId("set-light"));
    expect(screen.getByTestId("theme").textContent).toBe("light");
    expect(screen.getByTestId("resolved").textContent).toBe("light");
  });

  it("throws when useTheme is called outside ThemeProvider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow("useTheme must be used within a ThemeProvider");
    spy.mockRestore();
  });

  it("resolves system to light when prefers-color-scheme is light", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query === "(prefers-color-scheme: light)",
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    renderWithProvider();
    expect(screen.getByTestId("resolved").textContent).toBe("light");
  });
});
