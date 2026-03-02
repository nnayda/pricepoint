import { useCallback, useEffect, useState } from "react";
import { getSavedProperties, saveProperty, deleteSavedProperty } from "../services/saved";

const TOKEN_KEY = "pricepoint-auth-token";

function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

interface UseSavedPropertyResult {
  isSaved: boolean;
  savedId: number | null;
  isLoading: boolean;
  toggle: () => Promise<void>;
}

export function useSavedProperty(
  listingId: number | null | undefined,
  isAuthenticated: boolean,
): UseSavedPropertyResult {
  const [isSaved, setIsSaved] = useState(false);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !listingId) {
      setIsSaved(false);
      setSavedId(null);
      return;
    }

    const token = getToken();
    if (!token) return;

    let cancelled = false;
    setIsLoading(true);

    getSavedProperties(token)
      .then((items) => {
        if (cancelled) return;
        const match = items.find((item) => item.listing_id === listingId);
        if (match) {
          setIsSaved(true);
          setSavedId(match.id);
        } else {
          setIsSaved(false);
          setSavedId(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setIsSaved(false);
          setSavedId(null);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [listingId, isAuthenticated]);

  const toggle = useCallback(async () => {
    const token = getToken();
    if (!token || !listingId) return;

    setIsLoading(true);
    try {
      if (isSaved && savedId !== null) {
        await deleteSavedProperty(token, savedId);
        setIsSaved(false);
        setSavedId(null);
      } else {
        const result = await saveProperty(token, listingId);
        setIsSaved(true);
        setSavedId(result.id);
      }
    } finally {
      setIsLoading(false);
    }
  }, [listingId, isSaved, savedId]);

  return { isSaved, savedId, isLoading, toggle };
}
