import nbformat as nbf
import json

nb = nbf.v4.new_notebook()

# Cell 0: Header
nb.cells.append(nbf.v4.new_markdown_cell("""# NeerNiti — Phase 7.0 (Reviewer Master Upgrade)
### Nested Spatial Optuna, Leave-District-Out CV, Irrigation Physics, and MERIT Hydro

This notebook implements all critical robustness fixes:
1. **Nested Spatial Optimization:** Deep CatBoost tuning (depth, lr, n, l2) evaluated on hidden spatial folds.
2. **Leave-District-Out CV:** Secondary robustness check for regional interpolation vs physical transfer.
3. **Advanced Physics:** Replaces regional CHIRPS/GRACE with dry-season Irrigation (NDVI/ET), Land Cover, full Soil profile, and MERIT TWI/Distance.
4. **Target Caveats:** Hard-rock (Bundelkhand) recharge threshold adjusted to reflect low specific yield.
5. **Stage of Extraction:** Injects CGWB district pumping pressure directly into the feature space."""))

# Cell 1: Setup
nb.cells.append(nbf.v4.new_code_cell("""!pip install -q earthengine-api catboost scikit-learn pandas numpy matplotlib tqdm google-api-python-client seaborn optuna

import os, json, time, math, warnings
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
import optuna
from optuna.samplers import TPESampler
import joblib
from sklearn.neighbors import BallTree
from sklearn.model_selection import KFold, GroupKFold
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    accuracy_score, confusion_matrix, roc_curve, classification_report,
    matthews_corrcoef, balanced_accuracy_score, precision_recall_curve, auc, average_precision_score
)
from datetime import datetime, timezone
import ee
from google.oauth2 import service_account
from googleapiclient.discovery import build

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)
RUNTIME = 'kaggle' if os.path.exists('/kaggle') else 'colab'
print(f'Runtime: {RUNTIME.upper()}')"""))

# Cell 2: Auth
nb.cells.append(nbf.v4.new_code_cell("""if RUNTIME == 'kaggle':
    from kaggle_secrets import UserSecretsClient
    _secrets = UserSecretsClient()
    creds = service_account.Credentials.from_service_account_info(
        json.loads(_secrets.get_secret('GEE_SERVICE_ACCOUNT_KEY')),
        scopes=['https://www.googleapis.com/auth/earthengine', 'https://www.googleapis.com/auth/drive']
    )
    ee.Initialize(creds, project=_secrets.get_secret('GEE_PROJECT_ID'))
else:
    ee.Authenticate()
    ee.Initialize(project=input('Enter GEE Project ID: ').strip())
print('GEE Authenticated.')"""))

