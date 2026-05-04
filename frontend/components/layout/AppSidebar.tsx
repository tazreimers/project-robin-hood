"use client";

import ApiIcon from "@mui/icons-material/Api";
import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DashboardIcon from "@mui/icons-material/Dashboard";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";
import HistoryIcon from "@mui/icons-material/History";
import PendingActionsIcon from "@mui/icons-material/PendingActions";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import Link from "next/link";
import { usePathname } from "next/navigation";

export const expandedDrawerWidth = 248;
export const collapsedDrawerWidth = 76;

const navItems = [
  { label: "Dashboard", href: "/", icon: <DashboardIcon /> },
  { label: "Opportunities", href: "/opportunities", icon: <TrendingUpIcon /> },
  { label: "Executions", href: "/executions", icon: <AssignmentTurnedInIcon /> },
  { label: "Scan Priorities", href: "/scan-priorities", icon: <PendingActionsIcon /> },
  { label: "Scan Runs", href: "/scan-runs", icon: <HistoryIcon /> },
  { label: "API Usage", href: "/api-usage", icon: <ApiIcon /> },
  { label: "Help", href: "/help", icon: <HelpOutlineIcon /> },
];

export default function AppSidebar({
  open,
  width,
  onToggle,
}: {
  open: boolean;
  width: number;
  onToggle: () => void;
}) {
  const pathname = usePathname();

  return (
    <Box component="nav" sx={{ width, flexShrink: 0, transition: "width 200ms ease" }}>
      <Drawer
        variant="permanent"
        sx={{
          "& .MuiDrawer-paper": {
            boxSizing: "border-box",
            width,
            overflowX: "hidden",
            transition: "width 200ms ease",
            borderRight: 1,
            borderColor: "divider",
            bgcolor: "background.paper",
          },
        }}
        open
      >
        <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <Toolbar sx={{ minHeight: 64, px: open ? 2 : 1.25 }}>
            <Stack direction="row" spacing={1.25} sx={{ alignItems: "center", minWidth: 0, width: "100%" }}>
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: 2,
                  bgcolor: "primary.main",
                  color: "primary.contrastText",
                  display: "grid",
                  placeItems: "center",
                  fontWeight: 900,
                  flex: "0 0 auto",
                }}
              >
                RH
              </Box>
              {open ? (
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.1 }} noWrap>
                    Project Robin Hood
                  </Typography>
                  <Typography color="text.secondary" variant="caption" noWrap>
                    Arbitrage terminal
                  </Typography>
                </Box>
              ) : null}
            </Stack>
          </Toolbar>
          <Divider />
          <List sx={{ px: 1, py: 1.25 }}>
            {navItems.map((item) => {
              const selected = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Tooltip key={item.href} title={open ? "" : item.label} placement="right">
                  <ListItemButton
                    component={Link}
                    href={item.href}
                    selected={selected}
                    sx={{
                      borderRadius: 2,
                      mb: 0.75,
                      minHeight: 44,
                      justifyContent: open ? "initial" : "center",
                      px: open ? 1.5 : 1,
                      transition: "background-color 180ms ease, color 180ms ease",
                      "&.Mui-selected": {
                        bgcolor: "primary.main",
                        color: "primary.contrastText",
                        "& .MuiListItemIcon-root": { color: "primary.contrastText" },
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: open ? 40 : 0, color: "inherit" }}>{item.icon}</ListItemIcon>
                    {open ? (
                      <ListItemText primary={item.label} slotProps={{ primary: { sx: { fontWeight: 700 } } }} />
                    ) : null}
                  </ListItemButton>
                </Tooltip>
              );
            })}
          </List>
          <Box sx={{ flexGrow: 1 }} />
          <Divider />
          <Box sx={{ p: 1 }}>
            <Tooltip title={open ? "Collapse sidebar" : "Expand sidebar"} placement="right">
              <IconButton
                aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
                onClick={onToggle}
                sx={{ width: "100%", borderRadius: 2 }}
              >
                {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Drawer>
    </Box>
  );
}
