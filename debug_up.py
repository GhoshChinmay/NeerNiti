import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from sklearn.model_selection import KFold
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import BallTree
import json

RANDOM_SEED = 42

print("Loading data...")
# Recreate dataset from cache
# (Since the notebook creates dataset in memory, we need to quickly re-run the aggregation step to get 'target' and merge with cache)

def process_telemetry():
    tel1 = pd.read_csv('/kaggle/input/datasets/chinmay302/neerniti/gwl_tel_6_hourly_upgw_up_2021_2025.csv', low_memory=False)
    tel2 = pd.read_csv('/kaggle/input/datasets/chinmay302/neerniti/gwl_tel_6_hourly_upgw_up_2026_2030.csv', low_memory=False)
    
    combined = pd.concat([tel1, tel2], ignore_index=True)
    combined['Date'] = pd.to_datetime(combined['Data Acquisition Time'], errors='coerce', format='mixed', dayfirst=True)
    combined = combined.dropna(subset=['Date'])
    combined['Month'] = combined['Date'].dt.month
    combined['Year'] = combined['Date'].dt.year
    lvl_col = [c for c in combined.columns if 'meter' in c.lower()][0]
    combined[lvl_col] = pd.to_numeric(combined[lvl_col], errors='coerce').abs()
    
    pre = combined[combined['Month'].isin([4, 5])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
    pre.rename(columns={lvl_col: 'pre_monsoon_m'}, inplace=True)
    post = combined[combined['Month'].isin([10, 11])].groupby(['Latitude', 'Longitude', 'Year', 'District'])[lvl_col].mean().reset_index()
    post.rename(columns={lvl_col: 'post_monsoon_m'}, inplace=True)
    
    paired = pd.merge(pre, post, on=['Latitude', 'Longitude', 'Year', 'District'], how='inner')
    final_df = paired.groupby(['Latitude', 'Longitude']).agg({'pre_monsoon_m': 'mean', 'post_monsoon_m': 'mean', 'District': 'first'}).reset_index()
    
    final_df['recharge_potential'] = final_df['pre_monsoon_m'] - final_df['post_monsoon_m']
    final_df['target'] = ((final_df['pre_monsoon_m'] >= 6.0) & (final_df['pre_monsoon_m'] <= 35.0) & (final_df['recharge_potential'] >= 1.5)).astype(int)
    final_df['well_id'] = ['UP_WELL_' + str(i) for i in range(len(final_df))]
    final_df['spatial_block_id'] = (np.floor(final_df['Latitude'] / 0.25).astype(str) + '_' + np.floor(final_df['Longitude'] / 0.25).astype(str))
    
    bhabar_terai = ['saharanpur', 'bijnor', 'moradabad', 'rampur', 'bareilly', 'pilibhit', 'lakhimpur', 'kheri', 'bahraich', 'shravasti', 'balrampur', 'siddharthnagar', 'mahrajganj']
    bundelkhand_hard_rock = ['jhansi', 'lalitpur', 'jalaun', 'hamirpur', 'mahoba', 'banda', 'chitrakoot', 'mirzapur', 'sonbhadra']
    def get_hydro_zone(district):
        d = str(district).strip().lower()
        if d in bhabar_terai: return 0
        if d in bundelkhand_hard_rock: return 2
        return 1
    final_df['pdf_hydro_zone'] = final_df['District'].apply(get_hydro_zone)
    return final_df

dataset = process_telemetry()
gee_features = pd.read_csv('c:/Projects/NeerNiti/up_gee_cache.csv') if os.path.exists('c:/Projects/NeerNiti/up_gee_cache.csv') else None
# Wait, the cache is on kaggle. I can't read it here!
