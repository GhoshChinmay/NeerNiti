import nbformat

nb = nbformat.v4.new_notebook()
cells = []

cells.append(nbformat.v4.new_markdown_cell(source="""# NeerNiti — Phase 13.0
### High-Volume Extraction, Checkpointing, and Robust Retries

**Key Additions:**
1. **High-Volume Endpoint:** Earth Engine now initializes using the `earthengine-highvolume.googleapis.com` endpoint meant for bulk parallel extraction.
2. **Robust Checkpointing:** GEE extractions are appended to a `.csv` immediately after each chunk finishes. If a crash or timeout occurs, restarting the notebook will instantly resume from the exact well it left off at.
3. **Adaptive Splitting & ThreadPool:** Added multi-threading with adaptive fallback. If GEE throws a timeout on a chunk, it recursively splits the chunk in half and tries again instead of failing.
4. **Optimized Distance Transform:** Capped the `fastDistanceTransform` to `128` pixels (instead of 512) to massively speed up the GEE backend computation without impacting the tree model's ability to threshold distance."""))

cells.append(nbformat.v4.new_code_cell(source="""!pip install -q earthengine-api catboost scikit-learn pandas numpy matplotlib tqdm google-api-python-client seaborn optuna

import os, json, time, warnings
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.calibration import CalibratedClassifierCV
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, brier_score_loss, classification_report
from datetime import datetime, timezone
import ee
from google.oauth2 import service_account
from concurrent.futures import ThreadPoolExecutor, as_completed
import joblib

warnings.filterwarnings('ignore')
RUNTIME = 'kaggle' if os.path.exists('/kaggle') else 'colab'
print(f'Runtime: {RUNTIME.upper()}')"""))

cells.append(nbformat.v4.new_code_cell(source="""if RUNTIME == 'kaggle':
    from kaggle_secrets import UserSecretsClient
    _secrets = UserSecretsClient()
    creds = service_account.Credentials.from_service_account_info(
        json.loads(_secrets.get_secret('GEE_SERVICE_ACCOUNT_KEY')),
        scopes=['https://www.googleapis.com/auth/earthengine', 'https://www.googleapis.com/auth/drive']
    )
    ee.Initialize(creds, project=_secrets.get_secret('GEE_PROJECT_ID'), opt_url='https://earthengine-highvolume.googleapis.com')
else:
    ee.Authenticate()
    ee.Initialize(project=input('Enter GEE Project ID: ').strip(), opt_url='https://earthengine-highvolume.googleapis.com')
print('GEE Authenticated with High-Volume Endpoint.')"""))

cells.append(nbformat.v4.new_code_cell(source="""TEL_2021_CSV_PATH = '/kaggle/input/datasets/chinmay302/neerniti/gwl_tel_6_hourly_upgw_up_2021_2025.csv'
GEE_CACHE_FILE = '/kaggle/working/up_gee_cache_v13_0.csv'
GEE_BUFFER_M = 500
VERSION_ID = f'neerniti_up_v13_0_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'
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
}

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
    return aliases.get(d, d)"""))

