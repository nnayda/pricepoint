import { useCallback, useEffect, useState } from "react";
import {
  getSavedProperties,
  deleteSavedProperty,
  type SavedPropertyResponse,
} from "../services/saved";

const TOKEN_KEY = "pricepoint-auth-token";

function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

interface UseSavedPropertiesResult {
  properties: SavedPropertyResponse[];
  isLoading: boolean;
  error: string | null;
  remove: (savedId: number) => Promise<void>;
  refetch: () => void;
}

export function useSavedProperties(isAuthenticated: boolean): UseSavedPropertiesResult {
  const [properties, setProperties] = useState<SavedPropertyResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchKey, setFetchKey] = useState(0);

  useEffect(() => {
    if (!isAuthenticated) {
      setProperties([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    const token = getToken();
    if (!token) return;

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    getSavedProperties(token)
      .then((items) => {
        if (!cancelled) setProperties(items);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load saved properties.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, fetchKey]);

  const remove = useCallback(async (savedId: number) => {
    const token = getToken();
    if (!token) return;

    // Optimistic removal
    setProperties((prev) => prev.filter((p) => p.id !== savedId));
    try {
      await deleteSavedProperty(token, savedId);
    } catch {
      // Re-fetch on failure to restore state
      setFetchKey((k) => k + 1);
    }
  }, []);

  const refetch = useCallback(() => {
    setFetchKey((k) => k + 1);
  }, []);

  return { properties, isLoading, error, remove, refetch };
}
