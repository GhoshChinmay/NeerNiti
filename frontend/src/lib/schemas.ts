import { z } from "zod";

export const GeometryPointSchema = z.object({
  type: z.literal("Point"),
  coordinates: z.tuple([z.number(), z.number()]),
});

export const RegionPropertiesSchema = z.object({
  region_id: z.string(),
  region_name: z.string(),
  region_type: z.string(),
  state: z.string(),
});

export const RegionFeatureSchema = z.object({
  type: z.literal("Feature"),
  geometry: z.object({
    type: z.string(),
    coordinates: z.any(),
  }),
  properties: RegionPropertiesSchema,
});

export const RegionsSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(RegionFeatureSchema),
});

export const WellReadingSchema = z.object({
  date: z.string(),
  water_level_m: z.number(),
});

export const WellPropertiesSchema = z.object({
  well_id: z.string(),
  station_code: z.string().nullable(),
  source: z.string(),
  latest_water_level_m: z.number().nullable(),
  reading_date: z.string().nullable(),
  reading_history: z.array(WellReadingSchema).default([]),
});

export const WellFeatureSchema = z.object({
  type: z.literal("Feature"),
  geometry: GeometryPointSchema,
  properties: WellPropertiesSchema,
});

export const WellsSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(WellFeatureSchema),
});

export const RecommendationPropertiesSchema = z.object({
  recommendation_id: z.string(),
  final_suitability_score: z.number(),
  structure_type: z.string(),
  risk_category: z.enum(["Low", "Medium", "High"]).nullable().optional().default("Low"),
  explanation_text: z.string().default("No explanation available."),
  sub_scores: z.object({
    slope_score: z.number().default(0),
    ndvi_score: z.number().default(0),
    water_level_score: z.number().default(0),
  }).default({ slope_score: 0, ndvi_score: 0, water_level_score: 0 }),
  created_at: z.string().nullable().optional(),
});

export const RecommendationFeatureSchema = z.object({
  type: z.literal("Feature"),
  geometry: GeometryPointSchema,
  properties: RecommendationPropertiesSchema,
});

export const RecommendationsSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(RecommendationFeatureSchema),
});

export const VerificationLogSchema = z.object({
  date: z.string(),
  predicted_m: z.number(),
  actual_m: z.number(),
  deviation_pct: z.number(),
  status: z.string(),
});

export const StructurePropertiesSchema = z.object({
  structure_id: z.string(),
  structure_type: z.string(),
  construction_date: z.string().nullable(),
  current_status: z.string(),
  verification_logs: z.array(VerificationLogSchema).default([]),
});

export const StructureFeatureSchema = z.object({
  type: z.literal("Feature"),
  geometry: GeometryPointSchema,
  properties: StructurePropertiesSchema,
});

export const StructuresSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(StructureFeatureSchema),
});
