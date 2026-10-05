import nbformat

nb = nbformat.v4.new_notebook()
cells = []

cells.append(nbformat.v4.new_markdown_cell(source="""# NeerNiti — Phase 9.0 (Execution of Phase 0 & 1)
### Strict Evaluation Protocol, Deployable Features Only, and Baselines

**Key Changes:**
1. **Holdout Vault:** 10 districts are completely withheld from CV and tuning.
2. **Leak Removed:** `pre_monsoon_m` and `rainfall_anomaly_mm` (which required well history) are dropped. The model strictly uses deployable features (GEE statics + rainfall scenario).
3. **Repeated LODO:** Uses `StratifiedGroupKFold` repeated over 3 random seeds.
4. **Baselines:** A Logistic Regression (Elastic Net) is evaluated on the exact same folds.
5. **No In-Sample Metrics:** All permutation importance is calculated exclusively on Out-Of-Fold (OOF) rows."""))

cells.append(nbformat.v4.new_code_cell(source="""!pip install -q earthengine-api catboost scikit-learn pandas numpy matplotlib tqdm google-api-python-client seaborn optuna

import os, json, time, warnings
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
import optuna
from optuna.samplers import TPESampler
import joblib
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    accuracy_score, classification_report, average_precision_score, precision_recall_curve
)
from datetime import datetime, timezone
import ee
from google.oauth2 import service_account

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)
RUNTIME = 'kaggle' if os.path.exists('/kaggle') else 'colab'
print(f'Runtime: {RUNTIME.upper()}')"""))

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

