import type { FeatureCollection, Feature, Polygon } from "geojson";

/** Simple boundary polygons per geographic context, centred around ~35.57, -78.79 */
export const MOCK_BOUNDARIES: Record<string, Feature<Polygon>> = {
  subdivision: {
    type: "Feature",
    properties: { name: "Heritage Oaks" },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [-78.798, 35.575],
          [-78.782, 35.575],
          [-78.782, 35.565],
          [-78.798, 35.565],
          [-78.798, 35.575],
        ],
      ],
    },
  },
  neighborhood: {
    type: "Feature",
    properties: { name: "South Lakes" },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [-78.81, 35.585],
          [-78.77, 35.585],
          [-78.77, 35.555],
          [-78.81, 35.555],
          [-78.81, 35.585],
        ],
      ],
    },
  },
  town: {
    type: "Feature",
    properties: { name: "Fuquay-Varina" },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [-78.84, 35.61],
          [-78.74, 35.61],
          [-78.74, 35.53],
          [-78.84, 35.53],
          [-78.84, 35.61],
        ],
      ],
    },
  },
};

/** Neighbouring census tracts with demographic values for choropleth colouring */
export const MOCK_CHOROPLETH: FeatureCollection<Polygon> = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: {
        tract: "0541.01",
        median_income: 92400,
        ownership_rate: 84.2,
        population: 3200,
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-78.81, 35.585],
            [-78.79, 35.585],
            [-78.79, 35.57],
            [-78.81, 35.57],
            [-78.81, 35.585],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        tract: "0541.02",
        median_income: 78500,
        ownership_rate: 72.4,
        population: 4100,
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-78.79, 35.585],
            [-78.77, 35.585],
            [-78.77, 35.57],
            [-78.79, 35.57],
            [-78.79, 35.585],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        tract: "0542.01",
        median_income: 65200,
        ownership_rate: 61.8,
        population: 3800,
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-78.81, 35.57],
            [-78.79, 35.57],
            [-78.79, 35.555],
            [-78.81, 35.555],
            [-78.81, 35.57],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        tract: "0542.02",
        median_income: 71800,
        ownership_rate: 68.5,
        population: 2950,
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-78.79, 35.57],
            [-78.77, 35.57],
            [-78.77, 35.555],
            [-78.79, 35.555],
            [-78.79, 35.57],
          ],
        ],
      },
    },
  ],
};
