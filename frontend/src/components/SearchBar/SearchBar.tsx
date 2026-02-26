import { useState, useRef, useEffect, useCallback } from "react";
import { useGeocode } from "../../hooks/useGeocode";
import type { GeocodeResult } from "../../types";

interface SearchBarProps {
  onSelect: (result: GeocodeResult) => void;
  placeholder?: string;
  variant?: "default" | "landing";
}

function SearchBar({ onSelect, placeholder = "Search for an address...", variant = "default" }: SearchBarProps) {
  const isDark = variant === "landing";
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [notFound, setNotFound] = useState(false);
  const { results, loading, error } = useGeocode(query);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxRef = useRef<HTMLUListElement>(null);

  const showDropdown = isOpen && query.length >= 3 && (results.length > 0 || loading || !!error);

  useEffect(() => {
    if (results.length > 0) {
      setIsOpen(true);
      setNotFound(false);
    }
    setActiveIndex(-1);
  }, [results]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectResult = useCallback(
    (result: GeocodeResult) => {
      setQuery(result.display_name);
      setIsOpen(false);
      setActiveIndex(-1);
      setNotFound(false);
      onSelect(result);
    },
    [onSelect],
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    switch (e.key) {
      case "Enter":
        e.preventDefault();
        if (activeIndex >= 0 && activeIndex < results.length) {
          selectResult(results[activeIndex]);
        } else if (results.length > 0) {
          selectResult(results[0]);
        } else if (query.length >= 3 && !loading) {
          setNotFound(true);
          setIsOpen(false);
        }
        return;
      case "Escape":
        setIsOpen(false);
        setActiveIndex(-1);
        inputRef.current?.blur();
        return;
    }

    if (!showDropdown) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-lg">
      <div className="relative">
        <svg
          className={`pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 sm:left-4 ${isDark ? "text-[var(--color-db-text-muted)]" : "text-text-sec"}`}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={showDropdown || false}
          aria-controls="searchbar-listbox"
          aria-activedescendant={activeIndex >= 0 ? `searchbar-option-${activeIndex}` : undefined}
          aria-autocomplete="list"
          aria-label="Search address"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setNotFound(false);
            if (e.target.value.length >= 3) {
              setIsOpen(true);
            }
          }}
          onFocus={() => {
            if (results.length > 0 && query.length >= 3) {
              setIsOpen(true);
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={
            isDark
              ? "w-full rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] bg-[var(--color-db-surface)] py-3 pl-10 pr-3 text-sm font-medium text-[var(--color-db-text-primary)] shadow-[var(--shadow-db-card)] outline-none placeholder:text-[var(--color-db-text-muted)] focus:border-[var(--color-db-accent)] sm:py-3.5 sm:pl-11 sm:pr-4 sm:text-base"
              : "w-full rounded-pill bg-bg-card py-2.5 pl-10 pr-3 text-sm font-medium text-text-pri shadow-card outline-none placeholder:text-text-sec focus:ring-2 focus:ring-brand-blue sm:py-3 sm:pl-11 sm:pr-4 sm:text-base"
          }
        />
        {loading && (
          <div
            className={`absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin rounded-full border-2 ${isDark ? "border-[var(--color-db-text-muted)] border-t-[var(--color-db-accent)]" : "border-text-sec border-t-brand-blue"}`}
            role="status"
            aria-label="Loading results"
          />
        )}
      </div>

      {notFound && (
        <p role="alert" className={`mt-2 text-sm ${isDark ? "text-[var(--color-db-red)]" : "text-status-rented"}`}>
          Address not found. Try a different search.
        </p>
      )}

      {showDropdown && (
        <ul
          ref={listboxRef}
          id="searchbar-listbox"
          role="listbox"
          aria-label="Address suggestions"
          className={`absolute z-50 mt-2 w-full overflow-hidden rounded-md shadow-soft ${isDark ? "border border-[var(--color-db-border)] bg-[var(--color-db-surface)] shadow-[var(--shadow-db-card)]" : "bg-bg-card"}`}
        >
          {error && (
            <li
              role="option"
              aria-disabled="true"
              aria-selected={false}
              className={`px-4 py-3 text-sm ${isDark ? "text-[var(--color-db-red)]" : "text-status-rented"}`}
            >
              <span role="alert">{error}</span>
            </li>
          )}
          {loading && results.length === 0 && (
            <li
              role="option"
              aria-disabled="true"
              aria-selected={false}
              className={`px-4 py-3 text-sm ${isDark ? "text-[var(--color-db-text-secondary)]" : "text-text-sec"}`}
            >
              Searching...
            </li>
          )}
          {results.map((result, index) => (
            <li
              key={result.place_id ?? result.osm_id}
              id={`searchbar-option-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={`cursor-pointer px-4 py-3 text-sm transition-colors ${
                isDark
                  ? index === activeIndex
                    ? "bg-[var(--color-db-surface-alt)] text-[var(--color-db-text-primary)]"
                    : "text-[var(--color-db-text-secondary)] hover:bg-[var(--color-db-surface-alt)]"
                  : index === activeIndex
                    ? "bg-bg-main text-text-pri"
                    : "text-text-sec hover:bg-bg-main"
              }`}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseDown={(e) => {
                e.preventDefault();
                selectResult(result);
              }}
            >
              {result.display_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default SearchBar;
