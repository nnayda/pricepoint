interface PropertyDescriptionProps {
  highlights: string[];
  description: string;
}

function PropertyDescription({ highlights, description }: PropertyDescriptionProps) {
  return (
    <section
      aria-label="Property description"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <h2 className="text-lg font-bold text-text-pri">Description</h2>

      {highlights.length > 0 && (
        <ul className="mt-3 space-y-1" aria-label="Property highlights">
          {highlights.map((h, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-text-sec">
              <span className="mt-0.5 text-brand-blue" aria-hidden="true">
                &#x2022;
              </span>
              {h}
            </li>
          ))}
        </ul>
      )}

      <p className="mt-4 text-sm leading-relaxed text-text-sec">{description}</p>
    </section>
  );
}

export default PropertyDescription;
