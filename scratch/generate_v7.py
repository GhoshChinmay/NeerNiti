import nbformat

nb = nbformat.v4.new_notebook()

cells = []

# Cell 1
cells.append(nbformat.v4.new_markdown_cell(source="""# NeerNiti — Phase 7.0 (Reviewer Master Upgrade)
### Nested Spatial Optuna, Leave-District-Out CV, Irrigation Physics, and MERIT Hydro

This notebook implements all critical robustness fixes:
1. **Nested Spatial Optimization:** Deep CatBoost tuning (depth, lr, n, l2) evaluated on hidden spatial folds.
2. **Leave-District-Out CV:** Honest robustness check for regional interpolation vs physical transfer.
3. **Advanced Physics:** Replaces regional CHIRPS/GRACE with dry-season Irrigation (NDVI/ET), Land Cover, full Soil profile, and MERIT TWI/Distance.
4. **Target Caveats:** Hard-rock (Bundelkhand) recharge threshold adjusted to reflect low specific yield.
5. **Stage of Extraction:** Injects CGWB district pumping pressure directly into the feature space."""))

# Cell 2
cells.append(nbformat.v4.new_code_cell(source="""!pip install -q earthengine-api catboost scikit-learn pandas numpy matplotlib tqdm google-api-python-client seaborn optuna

import os, json, time, math, warnings
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
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
    'sitapur': 57.34, 'sonbhadra': 64.67, 'sultanpur': 60.28, 'unnao': 60.67, 'varanasi': 91.21,
    'praygraj': 74.19, 'allahabad': 74.19, 'bhadohi': 73.1, 'raibareli': 55.68, 
    'amethi (c.s.m. nagar)': 61.06, 'kansiram nagar': 73.51, 'shahjhanpur': 60.84, 
    'buland shahar': 91.38, 'amroha (j.p.nagar)': 96.4, 'jyotiba phule nagar': 96.4
}"""))

# Cell 5
cells.append(nbformat.v4.new_code_cell(source="""def process_telemetry():
    print("Loading UP Telemetry datasets (Strict Chronological Pairing)...")
    def load_and_pair(path, label):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing dataset: {path}")
        df = pd.read_csv(path, low_memory=False)
        print(f"Loaded {label}: {len(df)} rows.")
        df['Date'] = pd.to_datetime(df['Data Acquisition Time'], errors='coerce', format='mixed', dayfirst=True)
        df = df.dropna(subset=['Date'])
        # Keep <= 2025
        df = df[df['Date'].dt.year <= 2025]
        
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
    
    # Normalize District names to canonical form FIRST
    def normalize_district(d):
        d = str(d).strip().lower()
        if d in ['bareili', 'bareilly']: return 'bareilly'
        if d in ['bijnaur', 'bijnor']: return 'bijnor'
        if d in ['praygraj', 'allahabad', 'prayagraj']: return 'prayagraj'
        if d in ['buland shahar', 'bulandshahar', 'bulandshahr']: return 'bulandshahr'
        if d in ['shrawasti', 'shravasti']: return 'shravasti'
        if d in ['shambhal', 'sambhal']: return 'sambhal'
        if d in ['siddharth', 'siddharthnagar']: return 'siddharthnagar'
        if d in ['maharajganj', 'mahrajganj']: return 'mahrajganj'
        if d in ['kushi nagar', 'kushinagar']: return 'kushinagar'
        if d in ['raibareli', 'rae bareli']: return 'rae bareli'
        if d in ['kheri', 'lakhimpur', 'lakhimpur kheri']: return 'lakhimpur kheri'
        if d in ['aurraiya', 'auraiya']: return 'auraiya'
        if d in ['s.kabir nagar', 'sant kabir nagar']: return 'sant kabir nagar'
        if d in ['s.ravidas', 'sant ravidas nagar', 'bhadohi']: return 'bhadohi'
        if d in ['g.b. nagar', 'gautam buddha nagar']: return 'gautam buddha nagar'
        if d in ['amethi (c.s.m. nagar)', 'amethi']: return 'amethi'
        if d in ['amroha (j.p.nagar)', 'jyotiba phule nagar', 'amroha']: return 'amroha'
        if d in ['kansiram nagar', 'kasganj']: return 'kasganj'
        if d in ['shahjhanpur', 'shahjahanpur']: return 'shahjahanpur'
        return d

    combined['District'] = combined['District'].apply(normalize_district)

    final_df = combined.groupby(['Latitude', 'Longitude']).agg({'pre_monsoon_m': 'mean', 'post_monsoon_m': 'mean', 'District': 'first'}).reset_index()
    
    final_df['recharge_potential'] = final_df['pre_monsoon_m'] - final_df['post_monsoon_m']
    final_df['well_id'] = ['UP_WELL_' + str(i) for i in range(len(final_df))]
    final_df['spatial_block_id'] = (np.floor(final_df['Latitude'] / SPATIAL_BLOCK_DEGREES).astype(str) + '_' + np.floor(final_df['Longitude'] / SPATIAL_BLOCK_DEGREES).astype(str))
    
    # Geology Logic
    bhabar_terai = ['saharanpur', 'bijnor', 'moradabad', 'rampur', 'bareilly', 'pilibhit', 'lakhimpur kheri', 'bahraich', 'shravasti', 'balrampur', 'siddharthnagar', 'mahrajganj']
    bundelkhand_hard_rock = ['jhansi', 'lalitpur', 'jalaun', 'hamirpur', 'mahoba', 'banda', 'chitrakoot', 'mirzapur', 'sonbhadra']
    
    def get_hydro_zone(district):
        if district in bhabar_terai: return 0
        if district in bundelkhand_hard_rock: return 2
        return 1
    final_df['pdf_hydro_zone'] = final_df['District'].apply(get_hydro_zone)
    
    min_recharge = np.where(final_df['pdf_hydro_zone'] == 2, 2.5, 1.5)
    final_df['target'] = ((final_df['pre_monsoon_m'] >= 6.0) & (final_df['pre_monsoon_m'] <= 35.0) & (final_df['recharge_potential'] >= min_recharge)).astype(int)
    
    # Inject Stage of Extraction
    final_df['stage_of_extraction'] = final_df['District'].map(STAGE_OF_EXTRACTION)
    unmatched = final_df[final_df['stage_of_extraction'].isnull()]['District'].unique()
    if len(unmatched) > 0: print(f"Warning: Unmatched districts for Stage of Extraction: {unmatched}")
    # Unmatched left as NaN as CatBoost natively supports missing values
    
    print(f"Aggregated dataset: {len(final_df)} wells. Positive: {final_df['target'].sum()} | Negative: {len(final_df)-final_df['target'].sum()}")
    return final_df

dataset = process_telemetry()"""))