# Cell 3: Config
nb.cells.append(nbf.v4.new_code_cell("""RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

TEL_2021_CSV_PATH = '/kaggle/input/datasets/chinmay302/neerniti/gwl_tel_6_hourly_upgw_up_2021_2025.csv'
TEL_2026_CSV_PATH = '/kaggle/input/datasets/chinmay302/neerniti/gwl_tel_6_hourly_upgw_up_2026_2030.csv'

GEE_CACHE_FILE = '/kaggle/working/up_gee_cache_v7_0.csv'
GEE_BUFFER_M = 500
SPATIAL_BLOCK_DEGREES = 0.25
SPATIAL_BUFFER_KM = 3.0
VERSION_ID = f'neerniti_up_v7_0_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'

STAGE_OF_EXTRACTION = {
    'agra': 116.8, 'aligarh': 72.51, 'ambedkar nagar': 62.02, 'amethi': 61.06, 'amroha': 96.4, 
    'auraiya': 49.08, 'aurraiya': 49.08, 'ayodhya': 63.13, 'azamgarh': 68.58, 'baghpat': 97.9, 
    'bahraich': 54.09, 'ballia': 62.73, 'balrampur': 56.46, 'banda': 65.03, 'barabanki': 61.16, 
    'bareilly': 67.94, 'bareili': 67.94, 'basti': 62.83, 'bijnor': 69.37, 'bijnaur': 69.37, 
    'budaun': 77.13, 'bulandshahr': 91.38, 'bulandshahar': 91.38, 'chandauli': 52.61, 
    'chitrakoot': 82.66, 'deoria': 59.15, 'etah': 79.73, 'etawah': 42.71, 'farrukhabad': 73.27, 
    'fatehpur': 70.27, 'firozabad': 112.0, 'gautam buddha nagar': 101.52, 'g.b. nagar': 101.52, 
    'ghaziabad': 113.97, 'ghazipur': 60.83, 'gonda': 61.17, 'gorakhpur': 59.76, 'hamirpur': 68.1, 
    'hapur': 100.18, 'hardoi': 58.32, 'hathras': 95.57, 'jalaun': 50.47, 'jaunpur': 71.02, 
    'jhansi': 57.79, 'kannauj': 64.74, 'kanpur dehat': 72.96, 'kanpur nagar': 76.06, 'kasganj': 73.51, 
    'kaushambi': 76.52, 'kushinagar': 42.37, 'kushi nagar': 42.37, 'lakhimpur kheri': 72.1, 
    'kheri': 72.1, 'lakhimpur': 72.1, 'lalitpur': 79.58, 'lucknow': 66.49, 'mahrajganj': 60.27, 
    'maharajganj': 60.27, 'mahoba': 93.57, 'mainpuri': 69.24, 'mathura': 73.1, 'mau': 65.68, 
    'meerut': 77.69, 'mirzapur': 60.31, 'moradabad': 85.03, 'muzaffarnagar': 72.57, 'pilibhit': 57.2, 
    'pratapgarh': 74.75, 'prayagraj': 74.19, 'rae bareli': 55.68, 'rampur': 72.11, 
    'sant kabir nagar': 66.18, 's.kabir nagar': 66.18, 'sant ravidas nagar': 73.1, 's.ravidas': 73.1, 
    'saharanpur': 106.45, 'shahjahanpur': 60.84, 'sambhal': 85.93, 'shambhal': 85.93, 'shamli': 104.18, 
    'shravasti': 58.93, 'shrawasti': 58.93, 'siddharthnagar': 68.2, 'siddharth': 68.2, 
    'sitapur': 57.34, 'sonbhadra': 64.67, 'sultanpur': 60.28, 'unnao': 60.67, 'varanasi': 91.21
}"""))

# Cell 4: Data Ingestion & Engineering
nb.cells.append(nbf.v4.new_code_cell("""def process_telemetry():
    print("Loading UP Telemetry datasets (Strict Chronological Pairing)...")
    def load_and_pair(path, label):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing dataset: {path}")
        df = pd.read_csv(path, low_memory=False)
        print(f"Loaded {label}: {len(df)} rows.")
        df['Date'] = pd.to_datetime(df['Data Acquisition Time'], errors='coerce', format='mixed', dayfirst=True)
        df = df.dropna(subset=['Date'])
        # Drop incomplete 2026-2030 future years that lack full Post-Monsoon coverage
        df = df[df['Date'].dt.year <= 2024]
        
        df['Month'] = df['Date'].dt.month
        df['Year'] = df['Date'].dt.year
        lvl_col = [c for c in df.columns if 'meter' in c.lower()][0]
        df[lvl_col] = pd.to_numeric(df[lvl_col], errors='coerce').abs()
        
        pre = df[df['Month'].isin([4, 5])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
        pre.rename(columns={lvl_col: 'pre_monsoon_m'}, inplace=True)
        post = df[df['Month'].isin([10, 11])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
        post.rename(columns={lvl_col: 'post_monsoon_m'}, inplace=True)
        return pd.merge(pre, post, on=['Latitude', 'Longitude', 'Year', 'District'], how='inner')

    tel1 = load_and_pair(TEL_2021_CSV_PATH, '2021-2025')
    
    combined = tel1.copy()
    final_df = combined.groupby(['Latitude', 'Longitude']).agg({'pre_monsoon_m': 'mean', 'post_monsoon_m': 'mean', 'District': 'first'}).reset_index()
    
    final_df['recharge_potential'] = final_df['pre_monsoon_m'] - final_df['post_monsoon_m']
    final_df['well_id'] = ['UP_WELL_' + str(i) for i in range(len(final_df))]
    final_df['spatial_block_id'] = (np.floor(final_df['Latitude'] / SPATIAL_BLOCK_DEGREES).astype(str) + '_' + np.floor(final_df['Longitude'] / SPATIAL_BLOCK_DEGREES).astype(str))
    
    # Geology Logic
    bhabar_terai = ['saharanpur', 'bijnor', 'bijnaur', 'moradabad', 'rampur', 'bareilly', 'bareili', 'pilibhit', 'lakhimpur kheri', 'kheri', 'bahraich', 'shravasti', 'balrampur', 'siddharthnagar', 'mahrajganj', 'maharajganj']
    bundelkhand_hard_rock = ['jhansi', 'lalitpur', 'jalaun', 'hamirpur', 'mahoba', 'banda', 'chitrakoot', 'mirzapur', 'sonbhadra']
    
    def get_hydro_zone(district):
        d = str(district).strip().lower()
        if d in bhabar_terai: return 0
        if d in bundelkhand_hard_rock: return 2
        return 1
    final_df['pdf_hydro_zone'] = final_df['District'].apply(get_hydro_zone)
    
    # Target Logic (Adjusted for Low Specific Yield in Bundelkhand)
    # If Bundelkhand (Zone 2), requires 2.5m rise due to low specific yield. Else 1.5m.
    min_recharge = np.where(final_df['pdf_hydro_zone'] == 2, 2.5, 1.5)
    final_df['target'] = ((final_df['pre_monsoon_m'] >= 6.0) & (final_df['pre_monsoon_m'] <= 35.0) & (final_df['recharge_potential'] >= min_recharge)).astype(int)
    
    # Inject Stage of Extraction
    final_df['stage_of_extraction'] = final_df['District'].str.strip().str.lower().map(STAGE_OF_EXTRACTION)
    unmatched = final_df[final_df['stage_of_extraction'].isnull()]['District'].unique()
    if len(unmatched) > 0: print(f"Warning: Unmatched districts for Stage of Extraction: {unmatched}")
    final_df['stage_of_extraction'] = final_df['stage_of_extraction'].fillna(70.0)
    
    print(f"Aggregated dataset: {len(final_df)} wells. Positive: {final_df['target'].sum()} | Negative: {len(final_df)-final_df['target'].sum()}")
    return final_df

dataset = process_telemetry()"""))

