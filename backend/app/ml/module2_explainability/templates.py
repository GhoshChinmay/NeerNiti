"""
NeerNiti — Module 2: Plain Language Template Engine
Transforms raw SHAP contribution values into deterministic, human-readable sentences.
"""

from collections.abc import Sequence

FEATURE_PHRASE_LOOKUP: dict[str, tuple[str, str]] = {
    "slope_deg": ("steep terrain slope", "gentle terrain slope"),
    "drainage_density": ("high natural drainage density", "sparse drainage density"),
    "ndvi": ("dense surface vegetation", "sparse vegetation index"),
    "rainfall_mm": ("strong regional precipitation", "lower seasonal rainfall"),
    "distance_to_river_m": ("close proximity to river network", "high distance from surface water bodies"),
    "depth_to_groundwater_m": ("deep aquifer holding capacity", "shallow water table"),
    "geology_hardrock": ("fractured hard-rock formation", "alluvial sediment foundation"),
    "soil_clay_pct": ("clay-rich soil layer", "porous sandy soil texture"),
}


def render_explanation_template(
    suitability_score: float,
    top_contributions: Sequence[tuple[str, float]],
) -> str:
    """Renders a deterministic plain-language summary sentence.

    Template:
    "{High/Moderate/Low} suitability due to {factor_1} and {factor_2}."
      + optional: " Minor negative contribution from {factor_3}."
    """
    tier = "High" if suitability_score >= 0.75 else "Moderate" if suitability_score >= 0.50 else "Low"

    positives = [feat for feat, val in top_contributions if val > 0]
    negatives = [feat for feat, val in top_contributions if val <= 0]

    pos_phrases = [FEATURE_PHRASE_LOOKUP.get(f, (f, f))[0] for f in positives[:2]]
    neg_phrases = [FEATURE_PHRASE_LOOKUP.get(f, (f, f))[1] for f in negatives[:1]]

    if pos_phrases:
        reason = f"{tier} suitability due to {' and '.join(pos_phrases)}."
    else:
        reason = f"{tier} suitability across evaluated hydrogeological metrics."

    if neg_phrases:
        reason += f" Minor limitation from {neg_phrases[0]}."

    return reason
