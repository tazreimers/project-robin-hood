import { Card, CardContent, CircularProgress, Typography } from "@mui/material";

export default function MetricCard({ label, value, loading, tone }: { label: string; value: number | string; loading?: boolean; tone?: string }) {
  return (
    <Card sx={{ height: "100%", "&:hover": { boxShadow: 4, transform: "translateY(-1px)" } }}>
      <CardContent>
        <Typography color="text.secondary" variant="body2">
          {label}
        </Typography>
        <Typography variant="h4" sx={{ mt: 1, fontWeight: 700, color: tone }}>
          {loading ? <CircularProgress size={26} /> : value}
        </Typography>
      </CardContent>
    </Card>
  );
}