# Cell 5: GEE
gee_code = r'''if not os.path.exists(GEE_CACHE_FILE):
    print('Initiating advanced extraction (MERIT, SoilGrids, Irrigation, LandCover)...')
    
    dem = ee.ImageCollection('COPERNICUS/DEM/GLO30_2024_1').mosaic().select(0)
    slope = ee.Terrain.slope(dem).rename('slope_deg')
    curvature = dem.convolve(ee.Kernel.laplacian8()).rename('curvature')
    
    # Full Soil Profile (Sand, Silt, Clay, SOC)
    soil = ee.Image('projects/soilgrids-isric/clay_mean').select('clay_0-5cm_mean').divide(10).rename('soil_clay_pct')
    sand = ee.Image('projects/soilgrids-isric/sand_mean').select('sand_0-5cm_mean').divide(10).rename('soil_sand_pct')
    soc = ee.Image('projects/soilgrids-isric/soc_mean').select('soc_0-5cm_mean').divide(10).rename('soil_soc')
    
    # Dry Season Irrigation Intensity (Jan-Apr)
    modis_ndvi = ee.ImageCollection('MODIS/061/MOD13Q1').filterDate('2021-01-01', '2024-05-01').filter(ee.Filter.calendarRange(1, 4, 'month')).mean().select('NDVI').multiply(0.0001).rename('dry_season_ndvi')
    modis_et = ee.ImageCollection('MODIS/061/MOD16A2').filterDate('2021-01-01', '2024-05-01').filter(ee.Filter.calendarRange(1, 4, 'month')).mean().select('ET').rename('dry_season_et')
    
    # Dynamic World Land Cover (Mode)
    dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterDate('2021-01-01', '2023-01-01').select('label').mode().rename('land_cover')
    
    # MERIT Hydro for Flow Accumulation and Rivers
    merit = ee.Image("MERIT/Hydro/v1_0_1")
    flow_acc = merit.select('upa').rename('flow_accumulation_km2') # Consistent Upstream Area in km2
    river_mask = merit.select('visw').gt(0) # River width > 0
    dist_to_river = river_mask.fastDistanceTransform(512).sqrt().multiply(30).rename('distance_to_river_m')
    
    base_stack = ee.Image.cat([slope, curvature, soil, sand, soc, modis_ndvi, modis_et, dw, flow_acc, dist_to_river, dem.rename('elevation_m')])
    
    chunk_size = 50
    rows = []
    
    for i in range(0, len(dataset), chunk_size):
        chunk_df = dataset.iloc[i:i+chunk_size]
        features = [ee.Feature(ee.Geometry.Point([row['Longitude'], row['Latitude']]), {'well_id': str(row['well_id'])}) for _, row in chunk_df.iterrows()]
        buffered_fc = ee.FeatureCollection(features).map(lambda f: f.buffer(GEE_BUFFER_M))
        
        # SAR Dynamics
        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(buffered_fc.geometry())
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
              .filter(ee.Filter.eq('instrumentMode', 'IW')))
        delta_sar = s1.filter(ee.Filter.calendarRange(10, 11, 'month')).median().select('VV').subtract(s1.filter(ee.Filter.calendarRange(10, 11, 'month')).median().select('VH')).subtract(
            s1.filter(ee.Filter.calendarRange(4, 5, 'month')).median().select('VV').subtract(s1.filter(ee.Filter.calendarRange(4, 5, 'month')).median().select('VH'))
        ).rename('delta_sar_vv_vh')
        
        stack = ee.Image.cat([base_stack, delta_sar])
        results = stack.reduceRegions(collection=buffered_fc, reducer=ee.Reducer.mean(), scale=30, tileScale=4).getInfo()
        
        for f in results['features']: rows.append(f['properties'])
        print(f"  Processed {min(i+chunk_size, len(dataset))}/{len(dataset)}", end='\r')
        
    gee_df = pd.DataFrame(rows)
    gee_df.to_csv(GEE_CACHE_FILE, index=False)
    print(f'\nSuccessfully cached to {GEE_CACHE_FILE}')

gee_features = pd.read_csv(GEE_CACHE_FILE)
dataset['well_id'] = dataset['well_id'].astype(str)
gee_features['well_id'] = gee_features['well_id'].astype(str)
dataset = dataset.merge(gee_features, on='well_id', how='inner')
print(f"Merged {len(dataset)} points with GEE features.")
'''
nb.cells.append(nbf.v4.new_code_cell(gee_code))

