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
      // localStorage has no schema at runtime; the hook caller owns the value contract for its key.
      // eslint-disable-next-line no-type-assertion/no-type-assertion
      setValue(JSON.parse(storedValue) as T);
    } catch {
      // eslint-disable-next-line no-type-assertion/no-type-assertion
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
    [key]
  );

  return [value, updateValue] as const;
}
