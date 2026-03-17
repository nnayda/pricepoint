import { useMemo, useState } from "react";
import type { FeatureCatalogEntry } from "../../types";

interface FeatureCatalogTableProps {
  features: FeatureCatalogEntry[];
  categories: string[];
}

function FeatureCatalogTable({ features, categories }: FeatureCatalogTableProps) {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [sortField, setSortField] = useState<"name" | "category" | "sql_type" | "source">("name");
  const [sortAsc, setSortAsc] = useState(true);

  const filtered = useMemo(() => {
    let result = features;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          f.category.toLowerCase().includes(q) ||
          f.source.toLowerCase().includes(q),
      );
    }
    if (activeCategory) {
      result = result.filter((f) => f.category === activeCategory);
    }
    result = [...result].sort((a, b) => {
      const av = a[sortField].toLowerCase();
      const bv = b[sortField].toLowerCase();
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    return result;
  }, [features, search, activeCategory, sortField, sortAsc]);

  function handleSort(field: typeof sortField) {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  }

  const sortIndicator = (field: typeof sortField) =>
    sortField === field ? (sortAsc ? " \u25B2" : " \u25BC") : "";

  return (
    <div>
      {/* Search */}
      <input
        type="text"
        placeholder="Search features..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        aria-label="Search features"
        className="mb-3 w-full rounded-[var(--radius-db-sm)] border border-[var(--th-border-subtle)] px-3 py-2 text-sm"
        style={{
          backgroundColor: "var(--th-bg-surface)",
          color: "var(--color-db-text-primary)",
        }}
      />

      {/* Category chips */}
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by category">
        <button
          type="button"
          onClick={() => setActiveCategory(null)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            activeCategory === null
              ? "bg-[var(--color-db-accent)] text-white"
              : "border border-[var(--th-border-subtle)] text-[var(--color-db-text-secondary)] hover:text-[var(--color-db-text-primary)]"
          }`}
          style={activeCategory !== null ? { backgroundColor: "var(--th-bg-surface)" } : {}}
        >
          All ({features.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeCategory === cat
                ? "bg-[var(--color-db-accent)] text-white"
                : "border border-[var(--th-border-subtle)] text-[var(--color-db-text-secondary)] hover:text-[var(--color-db-text-primary)]"
            }`}
            style={activeCategory !== cat ? { backgroundColor: "var(--th-bg-surface)" } : {}}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--th-border-subtle)]">
              {(["name", "category", "sql_type", "source"] as const).map((field) => (
                <th
                  key={field}
                  className="cursor-pointer px-3 py-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-primary)]"
                  onClick={() => handleSort(field)}
                >
                  {field === "sql_type" ? "Type" : field.charAt(0).toUpperCase() + field.slice(1)}
                  {sortIndicator(field)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((f) => (
              <tr key={f.name} className="group border-b border-[var(--th-border-subtle)]">
                <td className="px-3 py-2">
                  <button
                    type="button"
                    onClick={() => setExpandedRow(expandedRow === f.name ? null : f.name)}
                    className="font-mono text-xs text-[var(--color-db-accent)] hover:underline"
                  >
                    {f.name}
                  </button>
                  {expandedRow === f.name && (
                    <div className="mt-2 rounded border border-[var(--th-border-subtle)] p-3 text-xs">
                      <p className="text-[var(--color-db-text-secondary)]">
                        <span className="font-semibold">Derivation:</span> {f.derivation}
                      </p>
                      <p className="mt-1 text-[var(--color-db-text-secondary)]">
                        <span className="font-semibold">Example:</span>{" "}
                        <code className="rounded bg-[var(--color-db-surface-alt)] px-1">
                          {f.example}
                        </code>
                      </p>
                      <p className="mt-1 text-[var(--color-db-text-secondary)]">
                        <span className="font-semibold">Default:</span>{" "}
                        <code className="rounded bg-[var(--color-db-surface-alt)] px-1">
                          {f.default || "NULL"}
                        </code>
                      </p>
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-[var(--color-db-text-secondary)]">
                  {f.category}
                </td>
                <td className="px-3 py-2">
                  <code className="text-xs text-[var(--color-db-text-secondary)]">
                    {f.sql_type}
                  </code>
                </td>
                <td className="px-3 py-2 text-xs text-[var(--color-db-text-secondary)]">
                  {f.source}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="px-3 py-8 text-center text-sm text-[var(--color-db-text-tertiary)]"
                >
                  No features match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default FeatureCatalogTable;
