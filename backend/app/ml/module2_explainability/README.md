# Module 2: SHAP Explainability Engine

## Overview
Module 2 guarantees that every AI site recommendation produces a deterministic, human-readable justification using SHAP `TreeExplainer` feature attribution.

## Key Features
- Exact Shapley value breakdown across all input features.
- Deterministic template rendering via configurable phrase dictionary (no hallucination / no external LLM cost).
- Zero-prediction-without-explanation enforcement (PRD Rule #2).

## Usage Example
```python
from app.ml.module2_explainability import SHAPExplainer

explainer = SHAPExplainer(model, feature_names)
result = explainer.explain(feature_vector, suitability_score=0.91)

print("Summary:", result.plain_text_summary)
print("Top factors:", result.top_contributions)
```
