# ML judge questions and answers

## 1. Why does Triage15 require machine learning?

It does not require ML to operate; suggestions reduce manual tag discovery.

Technical detail: The classifier is an optional read-only stage. Manual selection remains available even if model loading fails.

Source: `ml/predictor.py::SkillPredictor.status; frontend/src/components/SkillSuggestions.tsx`.

## 2. What exactly is the model predicting?

Relevant supported technical skill tags.

Technical detail: It predicts eight binary labels from title/body text, not success, expertise, urgency, or mentor identity.

Source: `ml/config.py::LABEL_DOMAINS; ml/predictor.py::predict`.

## 3. Why did you choose Stack Overflow data?

It supplies real technical questions with human tags.

Technical detail: The official API returned labeled text and attribution metadata; source tags are mapped to the existing app taxonomy. Kaggle was attempted but its client was unavailable then.

Source: `scripts/download_dataset.py::acquire; ml/preprocess.py::normalize_tags`.

## 4. Is Stack Overflow representative of college students?

No; this is a useful starting dataset with domain shift.

Technical detail: Recent tag-specific samples differ in language, difficulty, and context from campus doubts. No campus validation was performed.

Source: `data/DATASET_CARD.md`.

## 5. Why did you choose supervised learning?

Existing tags provide examples of desired outputs.

Technical detail: Each text has a multi-hot target vector, so models learn parameters from observed labeled examples.

Source: `ml/train.py::train`.

## 6. Why is this a multi-label classification problem?

One question can involve Python and pandas, or SQL and joins.

Technical detail: Independent binary One-vs-Rest outputs permit multiple positives or abstention. A softmax single-class formulation would incorrectly force exclusivity.

Source: `ml/train.py::train`.

## 7. What is TF-IDF?

It weights informative words and phrases rather than treating all words equally.

Technical detail: Sublinear term frequency times smoothed inverse document frequency, then L2 normalization; word unigrams/bigrams and vocabulary/document frequency fit only on training.

Source: `ml/train.py::train; ml/config.py::TOKEN_PATTERN`.

## 8. What is One-vs-Rest classification?

One yes/no classifier per skill.

Technical detail: Eight binary estimators share sparse text features; outputs are thresholded independently and need not sum to one.

Source: `ml/train.py::train`.

## 9. How does Logistic Regression work mathematically?

It adds weighted text evidence, then applies a sigmoid.

Technical detail: z=b+sum(x_i*w_i); p=1/(1+exp(-z)). Parameters minimize regularized logistic loss. LR was a candidate, not the deployed winner.

Source: `ml/explain.py::explain_label; ml/train.py::train`.

## 10. Why not use BERT?

The CPU-only demo benefits from a small, directly explainable linear model.

Technical detail: Transformer training/inference adds compute and deployment work. BERT was not evaluated, so we make no comparative accuracy claim.

Source: `docs/MODEL_CARD.md`.

## 11. Why not use an LLM API?

Offline inference and no external AI calls are explicit requirements.

Technical detail: A saved local sparse classifier avoids runtime network dependencies and supports exact additive attribution.

Source: `ml/predictor.py::predict`.

## 12. Why compare Naive Bayes, Logistic Regression and SVM?

They are fast, distinct text-classification baselines.

Technical detail: NB uses smoothed likelihood ratios, LR uses logistic loss, and SVM uses separating margins. Identical data/features make the validation comparison interpretable.

Source: `ml/train.py::train`.

## 13. Which model actually performed best?

Linear SVM: validation micro F1 0.9078; LR 0.8803; NB 0.7660; keyword 0.7052.

Technical detail: The predefined LR preference applied only within .02 of best ML micro F1. SVM exceeded that gap and its final test micro F1 was 0.8736.

Source: `ml/reports/validation_results.json; ml/reports/test_results.json`.

## 14. What is the difference between precision and recall?

Precision measures how often suggested tags are right; recall measures how many true tags are found.

Technical detail: Precision=TP/(TP+FP); recall=TP/(TP+FN). Abstaining reduces false positives but can miss true labels.

Source: `ml/evaluate.py::metrics`.

## 15. Why report micro and macro F1?

Micro measures pooled quality; macro prevents common labels from hiding weak ones.

Technical detail: Micro pools TP/FP/FN, while macro averages label F1 equally. Test joins F1 is .6667, despite overall micro F1 .8736.

Source: `ml/reports/per_label_metrics.csv`.

## 16. What is data leakage?

Information from evaluation data improperly influences fitting or selection.

Technical detail: Examples include fitting IDF on all records, using tags in text, or tuning thresholds on test labels.

Source: `ml/train.py::train`.

## 17. How did you prevent data leakage?

Deduplicate first, save splits, fit text features on training only.

Technical detail: The pipeline excludes answers/tags/metadata from inputs, uses approximate near-duplicate removal, and fixes model/thresholds before opening test records. Approximate dedup may still miss paraphrases.

