import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SectionHeading from "../SectionHeading";

describe("SectionHeading", () => {
  it("renders as h3 by default", () => {
    render(<SectionHeading>Title</SectionHeading>);
    const heading = screen.getByRole("heading", { level: 3 });
    expect(heading).toHaveTextContent("Title");
  });

  it("renders as h2 when specified", () => {
    render(<SectionHeading as="h2">Title</SectionHeading>);
    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
  });

  it("renders as h4 when specified", () => {
    render(<SectionHeading as="h4">Title</SectionHeading>);
    expect(screen.getByRole("heading", { level: 4 })).toBeInTheDocument();
  });

  it("applies default variant styles", () => {
    render(<SectionHeading>Default</SectionHeading>);
    const heading = screen.getByRole("heading");
    expect(heading.className).toContain("text-sm");
    expect(heading.className).toContain("font-semibold");
  });

  it("applies uppercase variant styles", () => {
    render(<SectionHeading variant="uppercase">Upper</SectionHeading>);
    const heading = screen.getByRole("heading");
    expect(heading.className).toContain("uppercase");
    expect(heading.className).toContain("tracking-wider");
    expect(heading.className).toContain("text-xs");
  });

  it("renders action node alongside heading", () => {
    render(<SectionHeading action={<button>Edit</button>}>With Action</SectionHeading>);
    expect(screen.getByRole("heading")).toHaveTextContent("With Action");
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
  });

  it("wraps heading and action in flex container when action provided", () => {
    const { container } = render(
      <SectionHeading action={<span>Action</span>}>Title</SectionHeading>,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("flex");
    expect(wrapper.className).toContain("items-center");
    expect(wrapper.className).toContain("justify-between");
  });

  it("appends custom className", () => {
    render(<SectionHeading className="mb-4">Custom</SectionHeading>);
    const heading = screen.getByRole("heading");
    expect(heading.className).toContain("mb-4");
  });
});
