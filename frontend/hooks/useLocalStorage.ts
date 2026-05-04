"use client";

import { useCallback, useEffect, useState } from "react";

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(initialValue);

  useEffect(() => {
    const storedValue = window.localStorage.getItem(key);
    if (storedValue === null) {
      return;
    }

    try {
      setValue(JSON.parse(storedValue) as T);
    } catch {
      setValue(storedValue as T);
    }
  }, [key]);

  const updateValue = useCallback(
    (nextValue: T | ((current: T) => T)) => {
      setValue((current) => {
        const resolvedValue = nextValue instanceof Function ? nextValue(current) : nextValue;
        window.localStorage.setItem(key, JSON.stringify(resolvedValue));
        return resolvedValue;
      });
    },
    [key],
  );

  return [value, updateValue] as const;
}
