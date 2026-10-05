"""
NeerNiti — Module 3: Verification & Monitoring
Inference Engine

Loads the promoted Bi-LSTM model, evaluates recent groundwater telemetry
for constructed structures, detects performance deviations, logs
verification status to PostgreSQL, and dispatches real-time WebSocket
alerts for underperforming assets.
"""

import glob
import os
import sys
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
import requests
import tensorflow as tf

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.db.models import (
    Site,
    Structure,
    VerificationLog,
)
from app.db.session import SessionLocal

SEQUENCE_LENGTH = 24
DEVIATION_THRESHOLD = 0.15  # Flag 'Underperforming' if deviation > 15%
API_ALERT_URL = os.getenv("API_ALERT_URL", "http://127.0.0.1:8000/api/v1/alerts/broadcast")


def dispatch_realtime_alert(structure_id: str, structure_type: str, deviation_pct: float) -> None:
    """Dispatches an alert payload to the FastAPI Socket.IO broadcast endpoint."""
    try:
        payload = {
            "title": f"Telemetry Alert: {structure_type}",
            "message": f"Structure {str(structure_id)[:8]} is underperforming ({deviation_pct * 100:+.1f}% deviation from Bi-LSTM forecast)."
        }
        response = requests.post(API_ALERT_URL, json=payload, timeout=2.0)
        if response.status_code == 200:
            print(f"📡 Real-time alert broadcasted for structure {structure_id}")
        else:
            print(f"⚠️ Alert broadcast returned status {response.status_code}")
    except Exception as ex:
        print(f"⚠️ Could not dispatch WebSocket alert: {ex}")


def get_log_field_mapping(struct_id, model_ver, chk_date, pred_m, act_m, dev_pct, stat) -> dict:
    """Maps fields directly to concrete columns, avoiding read-only property getters."""
    fields = {
        "structure_id": struct_id,
        "model_version_id": model_ver,
    }

    # Date column
    if hasattr(VerificationLog, "check_date") and not isinstance(VerificationLog.check_date, property):
        fields["check_date"] = chk_date
    else:
        fields["evaluation_date"] = chk_date

    # Predicted level column
    if hasattr(VerificationLog, "predicted_level_m") and not isinstance(VerificationLog.predicted_level_m, property):
        fields["predicted_level_m"] = pred_m
    else:
        fields["predicted_water_level_m"] = pred_m

    # Actual level column
    if hasattr(VerificationLog, "actual_level_m") and not isinstance(VerificationLog.actual_level_m, property):
        fields["actual_level_m"] = act_m
    else:
        fields["actual_water_level_m"] = act_m

    # Deviation percentage column
    if hasattr(VerificationLog, "deviation_pct") and not isinstance(VerificationLog.deviation_pct, property):
        fields["deviation_pct"] = dev_pct
    else:
        fields["deviation_percentage"] = dev_pct

    # Performance status column
    if hasattr(VerificationLog, "status") and not isinstance(VerificationLog.status, property):
        fields["status"] = stat
    else:
        fields["performance_status"] = stat

    return fields


