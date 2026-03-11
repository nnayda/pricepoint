import type {
  DemographicContext,
  DemographicData,
  DemographicDataset,
  DemographicsApiContextData,
  DemographicsApiResponse,
  RaceDetailedBreakdown,
} from "../types";

const RACE_COLORS: Record<string, string> = {
  White: "#6366f1",
  Black: "#22d3ee",
  Hispanic: "#22c55e",
  Asian: "#f59e0b",
  Other: "#a855f7",
};

/** Sequential amber/gold shades for Asian sub-groups */
const ASIAN_SUBGROUP_COLORS: Record<string, string> = {
  "Asian Indian": "#f59e0b",
  Chinese: "#d97706",
  Filipino: "#b45309",
  Japanese: "#92400e",
  Korean: "#fbbf24",
  Vietnamese: "#f97316",
  "Other Asian": "#78716c",
};

function addRaceColors(
  race: { label: string; value: number }[],
): { label: string; value: number; color: string }[] {
  return race.map((entry) => ({
    ...entry,
    color: RACE_COLORS[entry.label] ?? "#6b7280",
  }));
}

function addSubgroupColors(
  raceDetailed?: Record<
    string,
    {
      race_category: string;
      total: number;
      subgroups: { label: string; value: number; percentage: number }[];
    }
  >,
): Record<string, RaceDetailedBreakdown> | undefined {
  if (!raceDetailed) return undefined;

  const result: Record<string, RaceDetailedBreakdown> = {};
  for (const [category, breakdown] of Object.entries(raceDetailed)) {
    result[category] = {
      race_category: breakdown.race_category,
      total: breakdown.total,
      subgroups: breakdown.subgroups.map((sg) => ({
        ...sg,
        color: ASIAN_SUBGROUP_COLORS[sg.label] ?? "#9ca3af",
      })),
    };
  }
  return result;
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
    race_detailed: addSubgroupColors(ctx.race_detailed),
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
