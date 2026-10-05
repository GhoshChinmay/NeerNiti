import nbformat

nb = nbformat.v4.new_notebook()

cells = []

# Cell 1
cells.append(nbformat.v4.new_markdown_cell(source="""# NeerNiti — Phase 8.0 (Well-Year Panel & LODO Tuning)
### Longitudinal Physics, Honest Evaluation, and Within-District Metrics

This notebook implements the major architectural shifts requested in the review:
1. **Well-Year Panel Data:** Stops averaging away physical drivers. Builds a dataset of well-years, preserving pre-monsoon depth and adding yearly CHIRPS monsoon rainfall + anomaly.
2. **Honest LODO Tuning:** Optuna now explicitly tunes on Leave-District-Out folds (capped at depth 3-5) to stop exploiting district constants.
3. **Data Quality & Label Noise:** Drops wells with < 3 paired years. Flags and excludes marginal labels (±0.3m of threshold) during training.
4. **Within-District AUC:** Evaluates the model's ability to rank sites *inside* a district, not just between them."""))

# Cell 2
cells.append(nbformat.v4.new_code_cell(source="""!pip install -q earthengine-api catboost scikit-learn pandas numpy matplotlib tqdm google-api-python-client seaborn optuna

import os, json, time, math, warnings
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
import optuna
from optuna.samplers import TPESampler
import joblib
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
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

# Cell 3
cells.append(nbformat.v4.new_code_cell(source="""if RUNTIME == 'kaggle':
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

# Cell 4
cells.append(nbformat.v4.new_code_cell(source="""RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

TEL_2021_CSV_PATH = '/kaggle/input/datasets/chinmay302/neerniti/gwl_tel_6_hourly_upgw_up_2021_2025.csv'

GEE_CACHE_FILE = '/kaggle/working/up_gee_cache_v8_0.csv'
GEE_BUFFER_M = 500
VERSION_ID = f'neerniti_up_v8_0_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'

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
    'sitapur': 57.34, 'sonbhadra': 64.67, 'sultanpur': 60.28, 'unnao': 60.67, 'varanasi': 91.21,
    'praygraj': 74.19, 'allahabad': 74.19, 'bhadohi': 73.1, 'raibareli': 55.68, 
    'amethi (c.s.m. nagar)': 61.06, 'kansiram nagar': 73.51, 'shahjhanpur': 60.84, 
    'buland shahar': 91.38, 'amroha (j.p.nagar)': 96.4, 'jyotiba phule nagar': 96.4
}"""))

# Cell 5
cells.append(nbformat.v4.new_code_cell(source="""def process_telemetry():
    print("Loading UP Telemetry datasets (Building Well-Year Panel)...")
    if not os.path.exists(TEL_2021_CSV_PATH):
        raise FileNotFoundError(f"Missing dataset: {TEL_2021_CSV_PATH}")
    
    df = pd.read_csv(TEL_2021_CSV_PATH, low_memory=False)
    df['Date'] = pd.to_datetime(df['Data Acquisition Time'], errors='coerce', format='mixed', dayfirst=True)
    df = df.dropna(subset=['Date'])
    df = df[df['Date'].dt.year <= 2025]
    
    df['Month'] = df['Date'].dt.month
    df['Year'] = df['Date'].dt.year
    lvl_col = [c for c in df.columns if 'meter' in c.lower()][0]
    df[lvl_col] = pd.to_numeric(df[lvl_col], errors='coerce').abs()
    
    # Pre-monsoon (Apr-May) and Post-monsoon (Oct-Nov) averages per year
    pre = df[df['Month'].isin([4, 5])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
    pre.rename(columns={lvl_col: 'pre_monsoon_m'}, inplace=True)
    post = df[df['Month'].isin([10, 11])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
    post.rename(columns={lvl_col: 'post_monsoon_m'}, inplace=True)
    
    panel_df = pd.merge(pre, post, on=['Latitude', 'Longitude', 'Year', 'District'], how='inner')
    
    # Normalize District
    def normalize_district(d):
        d = str(d).strip().lower()
        aliases = {
            'bareili': 'bareilly', 'bijnaur': 'bijnor', 'praygraj': 'prayagraj', 'allahabad': 'prayagraj',
            'buland shahar': 'bulandshahr', 'bulandshahar': 'bulandshahr', 'shrawasti': 'shravasti',
            'shambhal': 'sambhal', 'siddharth': 'siddharthnagar', 'maharajganj': 'mahrajganj',
            'kushi nagar': 'kushinagar', 'raibareli': 'rae bareli', 'kheri': 'lakhimpur kheri',
            'lakhimpur': 'lakhimpur kheri', 'aurraiya': 'auraiya', 's.kabir nagar': 'sant kabir nagar',
            's.ravidas': 'bhadohi', 'sant ravidas nagar': 'bhadohi', 'g.b. nagar': 'gautam buddha nagar',
            'amethi (c.s.m. nagar)': 'amethi', 'amroha (j.p.nagar)': 'amroha', 'jyotiba phule nagar': 'amroha',
            'kansiram nagar': 'kasganj', 'shahjhanpur': 'shahjahanpur'
        }
        return aliases.get(d, d)

    panel_df['District'] = panel_df['District'].apply(normalize_district)
    
    # Assign unique Well IDs
    locations = panel_df[['Latitude', 'Longitude']].drop_duplicates().reset_index(drop=True)
    locations['well_id'] = ['UP_WELL_' + str(i) for i in range(len(locations))]
    panel_df = panel_df.merge(locations, on=['Latitude', 'Longitude'], how='left')
    
    # Drop wells with < 3 paired years
    year_counts = panel_df.groupby('well_id').size()
    valid_wells = year_counts[year_counts >= 3].index
    panel_df = panel_df[panel_df['well_id'].isin(valid_wells)].copy()
    print(f"Retained {len(valid_wells)} wells with >= 3 years of data (Total rows: {len(panel_df)}).")
    
    panel_df['recharge_potential'] = panel_df['pre_monsoon_m'] - panel_df['post_monsoon_m']
    
    # Geology
    bhabar_terai = ['saharanpur', 'bijnor', 'moradabad', 'rampur', 'bareilly', 'pilibhit', 'lakhimpur kheri', 'bahraich', 'shravasti', 'balrampur', 'siddharthnagar', 'mahrajganj']
    bundelkhand_hard_rock = ['jhansi', 'lalitpur', 'jalaun', 'hamirpur', 'mahoba', 'banda', 'chitrakoot', 'mirzapur', 'sonbhadra']
    
    def get_hydro_zone(district):
        if district in bhabar_terai: return 0
        if district in bundelkhand_hard_rock: return 2
        return 1
    panel_df['pdf_hydro_zone'] = panel_df['District'].apply(get_hydro_zone)
    
    # Target (1.5m general, 2.5m for Hard Rock)
    min_recharge = np.where(panel_df['pdf_hydro_zone'] == 2, 2.5, 1.5)
    panel_df['target'] = ((panel_df['pre_monsoon_m'] >= 6.0) & (panel_df['pre_monsoon_m'] <= 35.0) & (panel_df['recharge_potential'] >= min_recharge)).astype(int)
    
    # Flag Marginal Wells (within 0.3m of threshold) to optionally drop from training
    panel_df['is_marginal'] = (np.abs(panel_df['recharge_potential'] - min_recharge) <= 0.3)
    print(f"Flagged {panel_df['is_marginal'].sum()} marginal well-years (within 0.3m of threshold).")
    
    panel_df['stage_of_extraction'] = panel_df['District'].map(STAGE_OF_EXTRACTION)
    
    print(f"Panel dataset ready: {len(panel_df)} well-years. Positive: {panel_df['target'].sum()} | Negative: {len(panel_df)-panel_df['target'].sum()}")
    return panel_df, locations

panel_df, unique_locations = process_telemetry()"""))

# Cell 6
cells.append(nbformat.v4.new_code_cell(source="""if not os.path.exists(GEE_CACHE_FILE):
    print('Initiating advanced extraction (Static + Yearly CHIRPS)...')
    
    dem = ee.ImageCollection('COPERNICUS/DEM/GLO30_2024_1').mosaic().select(0)
    slope = ee.Terrain.slope(dem).rename('slope_deg')
    curvature = dem.convolve(ee.Kernel.laplacian8()).rename('curvature')
    
    def soil_30_100(asset, prefix, divisor, name):
        img = ee.Image(asset)
        mid = (img.select(f'{prefix}_30-60cm_mean').multiply(30)
               .add(img.select(f'{prefix}_60-100cm_mean').multiply(40))
               .divide(70))
        return mid.divide(divisor).rename(name)

    clay_0 = ee.Image('projects/soilgrids-isric/clay_mean').select('clay_0-5cm_mean').divide(10).rename('soil_clay_0_5_pct')
    clay_30 = soil_30_100('projects/soilgrids-isric/clay_mean', 'clay', 10, 'soil_clay_30_100_pct')
    sand_0 = ee.Image('projects/soilgrids-isric/sand_mean').select('sand_0-5cm_mean').divide(10).rename('soil_sand_0_5_pct')
    sand_30 = soil_30_100('projects/soilgrids-isric/sand_mean', 'sand', 10, 'soil_sand_30_100_pct')
    soc_0 = ee.Image('projects/soilgrids-isric/soc_mean').select('soc_0-5cm_mean').divide(10).rename('soil_soc_0_5')
    soc_30 = soil_30_100('projects/soilgrids-isric/soc_mean', 'soc', 10, 'soil_soc_30_100')
    
    # We will exclude dry_season_et if requested, but let's extract it first and check NaNs
    modis_ndvi = ee.ImageCollection('MODIS/061/MOD13Q1').filterDate('2021-01-01', '2026-01-01').filter(ee.Filter.calendarRange(1, 4, 'month')).mean().select('NDVI').multiply(0.0001).rename('dry_season_ndvi')
    modis_et = ee.ImageCollection('MODIS/061/MOD16A2').filterDate('2021-01-01', '2026-01-01').filter(ee.Filter.calendarRange(1, 4, 'month')).mean().select('ET').multiply(0.1).rename('dry_season_et')
    
    dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterDate('2021-01-01', '2024-01-01').select('label').mode()
    crop_frac = dw.eq(4).rename('crop_frac')
    built_frac = dw.eq(6).rename('built_frac')
    tree_frac = dw.eq(1).rename('tree_frac')
    
    merit = ee.Image('MERIT/Hydro/v1_0_1')
    upa = merit.select('upa')
    log_upa = upa.add(0.01).log().rename('log_upstream_area')
    hand = merit.select('hnd').rename('hand_m')
    river_mask = upa.gt(10).unmask(0)
    dist_to_river = (river_mask.fastDistanceTransform(512).sqrt()
                     .multiply(ee.Image.pixelArea().sqrt()).rename('distance_to_river_m'))
    
    # Yearly CHIRPS (Jun-Sep) for 2021 to 2025
    def get_yearly_chirps(year):
        return ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
                 .filterDate(f'{year}-06-01', f'{year}-10-01') \
                 .sum().rename(f'chirps_{year}')
                 
    chirps_bands = [get_yearly_chirps(y) for y in range(2021, 2026)]
    
    base_stack = ee.Image.cat([
        slope, curvature, clay_0, clay_30, sand_0, sand_30, soc_0, soc_30, 
        modis_ndvi, modis_et, crop_frac, built_frac, tree_frac, 
        log_upa, hand, dist_to_river, dem.rename('elevation_m')
    ] + chirps_bands)
    
    chunk_size = 50
    rows = []
    
    for i in range(0, len(unique_locations), chunk_size):
        chunk_df = unique_locations.iloc[i:i+chunk_size]
        features = [ee.Feature(ee.Geometry.Point([row['Longitude'], row['Latitude']]), {'well_id': str(row['well_id'])}) for _, row in chunk_df.iterrows()]
        buffered_fc = ee.FeatureCollection(features).map(lambda f: f.buffer(GEE_BUFFER_M))
        
        # We drop SAR dynamics to keep this simple since SAR needs exact dates which complicates longitudinal
        results = base_stack.reduceRegions(collection=buffered_fc, reducer=ee.Reducer.mean(), scale=30, tileScale=4).getInfo()
        
        for f in results['features']: rows.append(f['properties'])
        print(f"  Processed {min(i+chunk_size, len(unique_locations))}/{len(unique_locations)}", end='\\r')
        
    gee_df = pd.DataFrame(rows)
    gee_df.to_csv(GEE_CACHE_FILE, index=False)
    print(f'\\nSuccessfully cached to {GEE_CACHE_FILE}')

gee_features = pd.read_csv(GEE_CACHE_FILE)
gee_features['well_id'] = gee_features['well_id'].astype(str)
panel_df['well_id'] = panel_df['well_id'].astype(str)

# Combine static features
static_cols = [c for c in gee_features.columns if not c.startswith('chirps_') and c != 'well_id']
panel_df = panel_df.merge(gee_features[['well_id'] + static_cols], on='well_id', how='left')

# Assign proper yearly CHIRPS to each row
def assign_chirps(row):
    year = row['Year']
    col_name = f'chirps_{year}'
    # Look up from gee_features
    well_gee = gee_features[gee_features['well_id'] == row['well_id']]
    if len(well_gee) > 0 and col_name in well_gee.columns:
        return well_gee.iloc[0][col_name]
    return np.nan

panel_df['monsoon_rainfall_mm'] = panel_df.apply(assign_chirps, axis=1)

# Compute well's mean CHIRPS to create anomaly
well_mean_chirps = panel_df.groupby('well_id')['monsoon_rainfall_mm'].mean().reset_index().rename(columns={'monsoon_rainfall_mm': 'well_mean_rainfall_mm'})
panel_df = panel_df.merge(well_mean_chirps, on='well_id', how='left')
panel_df['rainfall_anomaly_mm'] = panel_df['monsoon_rainfall_mm'] - panel_df['well_mean_rainfall_mm']

# TWI
panel_df['TWI'] = panel_df['log_upstream_area'] + np.log(1e6) - np.log(np.tan(np.radians(panel_df['slope_deg'])) + 0.001)
print(f"Merged {len(panel_df)} panel rows with GEE features.")"""))

# Cell 7
cells.append(nbformat.v4.new_code_cell(source="""# Check missingness of ET
et_na_rate = panel_df['dry_season_et'].isna().mean()
print(f"Missingness rate for dry_season_et: {et_na_rate:.2%}")
if et_na_rate > 0.05:
    print("Dropping dry_season_et as it largely encodes urban areas which built_frac handles.")
    if 'dry_season_et' in panel_df.columns: panel_df.drop(columns=['dry_season_et'], inplace=True)
else:
    print("Keeping dry_season_et.")"""))

# Cell 8
cells.append(nbformat.v4.new_code_cell(source="""FEATURE_COLS = [
    'pre_monsoon_m', 'monsoon_rainfall_mm', 'rainfall_anomaly_mm', # The physical drivers!
    'slope_deg', 'curvature', 'soil_clay_0_5_pct', 'soil_clay_30_100_pct', 
    'soil_sand_0_5_pct', 'soil_sand_30_100_pct', 'soil_soc_0_5', 'soil_soc_30_100',
    'dry_season_ndvi', 'crop_frac', 'built_frac', 'tree_frac', 
    'elevation_m', 'distance_to_river_m', 'hand_m', 'TWI',
    'pdf_hydro_zone', 'stage_of_extraction'
]
if 'dry_season_et' in panel_df.columns: FEATURE_COLS.append('dry_season_et')

# GroupKFold by District for Leave-District-Out CV
# This implicitly guarantees that all rows of the same well are kept in the same fold!
gkf = GroupKFold(n_splits=5)
district_folds = list(gkf.split(panel_df, panel_df['target'], panel_df['District']))

X = panel_df[FEATURE_COLS].copy()
y = panel_df['target'].values
scale_weight = float(np.sum(y == 0) / np.sum(y == 1)) if np.sum(y == 1) > 0 else 1.0
print(f"Feature matrix: {X.shape} | Target vector: {y.shape}")"""))

# Cell 9
cells.append(nbformat.v4.new_code_cell(source="""print("--- LODO Tuning (CatBoost) ---")
# Tuning strictly on LODO folds to prevent district-level leakage
def objective(trial):
    depth = trial.suggest_int('depth', 3, 5) # Capped at 5 to avoid memorizing district constants
    lr = trial.suggest_float('lr', 0.01, 0.1, log=True)
    n = trial.suggest_int('n', 200, 1000)
    l2 = trial.suggest_float('l2', 1, 50, log=True)
    
    auc_scores = []
    
    for train_idx, val_idx in district_folds:
        train_df = panel_df.iloc[train_idx]
        
        # Inner split for early stopping, also by District to maintain LODO integrity
        inner_gkf = GroupKFold(n_splits=5)
        inner_tr_idx, inner_val_idx = next(inner_gkf.split(train_df, train_df['target'], train_df['District']))
        
        orig_inner_tr = train_idx[inner_tr_idx]
        orig_inner_val = train_idx[inner_val_idx]
        
        # Drop marginal wells purely from training set
        tr_marginal = panel_df.iloc[orig_inner_tr]['is_marginal'].values
        orig_inner_tr = orig_inner_tr[~tr_marginal]
        
        clf = CatBoostClassifier(iterations=n, depth=depth, learning_rate=lr, l2_leaf_reg=l2, 
                                 scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
        
        clf.fit(X.iloc[orig_inner_tr], y[orig_inner_tr], 
                eval_set=(X.iloc[orig_inner_val], y[orig_inner_val]), 
                early_stopping_rounds=50, verbose=0)
        
        trial.set_user_attr(f"best_iteration_fold_{len(auc_scores)}", clf.get_best_iteration())
        auc_scores.append(roc_auc_score(y[val_idx], clf.predict_proba(X.iloc[val_idx])[:, 1]))
        
    return np.mean(auc_scores)

study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=RANDOM_SEED))
print("Running Optuna LODO Optimization...")
study.optimize(objective, n_trials=5) # Can increase for production
best_params = study.best_params
print(f"Best Params Found: {best_params} (CV AUC: {study.best_value:.4f})")

def evaluate_folds(folds, name):
    preds = np.zeros(len(X))
    y_true = np.zeros(len(X))
    fold_aucs = []
    
    for i, (train_idx, test_idx) in enumerate(folds):
        train_df = panel_df.iloc[train_idx]
        
        inner_gkf = GroupKFold(n_splits=5)
        inner_tr_idx, inner_val_idx = next(inner_gkf.split(train_df, train_df['target'], train_df['District']))
        
        orig_inner_tr = train_idx[inner_tr_idx]
        orig_inner_val = train_idx[inner_val_idx]
        
        # Exclude marginal wells from training
        tr_marginal = panel_df.iloc[orig_inner_tr]['is_marginal'].values
        orig_inner_tr = orig_inner_tr[~tr_marginal]
        
        clf = CatBoostClassifier(iterations=best_params['n'], depth=best_params['depth'], 
                                 learning_rate=best_params['lr'], l2_leaf_reg=best_params['l2'], 
                                 scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
        clf.fit(X.iloc[orig_inner_tr], y[orig_inner_tr], 
                eval_set=(X.iloc[orig_inner_val], y[orig_inner_val]), 
                early_stopping_rounds=50, verbose=0)
                
        fold_proba = clf.predict_proba(X.iloc[test_idx])[:, 1]
        preds[test_idx] = fold_proba
        y_true[test_idx] = y[test_idx]
        
        auc_val = roc_auc_score(y[test_idx], fold_proba)
        fold_aucs.append(auc_val)
        print(f"  {name} Fold {i+1} AUC: {auc_val:.4f} (Trees: {clf.get_best_iteration()})")
        
    roc = roc_auc_score(y_true, preds)
    pr = average_precision_score(y_true, preds)
    print(f"\\n>> {name} Overall ROC-AUC: {roc:.4f} | PR-AUC: {pr:.4f}\\n")
    return preds, y_true, clf

print("\\nEvaluating Leave-District-Out CV (HONEST ROBUSTNESS METRIC)...")
dist_preds, dist_y, dist_clf = evaluate_folds(district_folds, "Leave-District-Out")

# Within-District AUC Calculation
dist = panel_df['District'].values
within = [roc_auc_score(dist_y[dist==d], dist_preds[dist==d])
          for d in np.unique(dist) if len(np.unique(dist_y[dist==d]))==2 and (dist==d).sum()>=15]
print(f'Mean Within-District AUC: {np.mean(within):.4f} (Evaluated across {len(within)} districts)')

p, r, t = precision_recall_curve(dist_y, dist_preds)
target_t_idx = np.where(r >= 0.5)[0][-1]
opt_t = t[target_t_idx] if target_t_idx < len(t) else 0.5
final_classes = (dist_preds >= opt_t).astype(int)

print(f"\\nClassification Report (Leave-District-Out CV, Operating Point Threshold={opt_t:.3f} for ~50% Recall):")
print(classification_report(dist_y, final_classes, target_names=['Unsuitable', 'Suitable']))
print(f"Balanced Accuracy: {balanced_accuracy_score(dist_y, final_classes):.4f}")
print(f"MCC: {matthews_corrcoef(dist_y, final_classes):.4f}")"""))

# Cell 10
cells.append(nbformat.v4.new_code_cell(source="""fig, axes = plt.subplots(1, 3, figsize=(20, 5))

# 1. Confusion Matrix
cm = confusion_matrix(dist_y, final_classes)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0])
axes[0].set_title('Confusion Matrix (Leave-District-Out)')

# 2. ROC
fpr, tpr, _ = roc_curve(dist_y, dist_preds)
axes[1].plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC (AUC = {roc_auc_score(dist_y, dist_preds):.4f})')
axes[1].plot([0, 1], [0, 1], color='navy', lw=1, linestyle='--')
axes[1].set_title('ROC Curve (Leave-District-Out)')
axes[1].legend()

# 3. Permutation Importance
result = permutation_importance(dist_clf, X, y, n_repeats=5, random_state=RANDOM_SEED, scoring='roc_auc')
feat_imp = pd.Series(result.importances_mean, index=FEATURE_COLS).sort_values(ascending=True)
feat_imp.plot(kind='barh', ax=axes[2], color='teal')
axes[2].set_title('Permutation Importance')

plt.tight_layout()
plt.savefig('/kaggle/working/up_catboost_results_panel.png', dpi=150)
plt.show()"""))

# Cell 11
cells.append(nbformat.v4.new_code_cell(source="""# Train final model on 100% of data. Exclude marginal wells from training set.
tr_mask = ~panel_df['is_marginal'].values
prod_model = CatBoostClassifier(iterations=best_params['n'], depth=best_params['depth'], 
                                learning_rate=best_params['lr'], l2_leaf_reg=best_params['l2'], 
                                scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
prod_model.fit(X.iloc[tr_mask], y[tr_mask])

model_path = f'/kaggle/working/{VERSION_ID}.pkl'
artifact = {
    'model': prod_model,
    'features': FEATURE_COLS
}
joblib.dump(artifact, model_path)
print(f'Production Artifact exported: {VERSION_ID}.pkl')"""))

nb.cells = cells

with open(r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v8_0.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Notebook generated successfully.")
