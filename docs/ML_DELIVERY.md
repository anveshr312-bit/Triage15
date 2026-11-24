# Explainable ML delivery report

Implemented locally without committing or pushing. Recovery checkpoint: `.tmp/ml-checkpoint/` at Git `d048de3`. Existing Hungarian solver, scoring weights, SQLite, bounty/session/chat/scheduling logic and single-worker deployment architecture remain.

## Dataset

Actual source: official [Stack Exchange questions API](https://api.stackexchange.com/docs/questions), cached GET requests after Kaggle client unavailable. Downloaded 3123 unique real questions; usable 2675; train/validation/test {'train': 1872, 'validation': 399, 'test': 404}. Eight tags: aggregation, async, javascript, joins, pandas, python, react, sql. Source-license observations: {'CC BY-SA 4.0': 2267, 'see post timeline': 408}; attribution and license timeline references in `data/ATTRIBUTION.json` and `data/DATASET_CARD.md`. No raw dataset is tracked or deployed.

## Validation comparison (not test scores)

| Model | Micro F1 | Macro F1 | Precision | Recall | P@3 | Training s | Median scoring ms | Compressed bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| keyword | 0.7052 | 0.6923 | 0.6053 | 0.8446 | 0.4194 | 0.000 | 4.687 | 0 |
| naive_bayes | 0.7660 | 0.5235 | 0.8675 | 0.6858 | 0.4553 | 6.012 | 12.061 | 5267389 |
| logistic_regression | 0.8803 | 0.8530 | 0.8392 | 0.9257 | 0.4820 | 7.508 | 6.025 | 2114950 |
| linear_svm | 0.9078 | 0.8932 | 0.8711 | 0.9476 | 0.4912 | 6.322 | 5.837 | 1945048 |


Selected **linear_svm** because Best validation micro F1; Logistic Regression fell more than 0.02 behind. Mathematical explanations use selected model parameters.
Final test: micro F1 0.8736; macro F1 0.8396; precision 0.8336; recall 0.9176; coverage 0.9802; 8 abstentions. Weak labels and all per-label metrics are retained in the model card.
Candidate latency is transform+score on validation examples; complete predictor measurement (cleaning, transform, scoring, explanations, no HTTP): `{'measurement': 'Warm local predictor including cleaning, transform, scoring and explanations; illustrative inputs; excludes HTTP', 'median_ms': 71.8352500000492, 'p95_ms': 91.70670000003156, 'calls': 100}`. Timings are local CPU observations, not production guarantees.
The selected SVM computes z=b+sum(x_i*w_i), with TF-IDF x and learned w. Explanations display signed feature products and omitted contribution to reconstruct z. Margins are not probabilities. Its output does not determine mentor expertise or mentoring success.

## Allocation

30 seeded scenarios with real text/tags and simulated people/schedules. Shared-matrix total utility: Hungarian 17521.0394, greedy 14901.9776. Integrated utility: 16874.5787 vs 14641.7780; persisted assignments 235 vs 200. Both have zero invalid assignments and cross-role booking conflicts. Greedy is faster; Hungarian does not necessarily improve every per-scenario metric. Utility is not a learning outcome.

## Integration and deployment

- POST `/api/ml/predict-tags`; GET `/api/ml/status`, `/api/ml/metrics`, `/api/ml/model-info`.
- `SkillSuggestions.tsx`: explicit request, exact contributions, accept/remove/ignore; existing checkbox controls allow manual additions. `ModelEvaluation.tsx`: saved results and benchmark.
- `DoubtBoard.tsx` submits confirmed skills to the unchanged existing doubt API. Inference has no database writes.
- Artifact `ml/artifacts/skill_classifier.joblib` (1945076 bytes), metadata, label mapping, saved split IDs; SHA-256 in metadata.
- Runtime adds pinned scikit-learn 1.9.0, joblib 1.5.3, NumPy 2.5.5 and SciPy 1.18.1. Optional training adds kagglehub 1.0.3 and iterative-stratification 0.1.9.
- Docker copies `ml/` and adds root to PYTHONPATH, preserving database mount and worker configuration. No dataset downloads/training at startup. `ML_ENABLED=false` or unavailable artifacts retain manual operation.

## Verification

Baseline: 56 tests passed. Final suite: 94 passed, 0 failed (38 new ML tests). TypeScript and Vite production build passed. Actual browser confirmed suggestion, acceptance, rejection, manual addition, numerical explanations, persisted exact tags and successful matching, plus evaluation display. Details and warnings: [ML_VERIFICATION.md](ML_VERIFICATION.md).
Docker image build and Railway deployment were not executed (Docker unavailable). No Git push. Campus outcomes, calibration fitting and fairness/drift studies were not performed.

## Added files

- `backend/app/ml_routes.py`
- `backend/tests/test_ml.py`
- `data/ATTRIBUTION.json`
- `data/DATASET_CARD.md`
- `docs/ML_15_MINUTE_GUIDE.md`
- `docs/ML_ARCHITECTURE.md`
- `docs/ML_DELIVERY.md`
- `docs/ML_JUDGE_QA.md`
- `docs/ML_VERIFICATION.md`
- `docs/MODEL_CARD.md`
- `docs/ml-test-results.xml`
- `frontend/src/components/ModelEvaluation.tsx`
- `frontend/src/components/SkillSuggestions.tsx`
- `ml/__init__.py`
- `ml/artifacts/label_mapping.json`
- `ml/artifacts/model_metadata.json`
- `ml/artifacts/skill_classifier.joblib`
- `ml/artifacts/split_ids.json`
- `ml/benchmark_real_workload.py`
- `ml/config.py`
- `ml/evaluate.py`
- `ml/explain.py`
- `ml/predictor.py`
- `ml/preprocess.py`
- `ml/reports/allocation_benchmark.json`
- `ml/reports/error_analysis.md`
- `ml/reports/feature_importance.json`
- `ml/reports/inference_latency.json`
- `ml/reports/model_comparison.csv`
- `ml/reports/model_explanations.md`
- `ml/reports/per_label_metrics.csv`
- `ml/reports/test_results.json`
- `ml/reports/validation_results.json`
- `ml/requirements-training.txt`
- `ml/train.py`
- `scripts/download_dataset.py`
- `scripts/measure_ml_latency.py`
- `scripts/write_ml_docs.py`

## Modified files

- `.env.example`
- `.gitignore`
- `Dockerfile`
- `README.md`
- `backend/app/main.py`
- `backend/pytest.ini`
- `backend/requirements-lock.txt`
- `backend/requirements.txt`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/LIMITATIONS.md`
- `frontend/src/App.tsx`
- `frontend/src/components/DoubtBoard.tsx`

## Learn in fifteen minutes

Follow [ML_15_MINUTE_GUIDE.md](ML_15_MINUTE_GUIDE.md): dataset (2 min), supervised targets (1), TF-IDF (2), multi-label LR/SVM (2), contributions (2), metrics (2), human confirmation/Hungarian (2), limitations/fallback (2). [ML_JUDGE_QA.md](ML_JUDGE_QA.md) contains 32 source-referenced technical answers. [ML_ARCHITECTURE.md](ML_ARCHITECTURE.md) gives exact reproduction commands.