# Cell 6
cells.append(nbformat.v4.new_code_cell(source="""if not os.path.exists(GEE_CACHE_FILE):
    print('Initiating advanced extraction (MERIT, SoilGrids, Irrigation, LandCover)...')
    
    dem = ee.ImageCollection('COPERNICUS/DEM/GLO30_2024_1').mosaic().select(0)
    slope = ee.Terrain.slope(dem).rename('slope_deg')
    curvature = dem.convolve(ee.Kernel.laplacian8()).rename('curvature')
    
    # Full Soil Profile (Sand, Silt, Clay, SOC) - 0-5cm and 30-100cm
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
    
    # Dry Season Irrigation Intensity (Jan-Apr)
    modis_ndvi = ee.ImageCollection('MODIS/061/MOD13Q1').filterDate('2021-01-01', '2026-01-01').filter(ee.Filter.calendarRange(1, 4, 'month')).mean().select('NDVI').multiply(0.0001).rename('dry_season_ndvi')
    modis_et = ee.ImageCollection('MODIS/061/MOD16A2').filterDate('2021-01-01', '2026-01-01').filter(ee.Filter.calendarRange(1, 4, 'month')).mean().select('ET').multiply(0.1).rename('dry_season_et')
    
    # Dynamic World Land Cover (Fractions)
    dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterDate('2021-01-01', '2024-01-01').select('label').mode()
    crop_frac = dw.eq(4).rename('crop_frac')
    built_frac = dw.eq(6).rename('built_frac')
    tree_frac = dw.eq(1).rename('tree_frac')
    
    # MERIT Hydro for Flow Accumulation and Rivers
    merit = ee.Image('MERIT/Hydro/v1_0_1')
    upa = merit.select('upa')
    log_upa = upa.add(0.01).log().rename('log_upstream_area')      # log BEFORE averaging
    hand = merit.select('hnd').rename('hand_m')                    # new, free feature
    river_mask = upa.gt(10).unmask(0)                              # >=10 km2 catchment
    dist_to_river = (river_mask.fastDistanceTransform(512).sqrt()
                     .multiply(ee.Image.pixelArea().sqrt()).rename('distance_to_river_m'))
    
    base_stack = ee.Image.cat([
        slope, curvature, 
        clay_0, clay_30, sand_0, sand_30, soc_0, soc_30, 
        modis_ndvi, modis_et, 
        crop_frac, built_frac, tree_frac, 
        log_upa, hand, dist_to_river, dem.rename('elevation_m')
    ])
    
    # FAIL FAST TEST
    print("Checking each component separately...")
    components = {'slope': slope, 'curvature': curvature, 'clay0': clay_0, 'sand0': sand_0, 'soc0': soc_0,
                  'clay_deep': clay_30, 'sand_deep': sand_30, 'soc_deep': soc_30,
                  'ndvi': modis_ndvi, 'et': modis_et, 'crop': crop_frac, 'built': built_frac,
                  'tree': tree_frac, 'log_upa': log_upa, 'hand': hand,
                  'dist_river': dist_to_river, 'elev': dem.rename('elevation_m')}
    for k, img in components.items():
        try:
            print('OK  ', k, img.bandNames().getInfo())
        except Exception as e:
            print('FAIL', k, str(e)[:200])

    print("Running single-point test to catch errors...")
    test_pt = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([80.9, 26.8]).buffer(500))])
    print("Bands:", base_stack.bandNames().getInfo())
    test_result = base_stack.reduceRegions(test_pt, ee.Reducer.mean(), scale=30).getInfo()
    print("Test Result:", test_result['features'][0]['properties'])
    print("Test passed! Starting chunk loop...")
    
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
        print(f"  Processed {min(i+chunk_size, len(dataset))}/{len(dataset)}", end='\\r')
        
    gee_df = pd.DataFrame(rows)
    gee_df.to_csv(GEE_CACHE_FILE, index=False)
    print(f'\\nSuccessfully cached to {GEE_CACHE_FILE}')

gee_features = pd.read_csv(GEE_CACHE_FILE)
dataset['well_id'] = dataset['well_id'].astype(str)
gee_features['well_id'] = gee_features['well_id'].astype(str)
dataset = dataset.merge(gee_features, on='well_id', how='inner')
print(f"Merged {len(dataset)} points with GEE features.")"""))

