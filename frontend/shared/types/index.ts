export const HIGH_MIN = 0.85;
export const MEDIUM_MIN = 0.6;

export type ConfidenceBand = "HIGH" | "MEDIUM" | "LOW";

export function confidenceBand(score: number | null | undefined): ConfidenceBand | null {
  if (score == null) return null;
  if (score >= HIGH_MIN) return "HIGH";
  if (score >= MEDIUM_MIN) return "MEDIUM";
  return "LOW";
}

export type ParcelStatus = "ai_processed" | "needs_review" | "verified" | "rejected";
export type ParcelSource = "ai_extracted" | "existing_gis" | "field_verified";

export interface GeoJSONPolygon {
  type: "Polygon";
  coordinates: number[][][];
}

export interface Parcel {
  id: string;
  project_id: string;
  geom: GeoJSONPolygon;
  source: ParcelSource | string;
  status: ParcelStatus | string;
  confidence_score: number | null;
  confidence_band: ConfidenceBand | null;
  health_score: number | null;
  land_use: string | null;
  area_sqm: number | null;
  version: number;
}

export interface Project {
  id: string;
  name: string;
  status: string;
  created_at?: string;
  demo?: boolean;
}

export interface Explanation {
  parcel_id: string;
  explanation: string;
  confidence_score: number | null;
  health_score: number | null;
  components: { component: string; score: number; explanation: string }[];
}

export interface SurveyQueueItem {
  id: string;
  parcel_id: string;
  priority_score: number;
  reason: string;
  status: string;
  assigned_to: string | null;
}

export interface Vendor {
  id: string;
  name: string;
  services: string;
  contact_info: string | null;
}
