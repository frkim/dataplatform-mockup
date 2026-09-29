import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownRenderer } from "./MarkdownRenderer";

describe("MarkdownRenderer", () => {
  it("escapes raw HTML instead of injecting it", () => {
    const { container } = render(<MarkdownRenderer markdown={'# Answer\n<img src="x" onerror="alert(1)">'} />);
    expect(screen.getByText(/<img src="x" onerror="alert\(1\)">/)).toBeTruthy();
    expect(container.querySelector("img")).toBeNull();
  });

  it("renders numbered lists as ordered lists", () => {
    const { container } = render(<MarkdownRenderer markdown={"**Top 2 products**:\n\n1. Alpha — €10\n2. Beta — €5"} />);
    const items = container.querySelectorAll("ol > li");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toBe("Alpha — €10");
    expect(container.querySelector("strong")?.textContent).toBe("Top 2 products");
  });

  it("renders nested emphasis without treating identifiers as italic", () => {
    const { container } = render(
      <MarkdownRenderer markdown={"_Routed to the **Sales Agent**._ See order_items and retail_sales_orders."} />,
    );
    expect(container.querySelector("em strong")?.textContent).toBe("Sales Agent");
    expect(container.querySelectorAll("em")).toHaveLength(1);
    expect(container.textContent).toContain("order_items and retail_sales_orders.");
    expect(container.textContent).not.toContain("**");
  });

  it("keeps non-http links inert", () => {
    render(<MarkdownRenderer markdown={"[click](javascript:alert(1))"} />);
    expect(screen.getByText("click").getAttribute("href")).toBe("#");
  });
});