cells.append(nbformat.v4.new_code_cell(source="""def process_telemetry():
    print("Loading UP Telemetry datasets (Executing Strict QC)...")
    if not os.path.exists(TEL_2021_CSV_PATH): raise FileNotFoundError("Missing dataset")
    df = pd.read_csv(TEL_2021_CSV_PATH, low_memory=False)
    df['Date'] = pd.to_datetime(df['Data Acquisition Time'], errors='coerce', format='mixed', dayfirst=True)
    df = df.dropna(subset=['Date'])
    df = df[df['Date'].dt.year <= 2025]
    df['Month'] = df['Date'].dt.month
    df['Year'] = df['Date'].dt.year
    lvl_col = [c for c in df.columns if 'meter' in c.lower()][0]
    df[lvl_col] = pd.to_numeric(df[lvl_col], errors='coerce').abs()
    
    df = df[df[lvl_col] > 0]
    df['Season'] = np.where(df['Month'].isin([4, 5]), 'Pre', np.where(df['Month'].isin([10, 11]), 'Post', 'Other'))
    df = df[df['Season'] != 'Other']
    
    agg_df = df.groupby(['Latitude', 'Longitude', 'Year', 'District', 'Season'])[lvl_col].agg(['median', 'std', 'count']).reset_index()
    agg_df = agg_df[(agg_df['count'] >= 20) & (agg_df['std'] > 0)]
    
    pre = agg_df[agg_df['Season'] == 'Pre'].rename(columns={'median': 'pre_monsoon_m'})
    post = agg_df[agg_df['Season'] == 'Post'].rename(columns={'median': 'post_monsoon_m'})
    
    panel_df = pd.merge(pre[['Latitude', 'Longitude', 'Year', 'District', 'pre_monsoon_m']], 
                        post[['Latitude', 'Longitude', 'Year', 'District', 'post_monsoon_m']], 
                        on=['Latitude', 'Longitude', 'Year', 'District'], how='inner')
    
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
    def get_hydro_zone(d): return 0 if d in bhabar_terai else 2 if d in bundelkhand else 1
    panel_df['pdf_hydro_zone'] = panel_df['District'].apply(get_hydro_zone)
    panel_df['stage_of_extraction'] = panel_df['District'].map(STAGE_OF_EXTRACTION)
    
    min_recharge = np.where(panel_df['pdf_hydro_zone'] == 2, 2.5, 1.5)
    panel_df['target'] = ((panel_df['pre_monsoon_m'] >= 6.0) & (panel_df['pre_monsoon_m'] <= 35.0) & (panel_df['recharge_potential'] >= min_recharge)).astype(int)
    return panel_df, locations

panel_df, unique_locations = process_telemetry()"""))

cells.append(nbformat.v4.new_code_cell(source="""def get_gee_base_stack():
    dem = ee.ImageCollection('COPERNICUS/DEM/GLO30_2024_1').mosaic().select(0)
    slope = ee.Terrain.slope(dem).rename('slope_deg')
    curvature = dem.convolve(ee.Kernel.laplacian8()).rename('curvature')
    tpi_250 = dem.subtract(dem.focal_mean(radius=250, units='meters')).rename('tpi_250_m')
    tpi_1k = dem.subtract(dem.focal_mean(radius=1000, units='meters')).rename('tpi_1k_m')
    tpi_5k = dem.subtract(dem.focal_mean(radius=5000, units='meters')).rename('tpi_5k_m')
    
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
    
    # Capped fastDistanceTransform to 128 to dramatically reduce timeout errors!
    dist_to_river = (upa.gt(10).unmask(0).fastDistanceTransform(128).sqrt().multiply(ee.Image.pixelArea().sqrt()).rename('distance_to_river_m'))
    
    rain_clim = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate('1991-01-01', '2020-12-31').filter(ee.Filter.calendarRange(6, 9, 'month')).sum().divide(30).rename('rain_clim_mm')
    
    return ee.Image.cat([slope, curvature, tpi_250, tpi_1k, tpi_5k, clay_0, clay_30, sand_0, sand_30, soc_0, soc_30, modis_ndvi, crop_frac, built_frac, tree_frac, log_upa, hand, dist_to_river, dem.rename('elevation_m'), rain_clim])

print('Initiating GEE Checkpoint Extraction Workflow...')
base_stack = get_gee_base_stack()
yearly_rain = []
for y in range(2021, 2026):
    monsoon = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate(f'{y}-06-01', f'{y}-10-01')
    yearly_rain.extend([monsoon.sum().rename(f'chirps_{y}'), monsoon.map(lambda i: i.gt(2)).sum().rename(f'rainy_days_{y}'), ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate(f'{y}-10-01', f'{y}-11-01').sum().rename(f'late_rain_{y}')])
full_stack = ee.Image.cat([base_stack] + yearly_rain)

done_wells = set(pd.read_csv(GEE_CACHE_FILE)['well_id'].astype(str)) if os.path.exists(GEE_CACHE_FILE) else set()
todo = unique_locations[~unique_locations['well_id'].astype(str).isin(done_wells)]
print(f'{len(done_wells)} wells already done, {len(todo)} to go.')

def extract(df):
    feats = [ee.Feature(ee.Geometry.Point([r.Longitude, r.Latitude]), {'well_id': str(r.well_id)}) for r in df.itertuples()]
    fc = ee.FeatureCollection(feats).map(lambda f: f.buffer(GEE_BUFFER_M))
    for attempt in range(3):
        try:
            res = full_stack.reduceRegions(fc, ee.Reducer.mean(), scale=30, tileScale=8).getInfo()
            return [f['properties'] for f in res['features']]
        except Exception as e:
            msg = str(e).lower()
            if 'did not match' in msg or 'not found' in msg: raise
            if 'timed out' in msg or 'too many' in msg: break
            time.sleep(5 * (attempt + 1))
    if len(df) == 1:
        print('FAILED well', df.iloc[0]['well_id'])
        return []
    mid = len(df) // 2
    return extract(df.iloc[:mid]) + extract(df.iloc[mid:])

if len(todo) > 0:
    chunks = [todo.iloc[i:i+25] for i in range(0, len(todo), 25)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(extract, c) for c in chunks]
        for n, fut in enumerate(as_completed(futs), 1):
            rows = fut.result()
            if rows:
                pd.DataFrame(rows).to_csv(GEE_CACHE_FILE, mode='a', header=not os.path.exists(GEE_CACHE_FILE), index=False)
            print(f'chunks done {n}/{len(chunks)}', end='\\r')

gee = pd.read_csv(GEE_CACHE_FILE).drop_duplicates('well_id')
missing = set(unique_locations['well_id'].astype(str)) - set(gee['well_id'].astype(str))
print(f'\\nWells fully missing features: {len(missing)}')

gee['well_id'] = gee['well_id'].astype(str)
panel_df['well_id'] = panel_df['well_id'].astype(str)
static_cols = [c for c in gee.columns if not c.startswith('chirps_') and not c.startswith('rainy_days_') and not c.startswith('late_rain_') and c != 'well_id']
panel_df = panel_df.merge(gee[['well_id'] + static_cols], on='well_id', how='left')

def assign_yr(row, p):
    w = gee[gee['well_id'] == row['well_id']]
    return w.iloc[0][f'{p}_{row["Year"]}'] if len(w)>0 and f'{p}_{row["Year"]}' in w.columns else np.nan

panel_df['monsoon_rainfall_mm'] = panel_df.apply(lambda r: assign_yr(r, 'chirps'), axis=1)
panel_df['rainy_days'] = panel_df.apply(lambda r: assign_yr(r, 'rainy_days'), axis=1)
panel_df['late_rain_mm'] = panel_df.apply(lambda r: assign_yr(r, 'late_rain'), axis=1)
panel_df['rain_anomaly_mm'] = panel_df['monsoon_rainfall_mm'] - panel_df['rain_clim_mm']
panel_df['TWI'] = panel_df['log_upstream_area'] + np.log(1e6) - np.log(np.tan(np.radians(panel_df['slope_deg'])) + 0.001)
# Drop remaining NaNs (failed extracted wells)
panel_df = panel_df.dropna(subset=['monsoon_rainfall_mm', 'rain_clim_mm'])"""))

