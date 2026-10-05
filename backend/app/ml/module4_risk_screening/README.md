# Module 4: Water Quality Contamination Risk Screener

## Overview
Module 4 screens every candidate recharge site for chemical and microbiological contamination risks using GIS proximity buffer analysis (distance to farmland, industrial estates, sewage lines) before recommendations are approved.

## Risk Classes
- **Low**: Optimal location far from potential surface contaminants.
- **Medium**: Moderate proximity to agricultural runoff or drainage channel.
- **High**: Close to industrial clusters or open sewage lines; flagged with warning overlay.

## Usage Example
```python
from app.ml.module4_risk_screening import RiskClassifier

screener = RiskClassifier()
result = screener.classify_point(lat=25.4358, lng=81.8463, district_name="Prayagraj")

print(f"Risk: {result.risk_category}, Confidence: {result.data_confidence}")
```
