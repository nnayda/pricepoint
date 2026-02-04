import { useCallback, useState } from "react";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useApi<T, A extends unknown[]>(
  apiFn: (...args: A) => Promise<T>,
): UseApiState<T> & { execute: (...args: A) => Promise<void> } {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(
    async (...args: A) => {
      setState({ data: null, loading: true, error: null });
      try {
        const data = await apiFn(...args);
        setState({ data, loading: false, error: null });
      } catch (err) {
        const message = err instanceof Error ? err.message : "An error occurred";
        setState({ data: null, loading: false, error: message });
      }
    },
    [apiFn],
  );

  return { ...state, execute };
}
