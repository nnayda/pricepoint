import type { InteriorFeatures, ExteriorFeatures, FinancialDetails } from "../../types";

interface PropertyDetailsSectionProps {
  interior: InteriorFeatures;
  exterior: ExteriorFeatures;
  financial: FinancialDetails;
}

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-text-sec">{label}</dt>
      <dd className="text-sm font-bold text-text-pri">{value}</dd>
    </div>
  );
}

function PropertyDetailsSection({ interior, exterior, financial }: PropertyDetailsSectionProps) {
  return (
    <section
      aria-label="Property details"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <h2 className="text-lg font-bold text-text-pri">Property Details</h2>

      <div className="mt-4">
        <h3 className="text-sm font-bold text-text-pri">Interior</h3>
        <dl className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <DetailItem label="Flooring" value={interior.flooring.join(", ")} />
          <DetailItem label="Appliances" value={interior.appliances.join(", ")} />
          <DetailItem label="Heating" value={interior.heating} />
          <DetailItem label="Cooling" value={interior.cooling} />
          <DetailItem label="Fireplace" value={interior.fireplace ? "Yes" : "No"} />
          {interior.basement != null && <DetailItem label="Basement" value={interior.basement} />}
        </dl>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-bold text-text-pri">Exterior</h3>
        <dl className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <DetailItem label="Roof" value={exterior.roof} />
          <DetailItem label="Siding" value={exterior.siding} />
          <DetailItem label="Foundation" value={exterior.foundation} />
          <DetailItem label="Parking" value={exterior.parking} />
          <DetailItem label="Pool" value={exterior.pool ? "Yes" : "No"} />
          <DetailItem label="Fence" value={exterior.fence} />
        </dl>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-bold text-text-pri">Financial</h3>
        <dl className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {financial.hoa_monthly != null && (
            <DetailItem label="HOA (monthly)" value={currency.format(financial.hoa_monthly)} />
          )}
          <DetailItem label="Annual Tax" value={currency.format(financial.tax_annual)} />
          <DetailItem label="Tax Year" value={String(financial.tax_year)} />
          <DetailItem label="Assessed Value" value={currency.format(financial.assessed_value)} />
        </dl>
      </div>
    </section>
  );
}

export default PropertyDetailsSection;