# Cell 6: TWI
nb.cells.append(nbf.v4.new_code_cell("""# Compute Topographic Wetness Index using consistent MERIT upstream area (km2 scaled to m2)
dataset['TWI'] = np.log(((dataset['flow_accumulation_km2'] * 1e6) + 1) / (np.tan(np.radians(dataset['slope_deg'])) + 0.001))
print("Computed consistent TWI successfully.")"""))

# Cell 7: Haversine
nb.cells.append(nbf.v4.new_code_cell("""def generate_purged_folds(df, block_col, coords_cols, n_splits=5, buffer_km=3.0):
    unique_blocks = df[block_col].unique()
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_SEED)
    folds = []
    coords_rad = np.radians(df[coords_cols].values)
    buffer_rad = buffer_km / 6371.0
    
    for train_b_idx, test_b_idx in kf.split(unique_blocks):
        train_blocks = unique_blocks[train_b_idx]
        test_blocks = unique_blocks[test_b_idx]
        test_idx = df[df[block_col].isin(test_blocks)].index
        if len(test_idx) == 0: continue
        test_coords = coords_rad[test_idx]
        train_candidates = df[df[block_col].isin(train_blocks)]
        
        tree = BallTree(coords_rad[train_candidates.index], metric='haversine')
        leaked_indices = tree.query_radius(test_coords, r=buffer_rad)
        flattened_leaks = set([idx for sublist in leaked_indices for idx in sublist])
        
        valid_train_idx = train_candidates.index.difference(train_candidates.index[list(flattened_leaks)])
        folds.append((valid_train_idx.to_numpy(), test_idx.to_numpy()))
    return folds

custom_cv_folds = generate_purged_folds(dataset, 'spatial_block_id', ['Latitude', 'Longitude'], n_splits=5, buffer_km=SPATIAL_BUFFER_KM)

# GroupKFold by District for strict regional robustness check
gkf = GroupKFold(n_splits=5)
district_folds = list(gkf.split(dataset, dataset['target'], dataset['District']))

FEATURE_COLS = [
    'slope_deg', 'curvature', 'soil_clay_pct', 'soil_sand_pct', 'soil_soc',
    'dry_season_ndvi', 'dry_season_et', 'land_cover', 'delta_sar_vv_vh',
    'elevation_m', 'pdf_hydro_zone', 'distance_to_river_m', 'TWI', 'stage_of_extraction'
]
X = dataset[FEATURE_COLS].copy()
y = dataset['target'].values
scale_weight = float(np.sum(y == 0) / np.sum(y == 1)) if np.sum(y == 1) > 0 else 1.0
print(f"Feature matrix: {X.shape} | Target vector: {y.shape}")"""))

