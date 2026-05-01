"use client";

import DashboardIcon from "@mui/icons-material/Dashboard";
import HistoryIcon from "@mui/icons-material/History";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  AppBar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  ThemeProvider,
  Toolbar,
  Typography,
} from "@mui/material";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import theme from "../theme";

const drawerWidth = 240;

const navItems = [
  { label: "Dashboard", href: "/", icon: <DashboardIcon /> },
  { label: "Opportunities", href: "/opportunities", icon: <TrendingUpIcon /> },
  { label: "Scan Runs", href: "/scan-runs", icon: <HistoryIcon /> },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          Project Robin Hood
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1 }}>
        {navItems.map((item) => {
          const selected = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <ListItemButton
              component={Link}
              href={item.href}
              key={item.href}
              selected={selected}
              sx={{ borderRadius: 1, mb: 0.5 }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: "flex", minHeight: "100vh" }}>
        <AppBar
          position="fixed"
          sx={{
            ml: { md: `${drawerWidth}px` },
            width: { md: `calc(100% - ${drawerWidth}px)` },
          }}
        >
          <Toolbar>
            <Typography variant="h6" noWrap sx={{ fontWeight: 700 }}>
              Arbitrage Scanner
            </Typography>
          </Toolbar>
        </AppBar>
        <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: "none", md: "block" },
              "& .MuiDrawer-paper": {
                boxSizing: "border-box",
                width: drawerWidth,
              },
            }}
            open
          >
            {drawer}
          </Drawer>
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: "block", md: "none" },
              "& .MuiDrawer-paper": {
                boxSizing: "border-box",
                width: 72,
                overflowX: "hidden",
              },
            }}
            open
          >
            <Toolbar />
            <Divider />
            <List sx={{ px: 1 }}>
              {navItems.map((item) => {
                const selected = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                return (
                  <ListItemButton
                    component={Link}
                    href={item.href}
                    key={item.href}
                    selected={selected}
                    sx={{ borderRadius: 1, justifyContent: "center", mb: 0.5, px: 1 }}
                  >
                    <ListItemIcon sx={{ minWidth: 0 }}>{item.icon}</ListItemIcon>
                  </ListItemButton>
                );
              })}
            </List>
          </Drawer>
        </Box>
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            minWidth: 0,
            pl: { xs: "72px", md: 0 },
            pt: 8,
          }}
        >
          <Box sx={{ p: { xs: 2, sm: 3 } }}>{children}</Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
