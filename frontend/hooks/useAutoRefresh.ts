"use client";

import { useEffect, useState } from "react";

export function useAutoRefresh(enabled: boolean, intervalSeconds: number, onRefresh: () => void) {
  const [countdown, setCountdown] = useState(intervalSeconds);

  useEffect(() => {
    setCountdown(intervalSeconds);
  }, [intervalSeconds]);

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setCountdown((current) => {
        if (current <= 1) {
          onRefresh();
          return intervalSeconds;
        }
        return current - 1;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [enabled, intervalSeconds, onRefresh]);

  return countdown;
}
