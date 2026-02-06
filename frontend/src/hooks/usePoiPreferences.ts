import { useCallback, useState } from "react";
import type { PoiPreference } from "../types";

const STORAGE_KEY = "pricepoint-poi-preferences";

const DEFAULT_POIS: PoiPreference[] = [
  { id: "costco", name: "Costco", category: "Grocery", enabled: true },
  { id: "trader-joes", name: "Trader Joe's", category: "Grocery", enabled: true },
  { id: "whole-foods", name: "Whole Foods", category: "Grocery", enabled: true },
  { id: "publix", name: "Publix", category: "Grocery", enabled: true },
  { id: "target", name: "Target", category: "Retail", enabled: true },
  { id: "walmart", name: "Walmart", category: "Retail", enabled: true },
  { id: "cvs", name: "CVS", category: "Pharmacy", enabled: true },
  { id: "walgreens", name: "Walgreens", category: "Pharmacy", enabled: true },
  { id: "chipotle", name: "Chipotle", category: "Restaurant", enabled: true },
  { id: "starbucks", name: "Starbucks", category: "Restaurant", enabled: true },
];

function loadPreferences(): PoiPreference[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    // ignore parse errors
  }
  return DEFAULT_POIS;
}

function savePreferences(prefs: PoiPreference[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function usePoiPreferences() {
  const [preferences, setPreferences] = useState<PoiPreference[]>(loadPreferences);

  const togglePoi = useCallback((id: string) => {
    setPreferences((prev) => {
      const next = prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p));
      savePreferences(next);
      return next;
    });
  }, []);

  const toggleCategory = useCallback((category: string) => {
    setPreferences((prev) => {
      const inCategory = prev.filter((p) => p.category === category);
      const allEnabled = inCategory.every((p) => p.enabled);
      const next = prev.map((p) => (p.category === category ? { ...p, enabled: !allEnabled } : p));
      savePreferences(next);
      return next;
    });
  }, []);

  const addCustomPoi = useCallback((name: string, category: string) => {
    setPreferences((prev) => {
      const id = `custom-${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}`;
      const next = [...prev, { id, name, category, enabled: true, isCustom: true }];
      savePreferences(next);
      return next;
    });
  }, []);

  const removeCustomPoi = useCallback((id: string) => {
    setPreferences((prev) => {
      const next = prev.filter((p) => p.id !== id || !p.isCustom);
      savePreferences(next);
      return next;
    });
  }, []);

  return { preferences, togglePoi, toggleCategory, addCustomPoi, removeCustomPoi };
}