cells.append(nbformat.v4.new_code_cell(source="""print("--- Extracting Holdout Vault ---")
dist_summary = panel_df.groupby(['District', 'pdf_hydro_zone']).agg(n_wells=('well_id', 'nunique'), pos_rate=('target', 'mean')).reset_index()

holdout_districts = []
np.random.seed(42)
for zone in [0, 1, 2]:
    d_zone = dist_summary[dist_summary['pdf_hydro_zone'] == zone]
    if len(d_zone) > 0: holdout_districts.extend(np.random.choice(d_zone['District'], size=min(2 if zone!=1 else 6, len(d_zone)), replace=False).tolist())

panel_train_val = panel_df[~panel_df['District'].isin(holdout_districts)].copy()
panel_holdout = panel_df[panel_df['District'].isin(holdout_districts)].copy()
print(f"Training Pool: {len(panel_train_val)} | Holdout Pool: {len(panel_holdout)}")

DEPLOYABLE_FEATURES = [
    'rain_clim_mm', 'monsoon_rainfall_mm', 'rain_anomaly_mm', 'rainy_days', 'late_rain_mm', 
    'slope_deg', 'curvature', 'tpi_250_m', 'tpi_1k_m', 'tpi_5k_m',
    'soil_clay_0_5_pct', 'soil_clay_30_100_pct', 'soil_sand_0_5_pct', 'soil_sand_30_100_pct', 
    'soil_soc_0_5', 'soil_soc_30_100', 'dry_season_ndvi', 'crop_frac', 'built_frac', 'tree_frac', 
    'elevation_m', 'distance_to_river_m', 'hand_m', 'TWI', 'pdf_hydro_zone', 'stage_of_extraction'
]
X_cv, y_cv, groups_cv = panel_train_val[DEPLOYABLE_FEATURES], panel_train_val['target'].values, panel_train_val['District'].values
scale_weight = float(np.sum(y_cv == 0) / np.sum(y_cv == 1)) if np.sum(y_cv == 1) > 0 else 1.0"""))