Source: `ml/preprocess.py::deduplicate; ml/train.py::train`.

## 18. Why separate training, validation and test data?

Fit on training, choose on validation, estimate final performance on test.

Technical detail: Counts are 1872, 399, 404, from iterative multi-label stratification with seed 42. No final refit changes the selected artifact.

Source: `ml/artifacts/split_ids.json; ml/train.py::train`.

## 19. How do you explain an individual prediction?

Show the actual words pushing the score up and down.

Technical detail: For each present TF-IDF feature, multiply by the fitted coefficient. Intercept + displayed positive/negative contributions + omitted contribution reconstructs the score.

Source: `ml/explain.py::explain_label`.

## 20. What do positive and negative feature contributions mean?

They push this label score higher or lower.

Technical detail: Signs are relative to a particular fitted binary classifier. They are predictive associations, not causal reasoning or proof of expertise.

Source: `ml/explain.py::parameters; ml/reports/feature_importance.json`.

## 21. Are probability estimates calibrated?

No. The deployed SVM does not emit probabilities at all.

Technical detail: LR/NB candidate probabilities have validation Brier measurements but no calibration fit. SVM outputs raw margins and probability=null.

Source: `ml/evaluate.py::metrics; ml/predictor.py::predict`.

## 22. What happens for unsupported skills?

Students select them manually.

Technical detail: The API can abstain for insufficient known features or thresholds, but cannot reliably detect every unsupported domain. CAD, Design and Mathematics remain in the existing domain form.

Source: `ml/predictor.py::predict; frontend/src/components/DoubtBoard.tsx`.

## 23. What happens if the prediction is wrong?

The student removes it, adds another tag, or ignores suggestions.

Technical detail: Suggestions never mutate selected tags until Accept is clicked; the existing doubt schema validates confirmed domain/tag compatibility.

Source: `frontend/src/components/SkillSuggestions.tsx; backend/app/schemas.py::DoubtInput`.

## 24. How does the ML classifier interact with Hungarian matching?

It assists tag selection before matching begins.

Technical detail: Only posted confirmed tags enter existing eligibility, utility scoring and dispatch. Predictions do not bypass availability, ownership or booking checks.

Source: `backend/app/ml_routes.py; backend/app/services.py::dispatch`.

## 25. Was the Hungarian algorithm trained on the dataset?

No; it is a deterministic optimization algorithm.

Technical detail: The dataset supplies real question text/tags to simulated workloads. Production weights and solver code were not modified.

Source: `ml/benchmark_real_workload.py::run_benchmark; backend/app/algorithms.py::maximum_weight`.

## 26. Does the dataset prove better mentorship outcomes?

No. It contains questions and tags, not campus learning outcomes.

Technical detail: Measured allocation utility is the existing heuristic objective, and profiles/schedules are simulated. Assignment counts are not academic effectiveness.

Source: `ml/reports/allocation_benchmark.json`.

## 27. How does the application work without internet?

Prediction uses the local saved model and SQLite.

Technical detail: Dataset requests and training are offline preparation steps only. The app makes no Kaggle/Stack Exchange/inference API call at startup or prediction time.

Source: `ml/predictor.py::load; Dockerfile`.

## 28. How would you retrain the model in production?

Acquire a new licensed snapshot, validate offline, and deploy a reviewed artifact.

Technical detail: Preserve attribution and splits; compare on a fresh held-out campus-relevant set; regenerate metadata/checksums; pin compatible dependencies and restart. No automatic retraining is implemented.

Source: `docs/ML_ARCHITECTURE.md; ml/train.py::train`.

## 29. How do you handle domain drift?

Currently with manual correction and explicit limitations.

Technical detail: No monitoring feedback collection or drift detector is implemented. A future consented labeled campus set and temporal evaluation should measure changes before retraining.

Source: `docs/MODEL_CARD.md`.

## 30. What are the actual limitations?

Small biased dataset, eight skills, noisy tags, and imperfect abstention.

Technical detail: Only 63 async training positives and 14 test positives; joins/aggregation are weaker. Approximate dedup, truncation, uncalibrated alternatives, and no campus pilot limit generalization.

Source: `data/DATASET_CARD.md; ml/reports/per_label_metrics.csv`.

## 31. What does the real allocation benchmark measure?

Thirty isolated scenarios: Hungarian persisted 235 assignments; greedy 200.

Technical detail: Identical initial states and first matrices; the existing eligibility, scores and final validation persist results. Both had zero invalid assignments and cross-role conflicts. Solver runtime is separated from full dispatch runtime.

Source: `ml/benchmark_real_workload.py::run_benchmark`.

## 32. What happens if the model artifact is missing or corrupted?

The app stays available with manual tags.

Technical detail: Loading catches missing files, checksum/version mismatches and import failures, marks unavailable, and logs only the error type. No untrusted upload/path is accepted.

Source: `ml/predictor.py::load; backend/tests/test_ml.py`.