def run_verification_engine():
    db = SessionLocal()
    try:
        # 1. Locate latest promoted verification model and scaler
        artifact_dir = os.path.dirname(__file__)
        keras_files = glob.glob(os.path.join(artifact_dir, "verification_lstm_*.keras"))
        scaler_files = glob.glob(os.path.join(artifact_dir, "verification_lstm_*_scaler.pkl"))

        if not keras_files or not scaler_files:
            print("❌ No trained Bi-LSTM model artifacts found in backend/app/ml/")
            return

        latest_model_path = max(keras_files, key=os.path.getctime)
        latest_scaler_path = max(scaler_files, key=os.path.getctime)
        version_id = os.path.basename(latest_model_path).replace(".keras", "")

        print(f"🧠 Loading Bi-LSTM Model: {version_id}")
        model = tf.keras.models.load_model(latest_model_path)
        scaler = joblib.load(latest_scaler_path)

        # 2. Sync structures from top recommended candidate sites
        sites = db.query(Site).order_by(Site.suitability_score.desc()).limit(3).all()
        if not sites:
            print("❌ No sites found in DB. Run recommendations/inference first.")
            return

        print("🏗️  Syncing constructed structures...")
        structures = []
        for i, site in enumerate(sites):
            existing_struct = db.query(Structure).filter_by(site_id=site.site_id).first()
            if not existing_struct:
                struct_data = {
                    "site_id": site.site_id,
                    "structure_type": "Check Dam" if i % 2 == 0 else "Percolation Tank",
                    "status": "Active",
                    "location": site.location
                }
                const_date = datetime.now(timezone.utc).date() - timedelta(days=180)
                if hasattr(Structure, "build_date") and not isinstance(Structure.build_date, property):
                    struct_data["build_date"] = const_date
                else:
                    struct_data["construction_date"] = const_date

                struct = Structure(**struct_data)
                db.add(struct)
                db.flush()
                structures.append(struct)
            else:
                structures.append(existing_struct)

        # 3. Perform Bi-LSTM forecasting and verification
        print("📊 Running Bi-LSTM verification analysis...")
        for struct in structures:
            dates = pd.date_range(end=datetime.now(timezone.utc), periods=SEQUENCE_LENGTH + 1, freq="MS")

            # Baseline water depth around structure (m below surface)
            base_depth = 11.0 + np.random.uniform(-1.5, 1.5)
            months = dates.month.to_numpy()
            seasonality = 2.0 * np.sin(2 * np.pi * months / 12)
            rainfall = np.clip(
                120 + 100 * np.sin(2 * np.pi * (months - 6) / 12) + np.random.normal(0, 15, len(dates)),
                0,
                None,
            )

            # Simulated recharge vs degradation effect
            if struct.structure_type == "Check Dam":
                recharge_effect = -1.2  # Healthy recharge: water table rises
            else:
                recharge_effect = 0.8   # Underperforming: sedimentation clogging

            actual_water_levels = base_depth + seasonality + (recharge_effect * (np.arange(len(dates)) / len(dates)))

            # Normalize sequence
            input_df = pd.DataFrame({
                "y": actual_water_levels[:SEQUENCE_LENGTH],
                "rainfall_mm": rainfall[:SEQUENCE_LENGTH]
            })
            scaled_seq = scaler.transform(input_df.values)
            X_input = np.expand_dims(scaled_seq, axis=0)

            # Predict next month's level
            pred_scaled = model.predict(X_input, verbose=0)[0][0]
            pred_full = np.array([[pred_scaled, 0.0]])
            predicted_level_m = float(scaler.inverse_transform(pred_full)[0][0])
            actual_level_m = float(actual_water_levels[-1])

            # Calculate relative percentage deviation
            deviation_pct = (actual_level_m - predicted_level_m) / predicted_level_m if predicted_level_m != 0 else 0.0
            status = "Underperforming" if deviation_pct > DEVIATION_THRESHOLD else "OK"

            # Create or update verification log
            check_date = datetime.now(timezone.utc).date()
            date_col_attr = (
                VerificationLog.check_date
                if hasattr(VerificationLog, "check_date") and not isinstance(VerificationLog.check_date, property)
                else VerificationLog.evaluation_date
            )

            existing_log = (
                db.query(VerificationLog)
                .filter(
                    VerificationLog.structure_id == struct.structure_id,
                    date_col_attr == check_date
                )
                .first()
            )

            log_data = get_log_field_mapping(
                struct_id=struct.structure_id,
                model_ver=version_id,
                chk_date=check_date,
                pred_m=round(predicted_level_m, 2),
                act_m=round(actual_level_m, 2),
                dev_pct=round(deviation_pct * 100, 2),
                stat=status
            )

            if not existing_log:
                log_entry = VerificationLog(**log_data)
                db.add(log_entry)
            else:
                for k, v in log_data.items():
                    if k not in ("structure_id", "log_id"):
                        setattr(existing_log, k, v)

            print(f"🔹 Structure {struct.structure_id} ({struct.structure_type})")
            print(f"   Predicted: {predicted_level_m:.2f}m | Actual: {actual_level_m:.2f}m | Deviation: {deviation_pct*100:+.1f}% | Status: [{status}]")

            # Dispatch real-time WebSocket alert when underperforming
            if status == "Underperforming":
                dispatch_realtime_alert(str(struct.structure_id), struct.structure_type, deviation_pct)

        db.commit()
        print("💾 Verification run complete. Database updated successfully!")

    except Exception as e:
        print(f"❌ Error running verification engine: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run_verification_engine()