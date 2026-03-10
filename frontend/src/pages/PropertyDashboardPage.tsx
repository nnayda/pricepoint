import { useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import DashboardLayout from "../components/dashboard/DashboardLayout";
import DataRequestBanner from "../components/DataRequestBanner";
import { useDemographics } from "../hooks/useDemographics";
import { useFeatureAttributions } from "../hooks/useFeatureAttributions";
import {
  useNeighborhoodProperties,
  useNeighborhoodValuation,
  useNeighborhoodValuationHistory,
} from "../hooks/useNeighborhoodValuation";
import { usePois } from "../hooks/usePois";
import { usePropertyLookup } from "../hooks/usePropertyLookup";
import { useSavedPoisNearby } from "../hooks/useSavedPois";
import { buildEmptyDashboardData } from "../data/emptyDashboardData";
import { mockDashboardData } from "../data/mockDashboardData";
import type { DashboardPoi, PointOfInterest, PriceHistoryPoint } from "../types";
import { mapDemographicsResponse } from "../utils/mapDemographicsResponse";
import { mapPropertyResponse } from "../utils/mapPropertyResponse";

function PropertyDashboardPage() {
  const { address } = useParams<{ address: string }>();
  const [searchParams] = useSearchParams();
  const lat = searchParams.get("lat") ? Number(searchParams.get("lat")) : null;
  const lon = searchParams.get("lon") ? Number(searchParams.get("lon")) : null;
  const decodedAddress = address ? decodeURIComponent(address) : null;

  const { data, loading, notFound, error } = usePropertyLookup(lat, lon, decodedAddress);
  const { data: shapData } = useFeatureAttributions(data?.listing_id ?? null);
  const { data: demoApi } = useDemographics(lat, lon);
  const { data: neighborhoodVal } = useNeighborhoodValuation(lat, lon);
  const { data: neighborhoodHistory } = useNeighborhoodValuationHistory(lat, lon);
  const { data: neighborhoodProps } = useNeighborhoodProperties(lat, lon);

  const { data: poisData } = usePois(lat, lon);
  const { groups: savedPoiGroups } = useSavedPoisNearby(lat, lon);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const dashboardData = useMemo(() => {
    let result: ReturnType<typeof mapPropertyResponse>;
    if (data) {
      result = mapPropertyResponse(data);
    } else if (notFound && decodedAddress && lat != null && lon != null) {
      result = buildEmptyDashboardData(decodedAddress, lat, lon);
    } else {
      result = mockDashboardData;
    }

    if (demoApi) {
      result = { ...result, demographics: mapDemographicsResponse(demoApi) };
    }
    if (neighborhoodVal && neighborhoodVal.median_value != null) {
      result = {
        ...result,
        valuation: {
          ...result.valuation,
          neighborhood_median: neighborhoodVal.median_value,
          neighborhood_max: neighborhoodVal.max_value ?? result.valuation.neighborhood_max,
        },
      };
    }
    // Merge neighborhood history medians into price_history points
    if (neighborhoodHistory && neighborhoodHistory.monthly_medians.length > 0) {
      const medianMap = new Map(
        neighborhoodHistory.monthly_medians.map((m) => [m.date, m.median_value]),
      );
      const merged: PriceHistoryPoint[] = result.price_history.map((pt) => ({
        ...pt,
        neighborhood_median: medianMap.get(pt.date) ?? pt.neighborhood_median,
      }));
      // Add any neighborhood months not already in price_history
      for (const m of neighborhoodHistory.monthly_medians) {
        if (!merged.some((pt) => pt.date === m.date)) {
          merged.push({ date: m.date, neighborhood_median: m.median_value });
        }
      }
      merged.sort((a, b) => a.date.localeCompare(b.date));
      result = { ...result, price_history: merged };
    }
    if (neighborhoodProps && neighborhoodProps.properties.length > 0) {
      result = { ...result, neighborhood_properties: neighborhoodProps.properties };
    }
    if (shapData && shapData.length > 0) {
      result = {
        ...result,
        shap_features: shapData.map((fa) => ({
          feature: fa.feature,
          display_name: fa.display_name,
          impact_dollars: fa.impact_dollars,
          group: fa.group ?? "Other",
        })),
      };
    }
    // Map generic API POIs into DashboardPoi[]
    if (poisData && poisData.pois.length > 0) {
      const genericPois: DashboardPoi[] = poisData.pois.map((p: PointOfInterest) => ({
        id: p.id,
        name: p.name,
        category: p.category,
        subcategory: p.subcategory ?? p.category,
        lat: p.lat,
        lon: p.lon,
        distance_miles: p.distance_miles,
        drive_minutes: p.drive_minutes,
        icon: p.category.toLowerCase(),
        isSaved: false,
        address: p.address ?? undefined,
      }));
      result = { ...result, pois: genericPois };
    }

    // Merge saved POI nearby matches into the pois list
    if (savedPoiGroups.length > 0) {
      const savedPlaceIds = new Set<string>();
      const savedPois: DashboardPoi[] = savedPoiGroups.flatMap((group) =>
        group.matches.map((m) => {
          // Track the underlying Place ID to dedup from generic list
          const placeId = m.id.replace(/^SAVED-/, "");
          savedPlaceIds.add(placeId);
          return {
            id: m.id,
            name: m.name,
            category: group.user_category ?? group.display_name,
            subcategory: group.category ?? "saved",
            lat: m.lat,
            lon: m.lon,
            distance_miles: m.distance_miles,
            drive_minutes: m.drive_minutes,
            icon: "star",
            isSaved: true,
            marker_color: group.marker_color ?? undefined,
            marker_image_url: group.marker_image_url ?? undefined,
            address: m.address ?? undefined,
          };
        }),
      );
      // Remove generic POIs that overlap with saved POIs (same Place ID)
      const deduped = result.pois.filter((p) => {
        const placeId = p.id.replace(/^OVERTURE-/, "");
        return !savedPlaceIds.has(placeId);
      });
      result = { ...result, pois: [...deduped, ...savedPois] };
    }
    return result;
  }, [
    data,
    notFound,
    decodedAddress,
    lat,
    lon,
    demoApi,
    neighborhoodVal,
    neighborhoodHistory,
    neighborhoodProps,
    shapData,
    poisData,
    savedPoiGroups,
  ]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-db-bg)]">
        <div className="flex flex-col items-center gap-3">
          <div
            className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-db-accent)] border-t-transparent"
            role="status"
          >
            <span className="sr-only">Loading property data...</span>
          </div>
          <p className="text-sm text-[var(--color-db-text-secondary)]">Loading property data...</p>
        </div>
      </div>
    );
  }

  if (error || lat == null || lon == null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-db-bg)]">
        <div className="mx-4 max-w-md rounded-[var(--radius-db-lg)] border border-[var(--color-db-border)] bg-[var(--color-db-surface)] p-6 text-center">
          <p className="mb-2 text-sm font-medium text-[var(--color-db-red)]">
            {error || "Invalid property URL — missing location parameters."}
          </p>
          <a href="/" className="text-sm text-[var(--color-db-accent)] hover:underline">
            Back to search
          </a>
        </div>
      </div>
    );
  }

  const banner =
    notFound && !bannerDismissed && decodedAddress ? (
      <DataRequestBanner
        address={decodedAddress}
        lat={lat}
        lon={lon}
        onDismiss={() => setBannerDismissed(true)}
      />
    ) : undefined;

  return <DashboardLayout data={dashboardData} banner={banner} />;
}

export default PropertyDashboardPage;
