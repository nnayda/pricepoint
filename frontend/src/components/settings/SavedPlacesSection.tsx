import { useState, useRef, useEffect } from "react";
import type { PoiAutocompleteItem, SavedPoiResponse } from "../../types";
import { usePoiAutocomplete } from "../../hooks/useSavedPois";

interface Props {
  pois: SavedPoiResponse[];
  onAdd: (item: {
    match_type: string;
    match_value: string;
    display_name: string;
    category?: string | null;
  }) => Promise<void>;
  onRemove: (id: number) => Promise<void>;
}

export default function SavedPlacesSection({ pois, onAdd, onRemove }: Props) {
  const [query, setQuery] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { results, isLoading } = usePoiAutocomplete(query);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function handleSelect(item: PoiAutocompleteItem) {
    setSaving(true);
    try {
      await onAdd({
        match_type: item.match_type,
        match_value: item.match_value,
        display_name: item.display_name,
        category: item.category,
      });
      setQuery("");
      setShowDropdown(false);
    } catch {
      /* duplicate or network error — ignore */
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    setDeleting(id);
    try {
      await onRemove(id);
    } catch {
      /* ignore */
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold" style={{ color: "var(--color-db-text-primary)" }}>
        Saved Places
      </h2>
      <p className="text-sm" style={{ color: "var(--color-db-text-secondary)" }}>
        Search for brands or places you care about. They'll appear in the POIs tab when viewing any
        property.
      </p>

      {/* Autocomplete input */}
      <div className="relative" ref={dropdownRef}>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => query.length >= 2 && setShowDropdown(true)}
          placeholder="Search places (e.g. Costco, Trader Joe's)"
          className="w-full px-3 outline-none transition-shadow"
          style={{
            height: "36px",
            borderRadius: "8px",
            backgroundColor: "var(--th-bg-elevated, var(--th-bg-base))",
            color: "var(--color-db-text-primary)",
            border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
          }}
        />
        {showDropdown && query.length >= 2 && (
          <div
            className="absolute left-0 right-0 top-full z-10 mt-1 max-h-60 overflow-y-auto rounded-lg py-1"
            style={{
              backgroundColor: "var(--th-bg-surface, #fff)",
              border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
              boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
            }}
          >
            {isLoading && (
              <div
                className="px-3 py-2 text-sm"
                style={{ color: "var(--color-db-text-secondary)" }}
              >
                Searching...
              </div>
            )}
            {!isLoading && results.length === 0 && (
              <div
                className="px-3 py-2 text-sm"
                style={{ color: "var(--color-db-text-secondary)" }}
              >
                No results found
              </div>
            )}
            {results.map((item) => (
              <button
                key={`${item.match_type}-${item.match_value}`}
                onClick={() => handleSelect(item)}
                disabled={saving}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors hover:bg-black/5"
                style={{ color: "var(--color-db-text-primary)" }}
              >
                <span>
                  {item.display_name}
                  {item.category && (
                    <span
                      className="ml-2 text-xs"
                      style={{ color: "var(--color-db-text-secondary)" }}
                    >
                      {item.category}
                    </span>
                  )}
                </span>
                <span className="ml-2 text-xs" style={{ color: "var(--color-db-text-secondary)" }}>
                  {item.count} {item.count === 1 ? "location" : "locations"}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Saved POI list */}
      {pois.length > 0 && (
        <ul className="flex flex-col gap-2">
          {pois.map((poi) => (
            <li
              key={poi.id}
              className="flex items-center justify-between rounded-lg px-3 py-2"
              style={{
                backgroundColor: "var(--th-bg-elevated, var(--th-bg-base))",
                border: "1px solid var(--color-db-border, rgba(0,0,0,0.05))",
              }}
            >
              <div>
                <span
                  className="text-sm font-medium"
                  style={{ color: "var(--color-db-text-primary)" }}
                >
                  {poi.display_name}
                </span>
                {poi.category && (
                  <span
                    className="ml-2 text-xs"
                    style={{ color: "var(--color-db-text-secondary)" }}
                  >
                    {poi.category}
                  </span>
                )}
                <span
                  className="ml-2 rounded px-1.5 py-0.5 text-xs"
                  style={{
                    backgroundColor: "var(--color-db-accent-10, rgba(59,130,246,0.1))",
                    color: "var(--color-db-accent, #3b82f6)",
                  }}
                >
                  {poi.match_type}
                </span>
              </div>
              <button
                onClick={() => handleDelete(poi.id)}
                disabled={deleting === poi.id}
                className="text-sm transition-opacity hover:opacity-70 disabled:opacity-40"
                style={{ color: "#ef4444" }}
                aria-label={`Remove ${poi.display_name}`}
              >
                {deleting === poi.id ? "..." : "Remove"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
