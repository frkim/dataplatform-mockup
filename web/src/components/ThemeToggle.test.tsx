import { ThemeProvider } from "@mui/material";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { theme } from "@/theme/theme";
import { ThemeToggle } from "./ThemeToggle";

describe("ThemeToggle", () => {
  it("renders and persists an explicit color mode", async () => {
    localStorage.clear();
    const user = userEvent.setup();
    render(
      <ThemeProvider theme={theme} defaultMode="system" modeStorageKey="dataplatform-color-mode">
        <ThemeToggle />
      </ThemeProvider>,
    );

    const button = screen.getByRole("button", { name: /switch color mode/i });
    await user.click(button);

    await waitFor(() => expect(localStorage.getItem("dataplatform-color-mode")).toBe("dark"));
  });
});
