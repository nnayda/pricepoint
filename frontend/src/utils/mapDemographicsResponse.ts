import type {
  DemographicContext,
  DemographicData,
  DemographicDataset,
  DemographicsApiContextData,
  DemographicsApiResponse,
} from "../types";

const RACE_COLORS: Record<string, string> = {
  White: "#6366f1",
  Black: "#22d3ee",
  Hispanic: "#22c55e",
  Asian: "#f59e0b",
  Other: "#a855f7",
};

function addRaceColors(
  race: { label: string; value: number }[],
): { label: string; value: number; color: string }[] {
  return race.map((entry) => ({
    ...entry,
    color: RACE_COLORS[entry.label] ?? "#6b7280",
  }));
}

function apiContextToDataset(ctx: DemographicsApiContextData): DemographicDataset {
  return {
    race_ethnicity: addRaceColors(ctx.race_ethnicity),
    age_distribution: ctx.age_distribution,
    median_income: ctx.median_income,
    income_brackets: ctx.income_brackets,
    home_ownership_rate: ctx.home_ownership_rate,
    median_home_value: ctx.median_home_value,
    population: ctx.population,
    population_trend: ctx.population_trend,
    race_ethnicity_trend: ctx.race_ethnicity_trend,
    age_distribution_trend: ctx.age_distribution_trend,
    income_trend: ctx.income_trend,
    home_ownership_trend: ctx.home_ownership_trend,
    median_age_trend: ctx.median_age_trend,
  };
}

const CONTEXT_KEYS: DemographicContext[] = [
  "subdivision",
  "block_group",
  "neighborhood",
  "town",
  "county",
];

export function mapDemographicsResponse(resp: DemographicsApiResponse): DemographicData {
  const contexts = {} as Record<DemographicContext, DemographicDataset>;

  for (const key of CONTEXT_KEYS) {
    const apiCtx = resp.contexts[key];
    contexts[key] = apiCtx ? apiContextToDataset(apiCtx) : emptyDataset();
  }

  // Use neighborhood as the top-level snapshot
  const nb = contexts.neighborhood;

  // Benchmarks
  const benchmarks: Record<string, DemographicDataset> = {};
  for (const [key, val] of Object.entries(resp.benchmarks)) {
    benchmarks[key] = apiContextToDataset(val);
  }

  return {
    geography_level: "tract",
    contexts,
    race_ethnicity: nb.race_ethnicity,
    age_distribution: nb.age_distribution,
    median_income: nb.median_income,
    income_brackets: nb.income_brackets,
    home_ownership_rate: nb.home_ownership_rate,
    median_home_value: nb.median_home_value,
    population: nb.population,
    population_trend: nb.population_trend,
    race_ethnicity_trend: nb.race_ethnicity_trend,
    age_distribution_trend: nb.age_distribution_trend,
    income_trend: nb.income_trend,
    home_ownership_trend: nb.home_ownership_trend,
    median_age_trend: nb.median_age_trend,
    benchmarks,
  };
}

function emptyDataset(): DemographicDataset {
  return {
    race_ethnicity: [],
    age_distribution: [],
    median_income: 0,
    income_brackets: [],
    home_ownership_rate: 0,
    median_home_value: 0,
    population: 0,
    population_trend: [],
    race_ethnicity_trend: [],
    age_distribution_trend: [],
    income_trend: [],
    home_ownership_trend: [],
    median_age_trend: [],
  };
}