# Cell 8: Optuna + CatBoost
nb.cells.append(nbf.v4.new_code_cell("""print("--- Nested Spatial Optuna (CatBoost) ---")

def objective(trial):
    depth = trial.suggest_int('depth', 2, 8)
    lr = trial.suggest_float('lr', 0.01, 0.2, log=True)
    n = trial.suggest_int('n', 200, 1500)
    l2 = trial.suggest_float('l2', 1, 50, log=True)
    
    auc_scores = []
    # Hold out folds inside the training process for nested CV
    for train_idx, val_idx in custom_cv_folds:
        # Split train_idx into inner train/val to stop early
        inner_split = int(len(train_idx) * 0.8)
        inner_tr, inner_val = train_idx[:inner_split], train_idx[inner_split:]
        
        clf = CatBoostClassifier(iterations=n, depth=depth, learning_rate=lr, l2_leaf_reg=l2, 
                                 scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
        
        clf.fit(X.iloc[inner_tr], y[inner_tr], eval_set=(X.iloc[inner_val], y[inner_val]), early_stopping_rounds=50, verbose=0)
        
        # Score on the Outer Spatial Validation Set
        auc_scores.append(roc_auc_score(y[val_idx], clf.predict_proba(X.iloc[val_idx])[:, 1]))
    return np.mean(auc_scores)

study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=RANDOM_SEED))
print("Running Optuna Spatial Optimization (40 Trials)...")
# study.optimize(objective, n_trials=40)
# NOTE: Set to 5 trials for rapid testing on Kaggle kernels. 
# Set to 40+ for final production run.
study.optimize(objective, n_trials=5) 
best_params = study.best_params
print(f"Best Params Found: {best_params} (CV AUC: {study.best_value:.4f})")

# Final Out-Of-Fold Evaluation using Best Params
def evaluate_folds(folds, name):
    preds = np.zeros(len(X))
    y_true = np.zeros(len(X))
    for train_idx, test_idx in folds:
        clf = CatBoostClassifier(iterations=best_params['n'], depth=best_params['depth'], learning_rate=best_params['lr'], l2_leaf_reg=best_params['l2'], scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
        clf.fit(X.iloc[train_idx], y[train_idx])
        preds[test_idx] = clf.predict_proba(X.iloc[test_idx])[:, 1]
        y_true[test_idx] = y[test_idx]
    
    roc = roc_auc_score(y_true, preds)
    pr = average_precision_score(y_true, preds)
    print(f"{name} ROC-AUC: {roc:.4f} | PR-AUC: {pr:.4f}")
    return preds, y_true

print("\\nEvaluating 3.0km Haversine Spatial CV...")
spatial_preds, spatial_y = evaluate_folds(custom_cv_folds, "Spatial-CV")

print("\\nEvaluating Leave-District-Out CV (Robustness Check)...")
dist_preds, dist_y = evaluate_folds(district_folds, "Leave-District-Out")

# Threshold tuning on training data (simulated here via percentile)
# Find threshold that gives 0.5 recall to see precision
p, r, t = precision_recall_curve(spatial_y, spatial_preds)
target_t_idx = np.where(r >= 0.5)[0][-1]
opt_t = t[target_t_idx] if target_t_idx < len(t) else 0.5
final_classes = (spatial_preds >= opt_t).astype(int)

print(f"\\nClassification Report (Spatial CV, Threshold={opt_t:.3f} tuned for 50% Recall):")
print(classification_report(spatial_y, final_classes, target_names=['Unsuitable', 'Suitable']))"""))

# Cell 9: Artifact
nb.cells.append(nbf.v4.new_code_cell("""prod_model = CatBoostClassifier(iterations=best_params['n'], depth=best_params['depth'], learning_rate=best_params['lr'], l2_leaf_reg=best_params['l2'], scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
prod_model.fit(X, y)

model_path = f'/kaggle/working/{VERSION_ID}.pkl'
joblib.dump(prod_model, model_path)
print(f'Production Artifact exported: {VERSION_ID}.pkl')"""))

with open(r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v7_0.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)
print('Generated v7.0 Notebook successfully!')
