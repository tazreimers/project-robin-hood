"use client";

import { useCallback, useEffect, useState } from "react";

import { getHealth } from "../lib/api";
import type { HealthResponse } from "../types/api";

export function useApiHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setHealth(await getHealth());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load API health");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { health, loading, error, refresh };
}
