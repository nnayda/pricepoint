import { useState } from "react";
import { usePoiPreferences } from "../hooks/usePoiPreferences";
import { useMortgageDefaults } from "../hooks/useMortgageDefaults";

function SettingsPage() {
  const { preferences, togglePoi, toggleCategory, addCustomPoi, removeCustomPoi } =
    usePoiPreferences();
  const { defaults, updateDefaults } = useMortgageDefaults();

  const [newPoiName, setNewPoiName] = useState("");
  const [newPoiCategory, setNewPoiCategory] = useState("Grocery");

  const categories = [...new Set(preferences.map((p) => p.category))];

  function handleAddPoi(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newPoiName.trim();
    if (!trimmed) return;
    addCustomPoi(trimmed, newPoiCategory);
    setNewPoiName("");
  }

  return (
    <div className="mx-auto max-w-2xl space-y-grid p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-text-pri">Settings</h1>

      {/* POI Preferences */}
      <section
        aria-label="POI preferences"
        className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
      >
        <h2 className="text-lg font-bold text-text-pri">POI Preferences</h2>
        <p className="mt-1 text-sm text-text-sec">
          Choose which points of interest appear on the map.
        </p>

        <div className="mt-4 space-y-4">
          {categories.map((cat) => {
            const inCat = preferences.filter((p) => p.category === cat);
            const allEnabled = inCat.every((p) => p.enabled);

            return (
              <div key={cat}>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleCategory(cat)}
                    role="switch"
                    aria-checked={allEnabled}
                    aria-label={`Toggle all ${cat}`}
                    className={`relative h-5 w-9 rounded-full transition-colors ${
                      allEnabled ? "bg-brand-blue" : "bg-status-vacant"
                    }`}
                  >
                    <span
                      className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                        allEnabled ? "translate-x-4" : ""
                      }`}
                    />
                  </button>
                  <span className="text-sm font-bold text-text-pri">{cat}</span>
                </div>

                <div className="ml-6 mt-2 space-y-2">
                  {inCat.map((poi) => (
                    <div key={poi.id} className="flex items-center gap-2">
                      <button
                        onClick={() => togglePoi(poi.id)}
                        role="switch"
                        aria-checked={poi.enabled}
                        aria-label={`Toggle ${poi.name}`}
                        className={`relative h-5 w-9 rounded-full transition-colors ${
                          poi.enabled ? "bg-brand-blue" : "bg-status-vacant"
                        }`}
                      >
                        <span
                          className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                            poi.enabled ? "translate-x-4" : ""
                          }`}
                        />
                      </button>
                      <span className="text-sm text-text-pri">{poi.name}</span>
                      {poi.isCustom && (
                        <button
                          onClick={() => removeCustomPoi(poi.id)}
                          aria-label={`Remove ${poi.name}`}
                          className="ml-auto text-xs text-status-rented hover:underline"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <form onSubmit={handleAddPoi} className="mt-4 flex items-end gap-2">
          <div className="flex-1">
            <label htmlFor="poi-name" className="block text-xs font-medium text-text-sec">
              Name
            </label>
            <input
              id="poi-name"
              type="text"
              value={newPoiName}
              onChange={(e) => setNewPoiName(e.target.value)}
              placeholder="e.g. Aldi"
              className="mt-1 w-full rounded-md border border-status-vacant bg-bg-main px-3 py-1.5 text-sm text-text-pri placeholder:text-text-sec focus:border-brand-blue focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="poi-category" className="block text-xs font-medium text-text-sec">
              Category
            </label>
            <select
              id="poi-category"
              value={newPoiCategory}
              onChange={(e) => setNewPoiCategory(e.target.value)}
              className="mt-1 rounded-md border border-status-vacant bg-bg-main px-3 py-1.5 text-sm text-text-pri focus:border-brand-blue focus:outline-none"
            >
              <option>Grocery</option>
              <option>Retail</option>
              <option>Pharmacy</option>
              <option>Restaurant</option>
            </select>
          </div>
          <button
            type="submit"
            className="rounded-md bg-brand-blue px-4 py-1.5 text-sm font-medium text-white hover:opacity-90"
          >
            Add
          </button>
        </form>
      </section>

      {/* Mortgage Defaults */}
      <section
        aria-label="Mortgage defaults"
        className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
      >
        <h2 className="text-lg font-bold text-text-pri">Mortgage Defaults</h2>
        <p className="mt-1 text-sm text-text-sec">
          Set default values for the mortgage calculator.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="default-down" className="block text-xs font-medium text-text-sec">
              Down Payment %
            </label>
            <input
              id="default-down"
              type="number"
              min={0}
              max={100}
              step={1}
              value={defaults.downPaymentPercent}
              onChange={(e) => updateDefaults({ downPaymentPercent: Number(e.target.value) })}
              className="mt-1 w-full rounded-md border border-status-vacant bg-bg-main px-3 py-1.5 text-sm text-text-pri focus:border-brand-blue focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="default-rate" className="block text-xs font-medium text-text-sec">
              Interest Rate %
            </label>
            <input
              id="default-rate"
              type="number"
              min={0}
              max={20}
              step={0.125}
              value={defaults.interestRate}
              onChange={(e) => updateDefaults({ interestRate: Number(e.target.value) })}
              className="mt-1 w-full rounded-md border border-status-vacant bg-bg-main px-3 py-1.5 text-sm text-text-pri focus:border-brand-blue focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="default-term" className="block text-xs font-medium text-text-sec">
              Loan Term (years)
            </label>
            <input
              id="default-term"
              type="number"
              min={5}
              max={30}
              step={5}
              value={defaults.loanTermYears}
              onChange={(e) => updateDefaults({ loanTermYears: Number(e.target.value) })}
              className="mt-1 w-full rounded-md border border-status-vacant bg-bg-main px-3 py-1.5 text-sm text-text-pri focus:border-brand-blue focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="default-insurance" className="block text-xs font-medium text-text-sec">
              Annual Insurance ($)
            </label>
            <input
              id="default-insurance"
              type="number"
              min={0}
              step={100}
              value={defaults.annualInsurance}
              onChange={(e) => updateDefaults({ annualInsurance: Number(e.target.value) })}
              className="mt-1 w-full rounded-md border border-status-vacant bg-bg-main px-3 py-1.5 text-sm text-text-pri focus:border-brand-blue focus:outline-none"
            />
          </div>
        </div>
      </section>
    </div>
  );
}

export default SettingsPage;
