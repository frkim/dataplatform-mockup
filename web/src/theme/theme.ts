import { createTheme } from "@mui/material/styles";

/** Application-wide MUI CSS variables theme. */
export const theme = createTheme({
  cssVariables: { colorSchemeSelector: "class" },
  colorSchemes: {
    light: {
      palette: {
        primary: { main: "#0b4f6c", contrastText: "#ffffff" },
        secondary: { main: "#00796b", contrastText: "#ffffff" },
        background: { default: "#f5f8fb", paper: "#ffffff" },
        text: { primary: "#10212b", secondary: "#4b5d67" },
        success: { main: "#1b7f3a" },
        error: { main: "#b42318" },
      },
    },
    dark: {
      palette: {
        primary: { main: "#62c7e8", contrastText: "#06131a" },
        secondary: { main: "#4dd0c1", contrastText: "#041716" },
        background: { default: "#07131d", paper: "#0e2230" },
        text: { primary: "#edf7fb", secondary: "#b3c6d1" },
        success: { main: "#65d18a" },
        error: { main: "#ff9c8f" },
      },
    },
  },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 700 },
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 700 },
    button: { textTransform: "none", fontWeight: 700 },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiButtonBase: { defaultProps: { disableRipple: false } },
    MuiCard: { styleOverrides: { root: { backgroundImage: "none" } } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
  },
});
