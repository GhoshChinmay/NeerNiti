import nbformat
import json

v6_path = r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v6_0.ipynb'
v7_path = r'c:\Projects\NeerNiti\notebooks\NeerNiti_UP_Model_Training_v7_0.ipynb'

with open(v6_path, 'r', encoding='utf-8') as f:
    nb_v6 = nbformat.read(f, as_version=4)

with open(v7_path, 'r', encoding='utf-8') as f:
    nb_v7 = nbformat.read(f, as_version=4)

# Fix the bug in v7
for cell in nb_v7.cells:
    if cell.cell_type == 'code':
        if "merit.select('visw')" in cell.source:
            cell.source = cell.source.replace("merit.select('visw')", "merit.select('viswth')")

# Find the imports cell in v7 and add xgboost and lightgbm
for cell in nb_v7.cells:
    if cell.cell_type == 'code' and "import pandas as pd" in cell.source:
        if "xgboost" not in cell.source:
            cell.source = cell.source.replace("from catboost import CatBoostClassifier", "import xgboost as xgb\nfrom lightgbm import LGBMClassifier\nfrom catboost import CatBoostClassifier\nfrom sklearn.ensemble import VotingClassifier")

# Now, let's update the Optuna cell to use Voting Ensemble like v6
optuna_cell_index = -1
for i, cell in enumerate(nb_v7.cells):
    if cell.cell_type == 'code' and "def objective(trial):" in cell.source:
        optuna_cell_index = i
        break

if optuna_cell_index != -1:
    new_optuna_source = """print("--- Leak-Free Voting Ensemble with Optuna (Nested Spatial Evaluation) ---")
def objective(trial):
    depth = trial.suggest_int('depth', 3, 7)
    lr = trial.suggest_float('lr', 0.01, 0.1, log=True)
    
    auc_scores = []
    # Evaluate strictly on spatial purged folds
    for train_idx, val_idx in custom_cv_folds:
        inner_split = int(len(train_idx) * 0.8)
        inner_tr, inner_val = train_idx[:inner_split], train_idx[inner_split:]
        
        xgb_c = xgb.XGBClassifier(n_estimators=100, max_depth=depth, learning_rate=lr, scale_pos_weight=scale_weight, random_state=RANDOM_SEED, verbosity=0)
        cat_c = CatBoostClassifier(iterations=100, depth=depth, learning_rate=lr, scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
        lgb_c = LGBMClassifier(n_estimators=100, max_depth=depth, learning_rate=lr, class_weight='balanced', random_state=RANDOM_SEED, verbose=-1)
        
        vote = VotingClassifier(estimators=[('xgb', xgb_c), ('cat', cat_c), ('lgb', lgb_c)], voting='soft')
        vote.fit(X.iloc[inner_tr], y[inner_tr])
        
        auc_scores.append(roc_auc_score(y[val_idx], vote.predict_proba(X.iloc[val_idx])[:, 1]))
    return np.mean(auc_scores)

study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=RANDOM_SEED))
print("Running Optuna Optimization...")
study.optimize(objective, n_trials=5)
best_params = study.best_params
print(f"Best Params Found: {best_params} (CV AUC: {study.best_value:.4f})")

def evaluate_folds(folds, name):
    preds = np.zeros(len(X))
    y_true = np.zeros(len(X))
    for train_idx, test_idx in folds:
        xgb_best = xgb.XGBClassifier(n_estimators=150, max_depth=best_params['depth'], learning_rate=best_params['lr'], scale_pos_weight=scale_weight, random_state=RANDOM_SEED, verbosity=0)
        cat_best = CatBoostClassifier(iterations=150, depth=best_params['depth'], learning_rate=best_params['lr'], scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
        lgb_best = LGBMClassifier(n_estimators=150, max_depth=best_params['depth'], learning_rate=best_params['lr'], class_weight='balanced', random_state=RANDOM_SEED, verbose=-1)
        
        vote_clf = VotingClassifier(estimators=[('xgb', xgb_best), ('cat', cat_best), ('lgb', lgb_best)], voting='soft')
        vote_clf.fit(X.iloc[train_idx], y[train_idx])
        
        preds[test_idx] = vote_clf.predict_proba(X.iloc[test_idx])[:, 1]
        y_true[test_idx] = y[test_idx]
    
    roc = roc_auc_score(y_true, preds)
    pr = average_precision_score(y_true, preds)
    print(f"{name} ROC-AUC: {roc:.4f} | PR-AUC: {pr:.4f}")
    return preds, y_true, vote_clf

print("\\nEvaluating 3.0km Haversine Spatial CV...")
spatial_preds, spatial_y, spatial_vote_clf = evaluate_folds(custom_cv_folds, "Spatial-CV")

print("\\nEvaluating Leave-District-Out CV (Robustness Check)...")
dist_preds, dist_y, _ = evaluate_folds(district_folds, "Leave-District-Out")

p, r, t = precision_recall_curve(spatial_y, spatial_preds)
target_t_idx = np.where(r >= 0.5)[0][-1]
opt_t = t[target_t_idx] if target_t_idx < len(t) else 0.5
final_classes = (spatial_preds >= opt_t).astype(int)

print(f"\\nClassification Report (Spatial CV, Threshold={opt_t:.3f} tuned for 50% Recall):")
print(classification_report(spatial_y, final_classes, target_names=['Unsuitable', 'Suitable']))
"""
    nb_v7.cells[optuna_cell_index].source = new_optuna_source

