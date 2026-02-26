import { useState, useEffect, useCallback } from "react";
import type { MapStyle } from "../components/dashboard/maps/DashboardMap";

const STORAGE_KEY = "pricepoint-map-style";
const SYNC_EVENT = "pricepoint-map-style-change";

function readStored(): MapStyle | null {
  if (typeof window === "undefined") return null;
  const val = localStorage.getItem(STORAGE_KEY);
  if (val === "street" || val === "satellite" || val === "dark" || val === "light") return val;
  return null;
}

/**
 * Shared map style hook. Persists to localStorage and syncs across all
 * DashboardMap instances on the page via a custom DOM event.
 *
 * @param defaultStyle - fallback when no stored preference exists
 * @returns [style, setStyle, userHasChosen] where userHasChosen indicates
 *          whether the user has explicitly picked a style (vs theme default).
 */
export function useMapStyle(defaultStyle: MapStyle): [MapStyle, (s: MapStyle) => void, boolean] {
  const [style, setStyleState] = useState<MapStyle>(() => readStored() ?? defaultStyle);
  const [userHasChosen, setUserHasChosen] = useState(() => readStored() !== null);

  // Sync from other instances on same page
  useEffect(() => {
    function onSync(e: Event) {
      const detail = (e as CustomEvent<MapStyle>).detail;
      setStyleState(detail);
      setUserHasChosen(true);
    }
    window.addEventListener(SYNC_EVENT, onSync);
    return () => window.removeEventListener(SYNC_EVENT, onSync);
  }, []);

  // Follow default when user hasn't explicitly chosen
  useEffect(() => {
    if (!userHasChosen) {
      setStyleState(defaultStyle);
    }
  }, [defaultStyle, userHasChosen]);

  const setStyle = useCallback((s: MapStyle) => {
    setStyleState(s);
    setUserHasChosen(true);
    localStorage.setItem(STORAGE_KEY, s);
    window.dispatchEvent(new CustomEvent(SYNC_EVENT, { detail: s }));
  }, []);

  return [style, setStyle, userHasChosen];
}
