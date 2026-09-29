import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownRenderer } from "./MarkdownRenderer";

describe("MarkdownRenderer", () => {
  it("escapes raw HTML instead of injecting it", () => {
    const { container } = render(<MarkdownRenderer markdown={'# Answer\n<img src="x" onerror="alert(1)">'} />);
    expect(screen.getByText(/<img src="x" onerror="alert\(1\)">/)).toBeTruthy();
    expect(container.querySelector("img")).toBeNull();
  });
});