# Find the production training cell
prod_cell_index = -1
for i, cell in enumerate(nb_v7.cells):
    if cell.cell_type == 'code' and "prod_model =" in cell.source:
        prod_cell_index = i
        break

if prod_cell_index != -1:
    new_prod_source = """xgb_prod = xgb.XGBClassifier(n_estimators=200, max_depth=best_params['depth'], learning_rate=best_params['lr'], scale_pos_weight=scale_weight, random_state=RANDOM_SEED, verbosity=0)
cat_prod = CatBoostClassifier(iterations=200, depth=best_params['depth'], learning_rate=best_params['lr'], scale_pos_weight=scale_weight, random_seed=RANDOM_SEED, verbose=0)
lgb_prod = LGBMClassifier(n_estimators=200, max_depth=best_params['depth'], learning_rate=best_params['lr'], class_weight='balanced', random_state=RANDOM_SEED, verbose=-1)

prod_model = VotingClassifier(estimators=[('xgb', xgb_prod), ('cat', cat_prod), ('lgb', lgb_prod)], voting='soft')
prod_model.fit(X, y)

model_path = f'/kaggle/working/{VERSION_ID}.pkl'
joblib.dump(prod_model, model_path)
print(f'Production Artifact exported: {VERSION_ID}.pkl')
"""
    nb_v7.cells[prod_cell_index].source = new_prod_source

# Find plotting cell from v6
v6_plot_cell = None
for cell in nb_v6.cells:
    if cell.cell_type == 'code' and "fig, axes = plt.subplots(" in cell.source:
        v6_plot_cell = cell
        break

if v6_plot_cell:
    plot_source = v6_plot_cell.source
    plot_source = plot_source.replace("all_y_true", "spatial_y")
    plot_source = plot_source.replace("final_preds", "final_classes")
    plot_source = plot_source.replace("all_preds_proba", "spatial_preds")
    plot_source = plot_source.replace("vote_clf", "spatial_vote_clf")
    plot_source = plot_source.replace("X.iloc[test_idx]", "X")
    plot_source = plot_source.replace("y[test_idx]", "y")
    
    new_plot_cell = nbformat.v4.new_code_cell(source=plot_source)
    nb_v7.cells.insert(prod_cell_index, new_plot_cell)

with open(v7_path, 'w', encoding='utf-8') as f:
    nbformat.write(nb_v7, f)
    
print("Successfully merged notebooks and fixed visw bug.")
