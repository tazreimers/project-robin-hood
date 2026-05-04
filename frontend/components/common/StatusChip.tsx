import { Chip, type ChipProps } from "@mui/material";

export default function StatusChip({ status, color }: { status: string; color?: ChipProps["color"] }) {
  return <Chip size="small" label={status} color={color ?? statusColor(status)} />;
}

function statusColor(status: string): ChipProps["color"] {
  const normalized = status.toUpperCase();
  if (["COMPLETED", "FRESH", "VERIFIED", "ACTIONED", "SETTLED", "NORMAL"].includes(normalized)) {
    return "success";
  }
  if (["QUEUED", "RUNNING", "RISKY", "STALE", "HIGH", "ODDS_CHANGED"].includes(normalized)) {
    return "warning";
  }
  if (["FAILED", "REJECTED", "EXPIRED", "URGENT"].includes(normalized)) {
    return "error";
  }
  return "default";
}
