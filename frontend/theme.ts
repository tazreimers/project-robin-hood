import { createTheme } from "@mui/material/styles";

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
  palette: {
    mode: "light",
    primary: {
      main: "#2E7D32",
    },
    secondary: {
      main: "#C9A227",
      contrastText: "#1C1C1C",
    },
    background: {
      default: "#F5F1E6",
      paper: "#FFFFFF",
    },
    text: {
      primary: "#1C1C1C",
      secondary: "#5F5A4D",
    },
    success: {
      main: "#2E7D32",
    },
    warning: {
      main: "#C9A227",
    },
    error: {
      main: "#B3261E",
    },
  },
  shape: {
    borderRadius: 10,
  },
  typography: baseTypography,
  components: baseComponents,
});

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#4CAF50",
    },
    secondary: {
      main: "#D4AF37",
      contrastText: "#121212",
    },
    background: {
      default: "#121212",
      paper: "#1E1E1E",
    },
    text: {
      primary: "#EAEAEA",
      secondary: "#B7B7B7",
    },
    success: {
      main: "#4CAF50",
    },
    warning: {
      main: "#D4AF37",
    },
    error: {
      main: "#EF5350",
    },
  },
  shape: {
    borderRadius: 10,
  },
  typography: baseTypography,
  components: baseComponents,
});

export default lightTheme;
