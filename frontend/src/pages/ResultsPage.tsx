import { useSearchParams, Link } from "react-router-dom";
import { usePropertyData } from "../hooks/usePropertyData";
import PropertyHeader from "../components/PropertyHeader/PropertyHeader";
import ValueSection from "../components/ValueSection/ValueSection";
import PropertyDescription from "../components/PropertyDescription/PropertyDescription";
import SchoolsSection from "../components/SchoolsSection/SchoolsSection";
import PropertyDetailsSection from "../components/PropertyDetailsSection/PropertyDetailsSection";
import SaleTaxHistoryChart from "../components/SaleTaxHistoryChart/SaleTaxHistoryChart";
import ClimateRiskSection from "../components/ClimateRiskSection/ClimateRiskSection";
import MortgageCalculator from "../components/MortgageCalculator/MortgageCalculator";
import PropertyMap from "../components/PropertyMap/PropertyMap";
import SectionSidebar from "../components/SectionSidebar/SectionSidebar";
import SkeletonResultsPage from "../components/SkeletonResultsPage/SkeletonResultsPage";

const SIDEBAR_SECTIONS = [
  { id: "property-header", icon: "\u2302", tooltip: "Property" },
  { id: "valuation", icon: "$", tooltip: "Valuation" },
  { id: "description", icon: "\u2261", tooltip: "Description" },
  { id: "schools", icon: "\u{1F4D6}", tooltip: "Schools" },
  { id: "details", icon: "\u2630", tooltip: "Details" },
  { id: "history", icon: "\u{1F4C8}", tooltip: "History" },
  { id: "climate", icon: "\u2601", tooltip: "Climate" },
  { id: "mortgage", icon: "\u{1F5A9}", tooltip: "Mortgage" },
  { id: "map", icon: "\u{1F5FA}", tooltip: "Map" },
];

function ResultsPage() {
  const [searchParams] = useSearchParams();
  const address = searchParams.get("address") ?? "";
  const lat = searchParams.get("lat") ?? "";
  const lon = searchParams.get("lon") ?? "";

  const { data, loading, error } = usePropertyData(
    parseFloat(lat) || 0,
    parseFloat(lon) || 0,
    address,
  );

  if (!address) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4">
        <div className="flex max-w-md flex-col items-center gap-4 text-center">
          <h1 className="text-2xl font-bold text-text-pri">No address provided</h1>
          <p className="text-base font-medium text-text-sec">
            Please search for a property to see its forecast.
          </p>
          <Link
            to="/"
            className="rounded-pill bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Go to search
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return <SkeletonResultsPage />;
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4">
        <div className="flex max-w-md flex-col items-center gap-4 rounded-lg bg-bg-card/80 p-5 text-center shadow-soft backdrop-blur-md sm:p-8">
          <h1 className="text-2xl font-bold text-text-pri">Something went wrong</h1>
          <p className="text-base font-medium text-status-rented">{error}</p>
          <Link
            to="/"
            className="rounded-pill bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Try another address
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="flex flex-1 px-4 py-4 sm:py-8">
      <SectionSidebar sections={SIDEBAR_SECTIONS} />

      <main className="mx-auto w-full max-w-7xl space-y-grid lg:ml-16">
        <Link to="/" className="text-sm font-medium text-text-sec hover:text-brand-blue">
          &larr; Back to search
        </Link>

        {/* Zone A: Hero property header */}
        <div id="property-header">
          <PropertyHeader property={data.property} />
        </div>

        {/* Zone B: Dashboard grid — cards left, sticky map right */}
        <div className="grid grid-cols-1 gap-grid lg:grid-cols-12">
          <div className="space-y-grid lg:col-span-5">
            <div id="valuation">
              <ValueSection valuation={data.valuation} />
            </div>

            <div id="description">
              <PropertyDescription
                highlights={data.property.highlights}
                description={data.property.description}
              />
            </div>

            <div id="schools">
              <SchoolsSection schools={data.schools} />
            </div>

            <div id="details">
              <PropertyDetailsSection
                interior={data.interior}
                exterior={data.exterior}
                financial={data.financial}
              />
            </div>

            <div id="climate">
              <ClimateRiskSection climateRisk={data.climate_risk} />
            </div>
          </div>

          <div className="lg:col-span-7">
            <div id="map" className="lg:sticky lg:top-4">
              <PropertyMap lat={parseFloat(lat)} lon={parseFloat(lon)} address={address} />
            </div>
          </div>
        </div>

        {/* Zone C: Full-width bottom sections */}
        <div id="history">
          <SaleTaxHistoryChart saleHistory={data.sale_history} taxHistory={data.tax_history} />
        </div>

        <div id="mortgage">
          <MortgageCalculator
            listedPrice={data.valuation.listed_price ?? data.valuation.predicted_value ?? 0}
            annualTax={data.financial.tax_annual}
            monthlyHoa={data.financial.hoa_monthly ?? 0}
          />
        </div>
      </main>
    </div>
  );
}

export default ResultsPage;
