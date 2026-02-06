import type { PropertyDetails } from "../../types";

interface PropertyHeaderProps {
  property: PropertyDetails;
}

const fmt = new Intl.NumberFormat("en-US");

function PropertyHeader({ property }: PropertyHeaderProps) {
  const stats = [
    { label: "Beds", value: property.bedrooms },
    { label: "Baths", value: property.bathrooms },
    { label: "Sq Ft", value: fmt.format(property.sqft) },
    { label: "Lot", value: `${fmt.format(property.lot_size_sqft)} sqft` },
    { label: "Built", value: property.year_built },
    { label: "Type", value: property.property_type },
  ];

  return (
    <section
      aria-label="Property header"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <div className="flex items-start gap-4">
        {property.images.length > 0 ? (
          <img
            src={property.images.find((i) => i.is_primary)?.url ?? property.images[0].url}
            alt={property.images.find((i) => i.is_primary)?.alt ?? property.images[0].alt}
            className="h-16 w-16 rounded-md object-cover sm:h-20 sm:w-20"
          />
        ) : (
          <div
            className="flex h-16 w-16 items-center justify-center rounded-md bg-bg-main text-2xl text-text-sec sm:h-20 sm:w-20"
            aria-hidden="true"
          >
            &#8962;
          </div>
        )}
        <div>
          <h1 className="text-xl font-bold text-text-pri sm:text-2xl">{property.address}</h1>
          <p className="mt-1 text-sm font-medium text-text-sec">
            {property.city}, {property.state} {property.zip_code}
          </p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-4 sm:gap-6" role="list" aria-label="Property stats">
        {stats.map((s) => (
          <div key={s.label} role="listitem" className="text-center">
            <p className="text-lg font-bold text-text-pri">{s.value}</p>
            <p className="text-xs font-medium text-text-sec">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default PropertyHeader;