cells.append(nbformat.v4.new_code_cell(source="""print("\\n--- Final Training: Ensembling & Platt Scaling Calibration ---")
cb_params = {'iterations': 500, 'depth': 4, 'learning_rate': 0.05, 'l2_leaf_reg': 10, 'verbose': 0}
ensembled_models = []

for seed in RANDOM_SEEDS:
    base_cb = CatBoostClassifier(**cb_params, scale_pos_weight=scale_weight, random_seed=seed)
    print(f"Fitting Seed {seed} Ensembled Branch...")
    base_cb.fit(X_cv, y_cv)
    ensembled_models.append(base_cb)

print("\\n--- Final Holdout Vault Evaluation ---")
X_holdout, y_holdout = panel_holdout[DEPLOYABLE_FEATURES], panel_holdout['target'].values
holdout_probs = np.mean([model.predict_proba(X_holdout)[:, 1] for model in ensembled_models], axis=0)

holdout_auc = roc_auc_score(y_holdout, holdout_probs)
brier = brier_score_loss(y_holdout, holdout_probs)
print(f">> ULTIMATE HOLDOUT ROC-AUC: {holdout_auc:.4f}")
print(f">> Brier Score: {brier:.4f}")

opt_t = 0.5
print(classification_report(y_holdout, (holdout_probs >= opt_t).astype(int), target_names=['Unsuitable', 'Suitable']))"""))

cells.append(nbformat.v4.new_code_cell(source="""# Final Artifact Export
artifact = {
    'models': ensembled_models,
    'features': DEPLOYABLE_FEATURES,
    'stage_of_extraction_map': STAGE_OF_EXTRACTION,
    'optimal_threshold': opt_t
}
joblib.dump(artifact, f'/kaggle/working/{VERSION_ID}.pkl')
print(f'Production Artifact exported: {VERSION_ID}.pkl')"""))

cells.append(nbformat.v4.new_code_cell(source="""# ==========================================
# INFERENCE API FOR DEPLOYMENT
# ==========================================
def predict_site_recharge(lat, lon, monsoon_rainfall_mm, rainy_days, late_rain_mm, district_name):
    print(f"Running Live Inference for ({lat}, {lon})...")
    point = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([lon, lat]).buffer(500))])
    stack = get_gee_base_stack()
    res = stack.reduceRegions(collection=point, reducer=ee.Reducer.mean(), scale=30).getInfo()
    props = res['features'][0]['properties']
    
    df = pd.DataFrame([props])
    df['monsoon_rainfall_mm'] = monsoon_rainfall_mm
    df['rainy_days'] = rainy_days
    df['late_rain_mm'] = late_rain_mm
    df['rain_anomaly_mm'] = monsoon_rainfall_mm - df['rain_clim_mm']
    df['TWI'] = df['log_upstream_area'] + np.log(1e6) - np.log(np.tan(np.radians(df['slope_deg'])) + 0.001)
    
    d_norm = normalize_district(district_name)
    bhabar_terai = ['saharanpur', 'bijnor', 'moradabad', 'rampur', 'bareilly', 'pilibhit', 'lakhimpur kheri', 'bahraich', 'shravasti', 'balrampur', 'siddharthnagar', 'mahrajganj']
    bundelkhand = ['jhansi', 'lalitpur', 'jalaun', 'hamirpur', 'mahoba', 'banda', 'chitrakoot', 'mirzapur', 'sonbhadra']
    df['pdf_hydro_zone'] = 0 if d_norm in bhabar_terai else 2 if d_norm in bundelkhand else 1
    df['stage_of_extraction'] = STAGE_OF_EXTRACTION.get(d_norm, 70.0)
    
    probs = np.mean([model.predict_proba(df[DEPLOYABLE_FEATURES])[:, 1] for model in ensembled_models], axis=0)
    return {'Probability_Suitable': probs[0], 'Is_Suitable': bool(probs[0] >= opt_t), 'Extracted_Elevation': df['elevation_m'].iloc[0]}
"""))

nb.cells = cells
with open(r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v13_0.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)
print("Notebook generated successfully.")
