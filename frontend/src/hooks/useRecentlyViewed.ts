import { useCallback, useState } from "react";
import type { RecentlyViewedItem } from "../types";

const STORAGE_KEY = "pricepoint-recently-viewed";
const MAX_ITEMS = 10;

function loadItems(): RecentlyViewedItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    // ignore parse errors
  }
  return [];
}

function saveItems(items: RecentlyViewedItem[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function useRecentlyViewed() {
  const [recentlyViewed, setRecentlyViewed] = useState<RecentlyViewedItem[]>(loadItems);

  const addRecentlyViewed = useCallback((item: RecentlyViewedItem) => {
    setRecentlyViewed((prev) => {
      const filtered = prev.filter((p) => p.address !== item.address);
      const next = [{ ...item, viewedAt: item.viewedAt }, ...filtered].slice(0, MAX_ITEMS);
      saveItems(next);
      return next;
    });
  }, []);

  const clearRecentlyViewed = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setRecentlyViewed([]);
  }, []);

  return { recentlyViewed, addRecentlyViewed, clearRecentlyViewed };
}