cells.append(nbformat.v4.new_code_cell(source="""TEL_2021_CSV_PATH = '/kaggle/input/datasets/chinmay302/neerniti/gwl_tel_6_hourly_upgw_up_2021_2025.csv'
GEE_CACHE_FILE = '/kaggle/working/up_gee_cache_v9_0.csv'
GEE_BUFFER_M = 500
VERSION_ID = f'neerniti_up_v9_0_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'
RANDOM_SEEDS = [42, 100, 2024]

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

cells.append(nbformat.v4.new_code_cell(source="""def process_telemetry():
    print("Loading UP Telemetry datasets (Building Well-Year Panel)...")
    if not os.path.exists(TEL_2021_CSV_PATH): raise FileNotFoundError("Missing dataset")
    
    df = pd.read_csv(TEL_2021_CSV_PATH, low_memory=False)
    df['Date'] = pd.to_datetime(df['Data Acquisition Time'], errors='coerce', format='mixed', dayfirst=True)
    df = df.dropna(subset=['Date'])
    df = df[df['Date'].dt.year <= 2025]
    df['Month'] = df['Date'].dt.month
    df['Year'] = df['Date'].dt.year
    lvl_col = [c for c in df.columns if 'meter' in c.lower()][0]
    df[lvl_col] = pd.to_numeric(df[lvl_col], errors='coerce').abs()
    
    pre = df[df['Month'].isin([4, 5])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
    pre.rename(columns={lvl_col: 'pre_monsoon_m'}, inplace=True)
    post = df[df['Month'].isin([10, 11])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
    post.rename(columns={lvl_col: 'post_monsoon_m'}, inplace=True)
    
    panel_df = pd.merge(pre, post, on=['Latitude', 'Longitude', 'Year', 'District'], how='inner')
    
    def normalize_district(d):
        d = str(d).strip().lower()
        aliases = {'bareili':'bareilly', 'bijnaur':'bijnor', 'praygraj':'prayagraj', 'allahabad':'prayagraj',
                   'buland shahar':'bulandshahr', 'bulandshahar':'bulandshahr', 'shrawasti':'shravasti',
                   'shambhal':'sambhal', 'siddharth':'siddharthnagar', 'maharajganj':'mahrajganj',
                   'kushi nagar':'kushinagar', 'raibareli':'rae bareli', 'kheri':'lakhimpur kheri',
                   'lakhimpur':'lakhimpur kheri', 'aurraiya':'auraiya', 's.kabir nagar':'sant kabir nagar',
                   's.ravidas':'bhadohi', 'sant ravidas nagar':'bhadohi', 'g.b. nagar':'gautam buddha nagar',
                   'amethi (c.s.m. nagar)':'amethi', 'amroha (j.p.nagar)':'amroha', 'jyotiba phule nagar':'amroha',
                   'kansiram nagar':'kasganj', 'shahjhanpur':'shahjahanpur'}
        return aliases.get(d, d)

    panel_df['District'] = panel_df['District'].apply(normalize_district)
    
    locations = panel_df[['Latitude', 'Longitude']].drop_duplicates().reset_index(drop=True)
    locations['well_id'] = ['UP_WELL_' + str(i) for i in range(len(locations))]
    panel_df = panel_df.merge(locations, on=['Latitude', 'Longitude'], how='left')
    
    year_counts = panel_df.groupby('well_id').size()
    valid_wells = year_counts[year_counts >= 3].index
    panel_df = panel_df[panel_df['well_id'].isin(valid_wells)].copy()
    
    panel_df['recharge_potential'] = panel_df['pre_monsoon_m'] - panel_df['post_monsoon_m']
    
    bhabar_terai = ['saharanpur', 'bijnor', 'moradabad', 'rampur', 'bareilly', 'pilibhit', 'lakhimpur kheri', 'bahraich', 'shravasti', 'balrampur', 'siddharthnagar', 'mahrajganj']
    bundelkhand = ['jhansi', 'lalitpur', 'jalaun', 'hamirpur', 'mahoba', 'banda', 'chitrakoot', 'mirzapur', 'sonbhadra']
    def get_hydro_zone(d):
        if d in bhabar_terai: return 0
        if d in bundelkhand: return 2
        return 1
    panel_df['pdf_hydro_zone'] = panel_df['District'].apply(get_hydro_zone)
    
    min_recharge = np.where(panel_df['pdf_hydro_zone'] == 2, 2.5, 1.5)
    panel_df['target'] = ((panel_df['pre_monsoon_m'] >= 6.0) & (panel_df['pre_monsoon_m'] <= 35.0) & (panel_df['recharge_potential'] >= min_recharge)).astype(int)
    
    panel_df['stage_of_extraction'] = panel_df['District'].map(STAGE_OF_EXTRACTION)
    
    # Check for unmatched districts in Stage of Extraction dictionary
    unmatched = set(panel_df['District'].unique()) - set(STAGE_OF_EXTRACTION.keys())
    if unmatched: print(f"WARNING: Unmatched districts in Stage of Extraction: {unmatched}")
    
    return panel_df, locations

panel_df, unique_locations = process_telemetry()"""))

cells.append(nbformat.v4.new_code_cell(source="""if not os.path.exists(GEE_CACHE_FILE):
    print('Initiating advanced extraction...')
    dem = ee.ImageCollection('COPERNICUS/DEM/GLO30_2024_1').mosaic().select(0)
    slope = ee.Terrain.slope(dem).rename('slope_deg')
    curvature = dem.convolve(ee.Kernel.laplacian8()).rename('curvature')
    
    def soil_30_100(asset, prefix, divisor, name):
        img = ee.Image(asset)
        mid = (img.select(f'{prefix}_30-60cm_mean').multiply(30).add(img.select(f'{prefix}_60-100cm_mean').multiply(40)).divide(70))
        return mid.divide(divisor).rename(name)

    clay_0 = ee.Image('projects/soilgrids-isric/clay_mean').select('clay_0-5cm_mean').divide(10).rename('soil_clay_0_5_pct')
    clay_30 = soil_30_100('projects/soilgrids-isric/clay_mean', 'clay', 10, 'soil_clay_30_100_pct')
    sand_0 = ee.Image('projects/soilgrids-isric/sand_mean').select('sand_0-5cm_mean').divide(10).rename('soil_sand_0_5_pct')
    sand_30 = soil_30_100('projects/soilgrids-isric/sand_mean', 'sand', 10, 'soil_sand_30_100_pct')
    soc_0 = ee.Image('projects/soilgrids-isric/soc_mean').select('soc_0-5cm_mean').divide(10).rename('soil_soc_0_5')
    soc_30 = soil_30_100('projects/soilgrids-isric/soc_mean', 'soc', 10, 'soil_soc_30_100')
    
    modis_ndvi = ee.ImageCollection('MODIS/061/MOD13Q1').filterDate('2021-01-01', '2026-01-01').filter(ee.Filter.calendarRange(1, 4, 'month')).mean().select('NDVI').multiply(0.0001).rename('dry_season_ndvi')
    dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterDate('2021-01-01', '2024-01-01').select('label').mode()
    crop_frac = dw.eq(4).rename('crop_frac')
    built_frac = dw.eq(6).rename('built_frac')
    tree_frac = dw.eq(1).rename('tree_frac')
    
    merit = ee.Image('MERIT/Hydro/v1_0_1')
    upa = merit.select('upa')
    log_upa = upa.add(0.01).log().rename('log_upstream_area')
    hand = merit.select('hnd').rename('hand_m')
    river_mask = upa.gt(10).unmask(0)
    dist_to_river = (river_mask.fastDistanceTransform(512).sqrt().multiply(ee.Image.pixelArea().sqrt()).rename('distance_to_river_m'))
    
    chirps_bands = [ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate(f'{y}-06-01', f'{y}-10-01').sum().rename(f'chirps_{y}') for y in range(2021, 2026)]
    base_stack = ee.Image.cat([slope, curvature, clay_0, clay_30, sand_0, sand_30, soc_0, soc_30, modis_ndvi, crop_frac, built_frac, tree_frac, log_upa, hand, dist_to_river, dem.rename('elevation_m')] + chirps_bands)
    
    rows = []
    for i in range(0, len(unique_locations), 50):
        chunk = unique_locations.iloc[i:i+50]
        feats = [ee.Feature(ee.Geometry.Point([r['Longitude'], r['Latitude']]), {'well_id': str(r['well_id'])}) for _, r in chunk.iterrows()]
        res = base_stack.reduceRegions(collection=ee.FeatureCollection(feats).map(lambda f: f.buffer(GEE_BUFFER_M)), reducer=ee.Reducer.mean(), scale=30, tileScale=4).getInfo()
        for f in res['features']: rows.append(f['properties'])
        print(f"  Processed {min(i+50, len(unique_locations))}/{len(unique_locations)}", end='\\r')
    pd.DataFrame(rows).to_csv(GEE_CACHE_FILE, index=False)

gee_features = pd.read_csv(GEE_CACHE_FILE)
gee_features['well_id'] = gee_features['well_id'].astype(str)
panel_df['well_id'] = panel_df['well_id'].astype(str)

static_cols = [c for c in gee_features.columns if not c.startswith('chirps_') and c != 'well_id']
panel_df = panel_df.merge(gee_features[['well_id'] + static_cols], on='well_id', how='left')

def assign_chirps(row):
    w = gee_features[gee_features['well_id'] == row['well_id']]
    return w.iloc[0][f'chirps_{row["Year"]}'] if len(w) > 0 and f'chirps_{row["Year"]}' in w.columns else np.nan

panel_df['monsoon_rainfall_mm'] = panel_df.apply(assign_chirps, axis=1)
panel_df['TWI'] = panel_df['log_upstream_area'] + np.log(1e6) - np.log(np.tan(np.radians(panel_df['slope_deg'])) + 0.001)
"""))

cells.append(nbformat.v4.new_code_cell(source="""print("--- Phase 0 Protocol: Untouched Holdout Generation ---")
dist_summary = panel_df.groupby(['District', 'pdf_hydro_zone']).agg(n_wells=('well_id', 'nunique'), pos_rate=('target', 'mean')).reset_index()

# 10 Holdout districts stratified roughly by hydro zone
holdout_districts = []
np.random.seed(42)
for zone in [0, 1, 2]:
    d_zone = dist_summary[dist_summary['pdf_hydro_zone'] == zone]
    n_sample = 2 if zone != 1 else 6
    if len(d_zone) > 0:
        holdout_districts.extend(np.random.choice(d_zone['District'], size=min(n_sample, len(d_zone)), replace=False).tolist())

panel_train_val = panel_df[~panel_df['District'].isin(holdout_districts)].copy()
panel_holdout = panel_df[panel_df['District'].isin(holdout_districts)].copy()

print(f"Set aside {len(holdout_districts)} Holdout Districts. Training/CV Pool: {len(panel_train_val)} rows. Holdout Pool: {len(panel_holdout)} rows.")"""))

cells.append(nbformat.v4.new_code_cell(source="""# CRITICAL FIX: Removed pre_monsoon_m (Target Leakage)
# Only strictly deployable features remain
DEPLOYABLE_FEATURES = [
    'monsoon_rainfall_mm', 'slope_deg', 'curvature', 'soil_clay_0_5_pct', 'soil_clay_30_100_pct', 
    'soil_sand_0_5_pct', 'soil_sand_30_100_pct', 'soil_soc_0_5', 'soil_soc_30_100',
    'dry_season_ndvi', 'crop_frac', 'built_frac', 'tree_frac', 
    'elevation_m', 'distance_to_river_m', 'hand_m', 'TWI',
    'pdf_hydro_zone', 'stage_of_extraction'
]

X_cv = panel_train_val[DEPLOYABLE_FEATURES].copy()
y_cv = panel_train_val['target'].values
groups_cv = panel_train_val['District'].values
scale_weight = float(np.sum(y_cv == 0) / np.sum(y_cv == 1)) if np.sum(y_cv == 1) > 0 else 1.0"""))

cells.append(nbformat.v4.new_code_cell(source="""print("--- LODO Tuning (CatBoost) ---")
def objective(trial):
    depth = trial.suggest_int('depth', 3, 5)
    lr = trial.suggest_float('lr', 0.01, 0.1, log=True)
    n = trial.suggest_int('n', 200, 1000)
    l2 = trial.suggest_float('l2', 1, 50, log=True)
    
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = []
    
    for train_idx, val_idx in sgkf.split(X_cv, y_cv, groups_cv):
        inner_gkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
        inner_tr_idx, inner_val_idx = next(inner_gkf.split(X_cv.iloc[train_idx], y_cv[train_idx], groups_cv[train_idx]))
        
        orig_inner_tr, orig_inner_val = train_idx[inner_tr_idx], train_idx[inner_val_idx]
        
        clf = CatBoostClassifier(iterations=n, depth=depth, learning_rate=lr, l2_leaf_reg=l2, 
                                 scale_pos_weight=scale_weight, random_seed=42, verbose=0)
        clf.fit(X_cv.iloc[orig_inner_tr], y_cv[orig_inner_tr], eval_set=(X_cv.iloc[orig_inner_val], y_cv[orig_inner_val]), early_stopping_rounds=50, verbose=0)
        auc_scores.append(roc_auc_score(y_cv[val_idx], clf.predict_proba(X_cv.iloc[val_idx])[:, 1]))
    return np.mean(auc_scores)

study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
print("Running Optuna LODO Optimization (30 Trials)...")
study.optimize(objective, n_trials=30)
best_params = study.best_params
print(f"Best Params Found: {best_params} (CV AUC: {study.best_value:.4f})")"""))

cells.append(nbformat.v4.new_code_cell(source="""print("\\n--- Repeated Stratified LODO CV Evaluation ---")
cb_aucs, lr_aucs = [], []

for seed in RANDOM_SEEDS:
    print(f"\\nEvaluating Seed {seed}...")
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    
    for fold, (train_idx, test_idx) in enumerate(sgkf.split(X_cv, y_cv, groups_cv)):
        # 1. CatBoost
        inner_gkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        inner_tr_idx, inner_val_idx = next(inner_gkf.split(X_cv.iloc[train_idx], y_cv[train_idx], groups_cv[train_idx]))
        orig_inner_tr, orig_inner_val = train_idx[inner_tr_idx], train_idx[inner_val_idx]
        
        cb = CatBoostClassifier(iterations=best_params['n'], depth=best_params['depth'], learning_rate=best_params['lr'], l2_leaf_reg=best_params['l2'], scale_pos_weight=scale_weight, random_seed=seed, verbose=0)
        cb.fit(X_cv.iloc[orig_inner_tr], y_cv[orig_inner_tr], eval_set=(X_cv.iloc[orig_inner_val], y_cv[orig_inner_val]), early_stopping_rounds=50, verbose=0)
        cb_auc = roc_auc_score(y_cv[test_idx], cb.predict_proba(X_cv.iloc[test_idx])[:, 1])
        cb_aucs.append(cb_auc)
        
        # 2. Logistic Regression (Elastic Net Baseline)
        pipeline = Pipeline([('scaler', StandardScaler()), ('lr', LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=0.5, class_weight='balanced', max_iter=1000, random_state=seed))])
        pipeline.fit(X_cv.iloc[train_idx].fillna(0), y_cv[train_idx])
        lr_auc = roc_auc_score(y_cv[test_idx], pipeline.predict_proba(X_cv.iloc[test_idx].fillna(0))[:, 1])
        lr_aucs.append(lr_auc)
        
        print(f"  Fold {fold+1} | CatBoost AUC: {cb_auc:.4f} | Logistic Regression AUC: {lr_auc:.4f}")

print(f"\\n>> FINAL CV RESULTS (CatBoost): {np.mean(cb_aucs):.4f} ± {np.std(cb_aucs):.4f} ROC-AUC")
print(f">> FINAL CV RESULTS (LogReg Baseline): {np.mean(lr_aucs):.4f} ± {np.std(lr_aucs):.4f} ROC-AUC")"""))

nb.cells = cells
with open(r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v9_0.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)
print("Notebook generated successfully.")
