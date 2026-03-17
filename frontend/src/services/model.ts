import axios from "axios";
import type { FeatureCatalogResponse, ModelMethodologyResponse } from "../types";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export async function getModelMethodology(): Promise<ModelMethodologyResponse> {
  const { data } = await client.get<ModelMethodologyResponse>("/api/model/methodology");
  return data;
}

export async function getFeatureCatalog(): Promise<FeatureCatalogResponse> {
  const { data } = await client.get<FeatureCatalogResponse>("/api/model/features");
  return data;
}

export function getModelArtifactUrl(artifactPath: string): string {
  return `/api/model/artifact/${artifactPath}`;
}