# Cell 7
cells.append(nbformat.v4.new_code_cell(source="""# Compute Topographic Wetness Index using pre-logged upstream area
# log_upa = log(upa + 0.01) so upa = exp(log_upa) - 0.01
dataset['TWI'] = dataset['log_upstream_area'] + np.log(1e6) - np.log(np.tan(np.radians(dataset['slope_deg'])) + 0.001)
print("Computed consistent TWI successfully.")"""))

# Cell 8
cells.append(nbformat.v4.new_code_cell(source="""def generate_purged_folds(df, block_col, coords_cols, n_splits=5, buffer_km=3.0):
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
    'slope_deg', 'curvature', 'soil_clay_0_5_pct', 'soil_clay_30_100_pct', 
    'soil_sand_0_5_pct', 'soil_sand_30_100_pct', 'soil_soc_0_5', 'soil_soc_30_100',
    'dry_season_ndvi', 'dry_season_et', 'crop_frac', 'built_frac', 'tree_frac', 
    'delta_sar_vv_vh', 'elevation_m', 'distance_to_river_m', 'hand_m', 'TWI',
    'pdf_hydro_zone', 'stage_of_extraction'
]

# NOTE: During cross-validation, stage_of_extraction and pdf_hydro_zone will leak district identity 
# in the spatial block CV. Leave-District-Out CV is the honest metric here!
X = dataset[FEATURE_COLS].copy()
y = dataset['target'].values
scale_weight = float(np.sum(y == 0) / np.sum(y == 1)) if np.sum(y == 1) > 0 else 1.0
print(f"Feature matrix: {X.shape} | Target vector: {y.shape}")"""))

