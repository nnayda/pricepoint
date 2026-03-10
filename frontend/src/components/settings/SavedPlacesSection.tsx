import { useState, useRef, useEffect } from "react";
import type { PoiAutocompleteItem, SavedPoiResponse } from "../../types";
import { usePoiAutocomplete } from "../../hooks/useSavedPois";

const PRESET_COLORS = [
  "#F59E0B",
  "#EF4444",
  "#10B981",
  "#3B82F6",
  "#8B5CF6",
  "#EC4899",
  "#F97316",
  "#06B6D4",
  "#6366F1",
  "#14B8A6",
];

interface Props {
  pois: SavedPoiResponse[];
  onAdd: (item: {
    match_type: string;
    match_value: string;
    display_name: string;
    category?: string | null;
  }) => Promise<void>;
  onRemove: (id: number) => Promise<void>;
  onUpdate?: (
    id: number,
    body: {
      user_category?: string | null;
      marker_color?: string | null;
      marker_image_url?: string | null;
    },
  ) => Promise<void>;
}

function ColorPicker({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (color: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="h-6 w-6 shrink-0 rounded-full border-2"
        style={{
          backgroundColor: value || PRESET_COLORS[0],
          borderColor: "var(--color-db-border, rgba(0,0,0,0.1))",
        }}
        aria-label="Pick marker color"
      />
      {open && (
        <div
          className="absolute left-0 top-full z-20 mt-1 grid grid-cols-5 gap-1 rounded-lg p-2"
          style={{
            backgroundColor: "var(--th-bg-surface, #fff)",
            border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          }}
        >
          {PRESET_COLORS.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => {
                onChange(c);
                setOpen(false);
              }}
              className="h-6 w-6 rounded-full transition-transform hover:scale-110"
              style={{
                backgroundColor: c,
                outline: c === value ? "2px solid var(--color-db-accent)" : "none",
                outlineOffset: 2,
              }}
              aria-label={`Color ${c}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SavedPlacesSection({ pois, onAdd, onRemove, onUpdate }: Props) {
  const [query, setQuery] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [editingImageId, setEditingImageId] = useState<number | null>(null);
  const [imageUrlInput, setImageUrlInput] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { results, isLoading } = usePoiAutocomplete(query);

  // Derive existing user categories for autocomplete
  const existingCategories = [...new Set(pois.map((p) => p.user_category).filter(Boolean))];

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

      {/* Saved POI list with customization */}
      {pois.length > 0 && (
        <ul className="flex flex-col gap-3">
          {pois.map((poi) => (
            <li
              key={poi.id}
              className="flex flex-col gap-2 rounded-lg px-3 py-3"
              style={{
                backgroundColor: "var(--th-bg-elevated, var(--th-bg-base))",
                border: "1px solid var(--color-db-border, rgba(0,0,0,0.05))",
              }}
            >
              {/* Top row: name + remove */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ColorPicker
                    value={poi.marker_color}
                    onChange={(color) => onUpdate?.(poi.id, { marker_color: color })}
                  />
                  <span
                    className="text-sm font-medium"
                    style={{ color: "var(--color-db-text-primary)" }}
                  >
                    {poi.display_name}
                  </span>
                  {poi.category && (
                    <span
                      className="text-xs"
                      style={{ color: "var(--color-db-text-secondary)" }}
                    >
                      {poi.category}
                    </span>
                  )}
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
              </div>

              {/* Customization row */}
              {onUpdate && (
                <div className="flex flex-wrap items-center gap-3">
                  {/* Category input */}
                  <div className="flex items-center gap-1">
                    <label
                      className="text-[11px]"
                      style={{ color: "var(--color-db-text-tertiary)" }}
                    >
                      Group:
                    </label>
                    <input
                      type="text"
                      defaultValue={poi.user_category ?? ""}
                      list={`cat-list-${poi.id}`}
                      placeholder="Default"
                      onBlur={(e) => {
                        const val = e.target.value.trim() || null;
                        if (val !== poi.user_category) {
                          onUpdate(poi.id, { user_category: val });
                        }
                      }}
                      className="w-24 rounded px-1.5 py-0.5 text-xs outline-none"
                      style={{
                        backgroundColor: "var(--th-bg-surface, #fff)",
                        color: "var(--color-db-text-primary)",
                        border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
                      }}
                    />
                    <datalist id={`cat-list-${poi.id}`}>
                      {existingCategories.map((c) => (
                        <option key={c} value={c!} />
                      ))}
                    </datalist>
                  </div>

                  {/* Image URL */}
                  <div className="flex items-center gap-1">
                    {editingImageId === poi.id ? (
                      <>
                        <input
                          type="text"
                          value={imageUrlInput}
                          onChange={(e) => setImageUrlInput(e.target.value)}
                          placeholder="https://logo.url/img.png"
                          onBlur={() => {
                            const val = imageUrlInput.trim() || null;
                            onUpdate(poi.id, { marker_image_url: val });
                            setEditingImageId(null);
                            setImageUrlInput("");
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              (e.target as HTMLInputElement).blur();
                            }
                          }}
                          autoFocus
                          className="w-40 rounded px-1.5 py-0.5 text-xs outline-none"
                          style={{
                            backgroundColor: "var(--th-bg-surface, #fff)",
                            color: "var(--color-db-text-primary)",
                            border: "1px solid var(--color-db-border, rgba(0,0,0,0.1))",
                          }}
                        />
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setEditingImageId(poi.id);
                          setImageUrlInput(poi.marker_image_url ?? "");
                        }}
                        className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] transition-colors hover:bg-black/5"
                        style={{ color: "var(--color-db-text-tertiary)" }}
                      >
                        {poi.marker_image_url ? (
                          <>
                            <img
                              src={poi.marker_image_url}
                              alt=""
                              className="h-4 w-4 rounded-full object-cover"
                            />
                            <span>Logo</span>
                          </>
                        ) : (
                          <span>+ Logo</span>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
