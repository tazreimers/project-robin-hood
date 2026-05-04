import { createTheme } from "@mui/material/styles";

import { darkPalette, lightPalette } from "./palette";

const baseTypography = {
  fontFamily:
    'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  h5: {
    fontWeight: 700,
    letterSpacing: 0,
  },
  h6: {
    fontWeight: 700,
    letterSpacing: 0,
  },
  body2: {
    letterSpacing: 0,
  },
} as const;

const baseComponents = {
  MuiCard: {
    styleOverrides: {
      root: {
        backgroundImage: "none",
        transition: "box-shadow 180ms ease, transform 180ms ease, border-color 180ms ease",
      },
    },
  },
  MuiButton: {
    styleOverrides: {
      root: {
        textTransform: "none",
        fontWeight: 700,
        transition: "box-shadow 180ms ease, transform 180ms ease, background-color 180ms ease",
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        fontWeight: 700,
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        backgroundImage: "none",
      },
    },
  },
} as const;

export const lightTheme = createTheme({
  palette: lightPalette,
  shape: {
    borderRadius: 10,
  },
  typography: baseTypography,
  components: baseComponents,
});

export const darkTheme = createTheme({
  palette: darkPalette,
  shape: {
    borderRadius: 10,
  },
  typography: baseTypography,
  components: baseComponents,
});

export default lightTheme;