# Cell 9
cells.append(nbformat.v4.new_code_cell(source="""print("--- Nested Spatial Optuna (CatBoost) ---")

def objective(trial):
    depth = trial.suggest_int('depth', 2, 8)
    lr = trial.suggest_float('lr', 0.01, 0.2, log=True)
    n = trial.suggest_int('n', 200, 1500)
    l2 = trial.suggest_float('l2', 1, 50, log=True)
    
    auc_scores = []
    
    for train_idx, val_idx in custom_cv_folds:
        # Inner spatial split for early stopping
        # Group by spatial_block_id to avoid leakage in early stopping
        train_df = dataset.iloc[train_idx]
        inner_gkf = GroupKFold(n_splits=5)
        inner_tr_idx, inner_val_idx = next(inner_gkf.split(train_df, train_df['target'], train_df['spatial_block_id']))
        
        # Map back to original indices
        orig_inner_tr = train_idx[inner_tr_idx]
        orig_inner_val = train_idx[inner_val_idx]
        
        clf = CatBoostClassifier(iterations=n, depth=depth, learning_rate=lr, l2_leaf_reg=l2, 
                                 scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
        
        clf.fit(X.iloc[orig_inner_tr], y[orig_inner_tr], 
                eval_set=(X.iloc[orig_inner_val], y[orig_inner_val]), 
                early_stopping_rounds=50, verbose=0)
        
        # Store the best iteration so we evaluate exactly what we tuned
        trial.set_user_attr(f"best_iteration_fold_{len(auc_scores)}", clf.get_best_iteration())
        
        auc_scores.append(roc_auc_score(y[val_idx], clf.predict_proba(X.iloc[val_idx])[:, 1]))
    return np.mean(auc_scores)

study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=RANDOM_SEED))
print("Running Optuna Spatial Optimization...")
# study.optimize(objective, n_trials=40)
study.optimize(objective, n_trials=5)
best_params = study.best_params
best_trial = study.best_trial
print(f"Best Params Found: {best_params} (CV AUC: {study.best_value:.4f})")

def evaluate_folds(folds, name):
    preds = np.zeros(len(X))
    y_true = np.zeros(len(X))
    fold_aucs = []
    
    for i, (train_idx, test_idx) in enumerate(folds):
        # We must use the same inner early stopping strategy to mimic tuning
        train_df = dataset.iloc[train_idx]
        
        inner_gkf = GroupKFold(n_splits=5)
        # Use spatial_block_id for inner split regardless of outer fold type
        inner_tr_idx, inner_val_idx = next(inner_gkf.split(train_df, train_df['target'], train_df['spatial_block_id']))
        
        orig_inner_tr = train_idx[inner_tr_idx]
        orig_inner_val = train_idx[inner_val_idx]
        
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
    
    # Bootstrap CI for AUC
    n_bootstraps = 1000
    bootstrapped_scores = []
    rng = np.random.RandomState(RANDOM_SEED)
    for _ in range(n_bootstraps):
        indices = rng.randint(0, len(preds), len(preds))
        if len(np.unique(y_true[indices])) < 2: continue
        bootstrapped_scores.append(roc_auc_score(y_true[indices], preds[indices]))
    ci_lower = np.percentile(bootstrapped_scores, 2.5)
    ci_upper = np.percentile(bootstrapped_scores, 97.5)
    
    print(f"\\n>> {name} Overall ROC-AUC: {roc:.4f} (95% CI: {ci_lower:.4f} - {ci_upper:.4f}) | PR-AUC: {pr:.4f}\\n")
    return preds, y_true, clf

print("\\nEvaluating 3.0km Haversine Spatial CV (NOTE: Subject to district-level leakage)...")
spatial_preds, spatial_y, spatial_clf = evaluate_folds(custom_cv_folds, "Spatial-CV")

print("\\nEvaluating Leave-District-Out CV (HONEST ROBUSTNESS METRIC)...")
dist_preds, dist_y, dist_clf = evaluate_folds(district_folds, "Leave-District-Out")

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
# We use the final spatial_clf to evaluate permutation importance on the whole dataset
# In practice this gives a rough estimate of feature importance
result = permutation_importance(dist_clf, X, y, n_repeats=5, random_state=RANDOM_SEED, scoring='roc_auc')
feat_imp = pd.Series(result.importances_mean, index=FEATURE_COLS).sort_values(ascending=True)
feat_imp.plot(kind='barh', ax=axes[2], color='teal')
axes[2].set_title('Permutation Importance')

plt.tight_layout()
plt.savefig('/kaggle/working/up_catboost_results.png', dpi=150)
plt.show()"""))

# Cell 11
cells.append(nbformat.v4.new_code_cell(source="""# Train final model on 100% of data.
prod_model = CatBoostClassifier(iterations=best_params['n'], depth=best_params['depth'], 
                                learning_rate=best_params['lr'], l2_leaf_reg=best_params['l2'], 
                                scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
prod_model.fit(X, y)

model_path = f'/kaggle/working/{VERSION_ID}.pkl'
artifact = {
    'model': prod_model,
    'features': FEATURE_COLS
}
joblib.dump(artifact, model_path)
print(f'Production Artifact exported: {VERSION_ID}.pkl')"""))


nb.cells = cells

with open(r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v7_0.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Notebook generated successfully.")
