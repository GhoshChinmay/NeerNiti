import glob
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.db.models import ModelVersion
from app.db.session import SessionLocal


def register_latest_colab_model():
    # Find the most recently downloaded metadata JSON file
    artifact_dir = os.path.dirname(__file__)
    metadata_files = glob.glob(os.path.join(artifact_dir, "*_metadata.json"))
    
    if not metadata_files:
        print("❌ No Colab metadata JSON found. Make sure you moved it to backend/app/ml/")
        return
        
    latest_metadata_path = max(metadata_files, key=os.path.getctime)
    
    with open(latest_metadata_path, 'r') as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        # Support both PanIndia and Verification metadata schemas
        version_id = data.get("model_version_id") or data.get("version_id")
        module_name = data.get("module_name", "site_recommendation")
        
        # Check if it already exists
        existing = db.query(ModelVersion).filter_by(model_version_id=version_id).first()
        if existing:
            print(f"Model {version_id} is already registered in your database.")
            return

        # Register the new Colab model
        new_version = ModelVersion(
            model_version_id=version_id,
            module_name=module_name,
            algorithm=data["algorithm"],
            trained_on=data.get("trained_on", data.get("created_at")),
            hyperparameters=data["hyperparameters"],
            evaluation_metrics=data.get("evaluation_metrics", data.get("evaluation")),
            training_data_snapshot=data.get("training_data_snapshot", data.get("training_data", {}).get("total_samples", "live_gee"))
        )
        db.add(new_version)
        db.commit()
        print(f"Successfully registered Colab Model {version_id} into PostgreSQL!")
        
    except Exception as e:
        print(f"Error registering model: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    register_latest_colab_model()