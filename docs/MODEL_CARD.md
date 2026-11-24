# Triage15 skill classifier model card

Version: `20261124T070322Z`. Trained: 2026-11-24T07:03:26.695036+00:00. Selected model: **linear_svm**.
Intended use: optional technical skill suggestions for students to confirm, correct, or ignore.
Out of scope: mentor expertise, student ability, qualification, grades, mentoring success, or automatic unconfirmed allocation.

## Data and configuration

Stack Exchange API; 2675 usable real questions. Train/validation/test: {'train': 1872, 'validation': 399, 'test': 404}. See [dataset card](../data/DATASET_CARD.md) and [attribution](../data/ATTRIBUTION.json).
Training-only TF-IDF; word 1-2 grams; technical token pattern; min_df=2; max_df=.98; max_features=30000; sublinear_tf; 30000 fitted features. Sparse One-vs-Rest classifiers, seed 42. NB alpha=.5; LR C=1, max_iter=1000; LinearSVC C=1. No hyperparameter grid search. Per-label validation F1 selects thresholds over .10:.05:.80 for probabilistic models or -1:.1:1 for SVM; ties prefer higher thresholds. The keyword dictionary was predefined before viewing test results.

## Validation comparison

| Model | Micro F1 | Macro F1 | Precision | Recall | P@3 | Training s | Median scoring ms | Compressed bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| keyword | 0.7052 | 0.6923 | 0.6053 | 0.8446 | 0.4194 | 0.000 | 4.687 | 0 |
| naive_bayes | 0.7660 | 0.5235 | 0.8675 | 0.6858 | 0.4553 | 6.012 | 12.061 | 5267389 |
| logistic_regression | 0.8803 | 0.8530 | 0.8392 | 0.9257 | 0.4820 | 7.508 | 6.025 | 2114950 |
| linear_svm | 0.9078 | 0.8932 | 0.8711 | 0.9476 | 0.4912 | 6.322 | 5.837 | 1945048 |


Selection: Best validation micro F1; Logistic Regression fell more than 0.02 behind. Mathematical explanations use selected model parameters. Best measured validation candidate: linear_svm. The 0.02 tolerance was specified in training code before the test evaluation. SVM's advantage over LR is measured on one validation split, not a significance claim.
Timings are local CPU wall-clock measurements. Training includes shared TF-IDF fit time. Scoring latency is median over the first up to 100 validation inputs, including transform and classifier scoring, excluding HTTP and explanations. Model sizes include vectorizer, classifier, encoder, thresholds; keyword baseline has no serialized model (0 bytes does not mean zero code footprint).

## Final held-out test

Micro precision 0.8336; recall 0.9176; F1 **0.8736**. Macro F1 **0.8396**; samples F1 0.8665; Hamming loss 0.0489; exact-match accuracy 0.6906; Precision@3 0.4827.
Coverage 0.9802; 8 abstentions. Covered-only micro F1 0.8799. Main metrics include abstentions as all-zero predictions. Reports also include default-threshold results with no feature-count gate. P@3 is an unthresholded ranking metric, often limited by questions having fewer than three relevant labels.

| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| aggregation | 0.6667 | 0.7083 | 0.6869 | 48 |
| async | 0.8000 | 0.8571 | 0.8276 | 14 |
| javascript | 0.7456 | 0.9043 | 0.8173 | 94 |
| joins | 0.5152 | 0.9444 | 0.6667 | 36 |
| pandas | 0.9104 | 0.9385 | 0.9242 | 65 |
| python | 0.9412 | 0.9552 | 0.9481 | 134 |
| react | 0.8406 | 0.9355 | 0.8855 | 62 |
| sql | 0.9781 | 0.9437 | 0.9606 | 142 |


No weak labels were hidden or test questions removed. Joins and aggregation are weaker than broad language labels. Test results are final measurements, not a tuning objective.

## Explainability and oversight

SVM: decision margin = intercept + sum(TF-IDF value * learned coefficient). Positive contributions increase a margin; negative ones decrease it. API returns six strongest present features of each sign plus omitted contribution, so displayed values reconstruct the complete score. SVM margins are not probabilities. LR alternatives use the same additive logit and sigmoid; NB uses log-prior odds plus TF-IDF weighted log-likelihood ratios. Neither NB nor LR was calibrated; validation Brier scores are in reports.
Global feature weights are associations, not causal evidence. Fewer than two known sparse features or no threshold-qualified labels causes abstention. These simple checks do not reliably detect every unsupported domain.
Only explicit accepted/manual tags enter the existing doubt API. Human edits remain authoritative; the predictor neither creates doubts nor dispatches mentors.

## Deployment and risks

Artifact: `ml/artifacts/skill_classifier.joblib`, 1945076 bytes. SHA-256: `4811b35cc0afa57e0a03bcb77670865b02696ab64377df4db15084990a3327a2`.
Versions: `{'scikit-learn': '1.9.0', 'joblib': '1.5.3', 'numpy': '2.5.5', 'scipy': '1.18.1', 'iterative-stratification': '0.1.9'}`. Python >=3.12 runtime; trained with 3.14.5. No GPU, external inference API, dataset download, or training at server startup. Load once, verify checksum and dependency versions, then infer offline. `ML_ENABLED=false`, missing dependencies, missing/corrupt artifacts, or incompatibility produce explicit unavailable status and preserve manual workflow.
Joblib is executable serialization: use only the repository's controlled training output. A checksum detects corruption; it does not authenticate an attacker-controlled artifact plus metadata.
Known limitations: Stack Overflow differs from student doubts. Only eight technical skills targeted; unsupported tags omitted. Probability estimates are uncalibrated, not verified correctness. Feature weights are associations, not causes. Simple feature-count abstention cannot reliably detect all out-of-domain inputs. Tag-specific recent sampling is not representative of all Stack Overflow. Approximate near-duplicate detection may miss paraphrases. No evidence of improved learning or mentoring success. No calibration, subgroup fairness study, temporal holdout, campus pilot, or learning-outcome validation was performed.
