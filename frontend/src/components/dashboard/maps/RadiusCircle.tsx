import { Circle } from "react-leaflet";

const MILES_TO_METERS = 1609.34;

interface RadiusCircleProps {
  center: [number, number];
  radiusMiles: number;
}

function RadiusCircle({ center, radiusMiles }: RadiusCircleProps) {
  return (
    <Circle
      center={center}
      radius={radiusMiles * MILES_TO_METERS}
      pathOptions={{
        color: "var(--color-db-text-tertiary, #94A3B8)",
        weight: 1.5,
        dashArray: "6 4",
        fillColor: "var(--color-db-text-tertiary, #94A3B8)",
        fillOpacity: 0.04,
      }}
      interactive={false}
    />
  );
}

export default RadiusCircle;
