# Module 3: Recharge Verification & Monitoring Engine

## Overview
Module 3 continuously evaluates post-construction groundwater levels near constructed recharge structures, using a trained Bi-LSTM neural forecast model to verify whether expected aquifer recharge is physically occurring.

## Deviation Logic
```
deviation_pct = ((actual_level_m - predicted_level_m) / predicted_level_m) * 100
status = "Underperforming" if deviation_pct > 15% else "OK"
```

## Usage Example
```python
from app.ml.module3_verification import VerificationEngine

engine = VerificationEngine(deviation_threshold=0.15)
eval_result = engine.evaluate_structure(db, structure_id=my_structure_id)

print(f"Status: {eval_result.status}, Deviation: {eval_result.deviation_pct}%")
```
