import nbformat

nb_path = r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v8_0.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

# Find the last cell and update its source
last_cell = nb.cells[-1]

new_code = """# Train final model on 100% of data. Exclude marginal wells from training set.
tr_mask = ~panel_df['is_marginal'].values
prod_model = CatBoostClassifier(iterations=best_params['n'], depth=best_params['depth'], 
                                learning_rate=best_params['lr'], l2_leaf_reg=best_params['l2'], 
                                scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
prod_model.fit(X.iloc[tr_mask], y[tr_mask])

# Evaluate final production model on the entire dataset
prod_preds_proba = prod_model.predict_proba(X)[:, 1]
# Use the same optimal threshold found during CV
prod_classes = (prod_preds_proba >= opt_t).astype(int)

prod_roc = roc_auc_score(y, prod_preds_proba)
prod_acc = accuracy_score(y, prod_classes)
prod_prec = precision_score(y, prod_classes)
prod_rec = recall_score(y, prod_classes)
prod_f1 = f1_score(y, prod_classes)

print("\\n============================================================")
print("  FINAL PRODUCTION MODEL METRICS (Evaluated on 100% Data)")
print("============================================================")
print(f"  ROC-AUC:   {prod_roc:.4f}")
print(f"  Accuracy:  {prod_acc:.4f}")
print(f"  Precision: {prod_prec:.4f}")
print(f"  Recall:    {prod_rec:.4f}")
print(f"  F1 Score:  {prod_f1:.4f}")
print("============================================================\\n")

model_path = f'/kaggle/working/{VERSION_ID}.pkl'
artifact = {
    'model': prod_model,
    'features': FEATURE_COLS
}
joblib.dump(artifact, model_path)
print(f'Production Artifact exported: {VERSION_ID}.pkl')
"""

last_cell.source = new_code

with open(nb_path, 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Metrics block successfully added to final cell.")
