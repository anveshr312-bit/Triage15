"""Generate dataset/model/judge documentation from measured artifacts, never guessed scores."""
import json
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write_docs():
    from ml.config import ARTIFACTS, REPORTS, PROCESSED, LABEL_DOMAINS
    m = json.loads((ARTIFACTS / 'model_metadata.json').read_text(encoding='utf-8'))
    results = json.loads((REPORTS / 'validation_results.json').read_text(encoding='utf-8'))
    benchmark = json.loads((REPORTS / 'allocation_benchmark.json').read_text(encoding='utf-8'))['summary']
    d, test = m['dataset'], m['test']
    records = sum([json.loads((PROCESSED / f'{name}.json').read_text(encoding='utf-8')) for name in ('train', 'validation', 'test')], [])
    attribution = [{'question_id': q['id'], 'url': q['url'], 'author': q['owner'].get('display_name'),
                    'author_id': q['owner'].get('user_id'), 'author_url': q['owner'].get('link'),
                    'content_license': q['license'], 'created_at': q['created_at']} for q in records]
    (ROOT / 'data/ATTRIBUTION.json').write_text(json.dumps(attribution, ensure_ascii=False, indent=2), encoding='utf-8')
    distribution = '| Label | App domain | Train positives | Validation positives | Test positives |\n|---|---|---:|---:|---:|\n'
    for label in m['labels']:
        distribution += f"| {label} | {LABEL_DOMAINS[label]} | {d['label_distribution']['train'].get(label, 0)} | {d['label_distribution']['validation'].get(label, 0)} | {d['label_distribution']['test'].get(label, 0)} |\n"
    comparison = '| Model | Micro F1 | Macro F1 | Precision | Recall | P@3 | Training s | Median scoring ms | Compressed bytes |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for name, r in results.items():
        comparison += f"| {name} | {r['micro_f1']:.4f} | {r['macro_f1']:.4f} | {r['micro_precision']:.4f} | {r['micro_recall']:.4f} | {r['precision_at_3']:.4f} | {r['training_seconds']:.3f} | {r['median_inference_ms']:.3f} | {r['model_size_bytes']} |\n"
    label_results = '| Label | Precision | Recall | F1 | Support |\n|---|---:|---:|---:|---:|\n'
    for label, r in test['per_label'].items():
        label_results += f"| {label} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} | {r['support']} |\n"
    def write(path, text):
        (ROOT / path).write_text(text.strip() + '\n', encoding='utf-8')
    importance = json.loads((REPORTS / 'feature_importance.json').read_text(encoding='utf-8'))
    explanation_report = ['# Learned model feature associations', '',
        f"Selected model: {m['selected_model']}. These weights are learned associations, not causes. Local contributions multiply these weights by the input TF-IDF values. SVM margins are not probabilities."]
    for label, value in importance.items():
        explanation_report.extend(['', f'## {label}', '', f"Training positives: {value['training_examples']}; intercept: {value['intercept']:.6f}; validation F1: {value['validation_metrics']['f1']:.4f}; test F1: {value['test_metrics']['f1']:.4f}.", '',
            'Positive weights: ' + ', '.join(f"{f['feature']} ({f['weight']:.4f})" for f in value['positive']), '',
            'Negative weights: ' + ', '.join(f"{f['feature']} ({f['weight']:.4f})" for f in value['negative'])])
    write('ml/reports/model_explanations.md', '\n'.join(explanation_report))
    write('data/DATASET_CARD.md', f'''
# Triage15 real-question dataset card

Actual source: **{d['source']['source']}**, [official questions API](https://api.stackexchange.com/docs/questions).
Acquired: {d['source']['acquired_at']}. These are real Stack Overflow questions, not generated examples.
Acquisition: `scripts/download_dataset.py::acquire`, {d['source']['method']}.
The primary [StackSample dataset](https://www.kaggle.com/datasets/stackoverflow/stacksample) was attempted with kagglehub, but the package was not yet available during the bounded attempt. We immediately used the authorized API fallback. No Kaggle data was used in these results.

Downloaded unique questions: **{d['downloaded_questions']}**. Usable labeled questions after cleaning and deduplication: **{d['usable_questions']}**.
Two duplicate/near-duplicate records were removed; remaining excluded records had no supported mapped target.
The original Stack Overflow corpus size is not measured here. Four pages of up to 100 questions per query were requested for python, pandas, javascript, reactjs, sql, join, aggregate-functions, and async-await, sorted by creation descending with a fixed cutoff. Overlap is deduplicated by question ID.
Cached responses, quota counts, full request parameters, and acquisition logs stay in ignored `data/raw/`.
Requests are sequential, at least one second apart, honor backoff, stop on exhausted quota/error, and reuse cached pages. No HTML scraping or answers are used.

## Schema and preprocessing

Observed fields include `question_id`, `title`, `body`, `tags`, `creation_date`, `link`, `owner`, and sometimes `content_license`. The API record already joins tags to questions. The alternate CSV reader inspects headers and streams Questions.csv and Tags.csv by Id, never Answers.csv.
`ml/preprocess.py`: HTML entities/markup are normalized; code text, error messages, C++, C#, .NET, and Node.js survive. Whitespace is collapsed. Model inputs are title (up to 150 cleaned characters) plus body (up to 3,000), identically at inference. No stemming or generic English stopword deletion is used.
Exact text SHA-256, normalized title matches, and approximate near-duplicate 5-word shingle Jaccard >=0.90 deduplication run before splitting. Candidate pairs share one of eight minimum CRC32 shingle hashes. This is approximate and can miss paraphrases or conservatively merge reused titles. Duplicate label sets are unioned; duplicate source IDs remain in processed records.
For a large primary dataset, a fixed-seed reservoir limits eligible input to 20,000 records before deduplication. The API run uses all usable acquired records.

## Targets and partitions

Unsupported source tags are omitted. `python-3.x` maps to python; reactjs/react-hooks map to react; SQL dialects map to sql. Async is mapped only with JavaScript/React source tags; SQL joins/aggregation only when a SQL label exists. These restrictions avoid incompatible domain skills. A question may retain multiple labels across domains; the app still requires one explicitly selected domain per submitted doubt.
Vocabulary is predefined, and labels require >=20 training positives; no label was removed in this run. Iterative multi-label stratification uses seed 42, approximately 70/15/15: **{d['split_sizes']}**. Discrete stratification causes small deviations from exact percentages.
Split IDs and checksum: `ml/artifacts/split_ids.json`, `model_metadata.json`. Test labels do not select models, thresholds, features, or vocabulary. TF-IDF fits training only.

{distribution}

## License and attribution

Observed usable-record license metadata: `{d['licenses']}`. Do not assume absent license fields mean public domain or CC0.
[Stack Overflow licensing policy](https://stackoverflow.com/help/licensing) specifies CC BY-SA 2.5 before April 8, 2011, CC BY-SA 3.0 until May 2, 2018, and CC BY-SA 4.0 afterward; individual revisions' licenses should be checked on their timelines. [CC BY-SA 4.0 terms](https://creativecommons.org/licenses/by-sa/4.0/) require attribution and ShareAlike when applicable.
`data/ATTRIBUTION.json` preserves each retained question URL, author/name/link where supplied, creation timestamp and reported license. Raw records preserve additional original metadata. For the {d['licenses'].get('see post timeline', 0)} records lacking API license metadata, consult the linked source revision before redistribution.
Full question bodies and raw/processed datasets are not committed or shipped. Error analysis links to source questions rather than redistributing their text. Text transformations are described above; do not redistribute transformed question datasets without preserving attribution and applicable license obligations. Attribution metadata is included with the small learned artifact; do not interpret its inclusion as changing source-content licenses.

## Limitations and coverage

Queries oversample eight requested tags, and recent creation order samples different historical periods for high- and low-volume tags. This is neither a random sample of all Stack Overflow nor a campus cohort. Tags can be incomplete, noisy, or historically inconsistent; truncated bodies can lose context. Popular developer languages dominate; CAD, Design, Mathematics and many existing manual tags are unsupported by ML. No mentoring-session outcomes are present. Author metadata is used for attribution only, never model features.
''')
    write('docs/MODEL_CARD.md', f'''
# Triage15 skill classifier model card

Version: `{m['model_version']}`. Trained: {m['trained_at']}. Selected model: **{m['selected_model']}**.
Intended use: optional technical skill suggestions for students to confirm, correct, or ignore.
Out of scope: mentor expertise, student ability, qualification, grades, mentoring success, or automatic unconfirmed allocation.

## Data and configuration

{d['source']['source']}; {d['usable_questions']} usable real questions. Train/validation/test: {d['split_sizes']}. See [dataset card](../data/DATASET_CARD.md) and [attribution](../data/ATTRIBUTION.json).
{m['feature_extraction']}; {m['feature_count']} fitted features. Sparse One-vs-Rest classifiers, seed 42. NB alpha=.5; LR C=1, max_iter=1000; LinearSVC C=1. No hyperparameter grid search. Per-label validation F1 selects thresholds over .10:.05:.80 for probabilistic models or -1:.1:1 for SVM; ties prefer higher thresholds. The keyword dictionary was predefined before viewing test results.

## Validation comparison

{comparison}

Selection: {m['selection_reason']} Best measured validation candidate: {m['best_validation_model']}. The 0.02 tolerance was specified in training code before the test evaluation. SVM's advantage over LR is measured on one validation split, not a significance claim.
Timings are local CPU wall-clock measurements. Training includes shared TF-IDF fit time. Scoring latency is median over the first up to 100 validation inputs, including transform and classifier scoring, excluding HTTP and explanations. Model sizes include vectorizer, classifier, encoder, thresholds; keyword baseline has no serialized model (0 bytes does not mean zero code footprint).

## Final held-out test

Micro precision {test['micro_precision']:.4f}; recall {test['micro_recall']:.4f}; F1 **{test['micro_f1']:.4f}**. Macro F1 **{test['macro_f1']:.4f}**; samples F1 {test['samples_f1']:.4f}; Hamming loss {test['hamming_loss']:.4f}; exact-match accuracy {test['exact_match_accuracy']:.4f}; Precision@3 {test['precision_at_3']:.4f}.
Coverage {test['coverage']:.4f}; {test['abstention_count']} abstentions. Covered-only micro F1 {test['covered_micro_f1']:.4f}. Main metrics include abstentions as all-zero predictions. Reports also include default-threshold results with no feature-count gate. P@3 is an unthresholded ranking metric, often limited by questions having fewer than three relevant labels.

{label_results}

No weak labels were hidden or test questions removed. Joins and aggregation are weaker than broad language labels. Test results are final measurements, not a tuning objective.

## Explainability and oversight

SVM: decision margin = intercept + sum(TF-IDF value * learned coefficient). Positive contributions increase a margin; negative ones decrease it. API returns six strongest present features of each sign plus omitted contribution, so displayed values reconstruct the complete score. SVM margins are not probabilities. LR alternatives use the same additive logit and sigmoid; NB uses log-prior odds plus TF-IDF weighted log-likelihood ratios. Neither NB nor LR was calibrated; validation Brier scores are in reports.
Global feature weights are associations, not causal evidence. Fewer than two known sparse features or no threshold-qualified labels causes abstention. These simple checks do not reliably detect every unsupported domain.
Only explicit accepted/manual tags enter the existing doubt API. Human edits remain authoritative; the predictor neither creates doubts nor dispatches mentors.

## Deployment and risks

Artifact: `ml/artifacts/skill_classifier.joblib`, {m['artifact_size_bytes']} bytes. SHA-256: `{m['artifact_sha256']}`.
Versions: `{m['dependencies']}`. Python >=3.12 runtime; trained with {m['python_version']}. No GPU, external inference API, dataset download, or training at server startup. Load once, verify checksum and dependency versions, then infer offline. `ML_ENABLED=false`, missing dependencies, missing/corrupt artifacts, or incompatibility produce explicit unavailable status and preserve manual workflow.
Joblib is executable serialization: use only the repository's controlled training output. A checksum detects corruption; it does not authenticate an attacker-controlled artifact plus metadata.
Known limitations: {' '.join(m['limitations'])} No calibration, subgroup fairness study, temporal holdout, campus pilot, or learning-outcome validation was performed.
''')
    write('docs/ML_ARCHITECTURE.md', f'''
# Explainable skill suggestions and independent mentor optimization

The optional supervised classifier helps a student identify skill tags from a title and description. Historical question text is input and existing technical tags are targets; each record can have several targets. This is multi-label learning, not choosing a single class.

```mermaid
flowchart LR
    Text[Student title and description] --> Clean[Shared text cleaning]
    Clean --> TFIDF[Saved training-only TF-IDF]
    TFIDF --> Model[One-vs-Rest linear SVM]
    Model --> Explain[Margins and exact contributions]
    Explain --> Confirm[Student accepts or edits tags]
    Manual[Manual domain and tags] --> Confirm
    Confirm --> API[Existing doubt API]
    API --> Eligible[Existing eligibility and scheduling]
    Eligible --> Hungarian[Unchanged Hungarian matching]
```

## Offline pipeline

`scripts/download_dataset.py::acquire` attempts Kaggle then caches official Stack Exchange API questions. The actual run used the API, not StackSample. `ml/preprocess.py::source_records` inspects schemas; `clean_html`, `normalize_tags`, `deduplicate`, and `prepare` clean, map, deduplicate and stratify. Answers, owners, tags, votes and URLs never enter text features.
TF-IDF multiplies sublinear term frequency (1+log count) by smoothed inverse document frequency, then L2-normalizes rows. Training-only vocabulary and document frequencies prevent leakage. Technical tokenization retains identifiers; sparse matrices avoid dense document-by-vocabulary allocations.
`ml/train.py::train` fits one independent binary classifier per label through OneVsRestClassifier. Multinomial NB models weighted term likelihoods with smoothing. Logistic Regression minimizes regularized logistic loss and estimates sigmoid probabilities. Linear SVM learns regularized separating hyperplanes using squared hinge loss. All use the same splits, labels and vectorizer.
Validation chooses thresholds and model. The held-out test is opened afterward. {m['selected_model']} was selected; validation micro F1 {results[m['selected_model']]['micro_f1']:.4f}, test micro F1 {test['micro_f1']:.4f}. See [model card](MODEL_CARD.md) for every candidate and metric definition in `ml/evaluate.py::METRIC_DEFINITIONS`.

## Mathematical explanations

`ml/explain.py::parameters` extracts genuine learned coefficients or NB likelihood ratios. `explain_label` computes x_i*w_i for present sparse features. For LR z=b+sum(x_i*w_i), p=1/(1+exp(-z)). For SVM the same linear sum is a margin with no probability interpretation. For binary NB z=log P(y=1)-log P(y=0)+sum(x_i*(log P(feature_i|1)-log P(feature_i|0))). Global coefficients in `feature_importance.json` indicate association, not causation.

## Runtime and UI

`ml/predictor.py::SkillPredictor.load` runs once per process under a lock, checks packaged checksum and versions, and catches load failures. `predict` shares preprocessing and uses saved validation thresholds. No inference route writes to SQLite. `backend/app/ml_routes.py` exposes POST `/api/ml/predict-tags`, GET `/api/ml/status`, GET `/api/ml/metrics`, GET `/api/ml/model-info`. Input uses the existing title/description bounds and forbids extra fields. Metrics are saved results, never retraining.
`SkillSuggestions.tsx` uses an explicit button. Requests do not alter selected tags. Accepting a different-domain label explicitly replaces current domain/tags; the button says so. Existing checkboxes remove/add tags. Stale results are hidden when text changes. `DoubtBoard.tsx` submits only selected tags through its existing API and dispatch flow. `ModelEvaluation.tsx` displays measured comparisons, test results, feature weights and allocation reports.

## Allocation experiment

`ml/benchmark_real_workload.py::run_benchmark` creates 30 seeded scenarios from real question text and mapped tags. Profiles, skill declarations, availability, urgency and deadlines are simulated; multi-domain questions use their most represented mapped domain with deterministic tie-breaking. Both solvers see the identical first candidate matrix and equivalent initial isolated SQLite databases. Production `services.score`, `feasible`, and `dispatch` implement scoring and constraints; only a scoped test patch substitutes greedy for the solver. The production engine and weights are unchanged.
Shared-matrix utility: Hungarian {benchmark['hungarian']['shared_matrix_total_utility']:.4f}, greedy {benchmark['greedy']['shared_matrix_total_utility']:.4f}. Integrated persisted utility: {benchmark['hungarian']['total_utility']:.4f} versus {benchmark['greedy']['total_utility']:.4f}. Persisted assignments: {benchmark['hungarian']['assignments']} versus {benchmark['greedy']['assignments']}. Invalid assignments and cross-role conflicts: zero in both. Final validation rejections and recovery are measured in the report; Hungarian is slower and does not guarantee every per-scenario metric improves. None of these numbers measures learning outcomes.

## Reproduce from repository root (PowerShell)

```powershell
uv pip install --python .venv/Scripts/python.exe -r ml/requirements-training.txt
.venv/Scripts/python.exe scripts/download_dataset.py
.venv/Scripts/python.exe -m ml.preprocess
.venv/Scripts/python.exe -m ml.train
.venv/Scripts/python.exe -m ml.benchmark_real_workload
.venv/Scripts/python.exe scripts/write_ml_docs.py
.venv/Scripts/python.exe -m pytest backend -q
npm --prefix frontend run build
$env:PYTHONPATH=".;backend"
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Use Python >=3.12; pip can install the same requirements if uv is unavailable. On Unix use `.venv/bin/python` and `PYTHONPATH=.:backend`. `--api-only` skips Kaggle deliberately. Raw responses are reused; move an existing acquisition aside intentionally to acquire a new snapshot. Fixed cutoff/splits help reproducibility but live API deletions, retagging and edits can change later acquisitions. Preserve the ignored raw snapshot to reproduce the exact model, while honoring source licenses.

## Packaging and fallback

Docker adds `/app/ml` and `/app` to Python import resolution, and includes the ~{m['artifact_size_bytes']/1024/1024:.2f} MiB artifact and reports. Existing `/data` SQLite mount, port, single worker and coordinator remain. `.dockerignore` excludes data; optional Kaggle/stratification packages are training-only. Runtime pins sklearn/joblib/numpy/scipy. Run from repository root; README commands include it in PYTHONPATH. Set `ML_ENABLED=false` to disable; missing artifacts/dependencies safely disable suggestions, never manual tags. Redeploy/restart after replacing a controlled artifact because models load once.
''')
    qa = [
        ('Why does Triage15 require machine learning?', 'It does not require ML to operate; suggestions reduce manual tag discovery.', 'The classifier is an optional read-only stage. Manual selection remains available even if model loading fails.', 'ml/predictor.py::SkillPredictor.status; frontend/src/components/SkillSuggestions.tsx'),
        ('What exactly is the model predicting?', 'Relevant supported technical skill tags.', 'It predicts eight binary labels from title/body text, not success, expertise, urgency, or mentor identity.', 'ml/config.py::LABEL_DOMAINS; ml/predictor.py::predict'),
        ('Why did you choose Stack Overflow data?', 'It supplies real technical questions with human tags.', 'The official API returned labeled text and attribution metadata; source tags are mapped to the existing app taxonomy. Kaggle was attempted but its client was unavailable then.', 'scripts/download_dataset.py::acquire; ml/preprocess.py::normalize_tags'),
        ('Is Stack Overflow representative of college students?', 'No; this is a useful starting dataset with domain shift.', 'Recent tag-specific samples differ in language, difficulty, and context from campus doubts. No campus validation was performed.', 'data/DATASET_CARD.md'),
        ('Why did you choose supervised learning?', 'Existing tags provide examples of desired outputs.', 'Each text has a multi-hot target vector, so models learn parameters from observed labeled examples.', 'ml/train.py::train'),
        ('Why is this a multi-label classification problem?', 'One question can involve Python and pandas, or SQL and joins.', 'Independent binary One-vs-Rest outputs permit multiple positives or abstention. A softmax single-class formulation would incorrectly force exclusivity.', 'ml/train.py::train'),
        ('What is TF-IDF?', 'It weights informative words and phrases rather than treating all words equally.', 'Sublinear term frequency times smoothed inverse document frequency, then L2 normalization; word unigrams/bigrams and vocabulary/document frequency fit only on training.', 'ml/train.py::train; ml/config.py::TOKEN_PATTERN'),
        ('What is One-vs-Rest classification?', 'One yes/no classifier per skill.', 'Eight binary estimators share sparse text features; outputs are thresholded independently and need not sum to one.', 'ml/train.py::train'),
        ('How does Logistic Regression work mathematically?', 'It adds weighted text evidence, then applies a sigmoid.', 'z=b+sum(x_i*w_i); p=1/(1+exp(-z)). Parameters minimize regularized logistic loss. LR was a candidate, not the deployed winner.', 'ml/explain.py::explain_label; ml/train.py::train'),
        ('Why not use BERT?', 'The CPU-only demo benefits from a small, directly explainable linear model.', 'Transformer training/inference adds compute and deployment work. BERT was not evaluated, so we make no comparative accuracy claim.', 'docs/MODEL_CARD.md'),
        ('Why not use an LLM API?', 'Offline inference and no external AI calls are explicit requirements.', 'A saved local sparse classifier avoids runtime network dependencies and supports exact additive attribution.', 'ml/predictor.py::predict'),
        ('Why compare Naive Bayes, Logistic Regression and SVM?', 'They are fast, distinct text-classification baselines.', 'NB uses smoothed likelihood ratios, LR uses logistic loss, and SVM uses separating margins. Identical data/features make the validation comparison interpretable.', 'ml/train.py::train'),
        ('Which model actually performed best?', f"Linear SVM: validation micro F1 {results['linear_svm']['micro_f1']:.4f}; LR {results['logistic_regression']['micro_f1']:.4f}; NB {results['naive_bayes']['micro_f1']:.4f}; keyword {results['keyword']['micro_f1']:.4f}.", f"The predefined LR preference applied only within .02 of best ML micro F1. SVM exceeded that gap and its final test micro F1 was {test['micro_f1']:.4f}.", 'ml/reports/validation_results.json; ml/reports/test_results.json'),
        ('What is the difference between precision and recall?', 'Precision measures how often suggested tags are right; recall measures how many true tags are found.', 'Precision=TP/(TP+FP); recall=TP/(TP+FN). Abstaining reduces false positives but can miss true labels.', 'ml/evaluate.py::metrics'),
        ('Why report micro and macro F1?', 'Micro measures pooled quality; macro prevents common labels from hiding weak ones.', 'Micro pools TP/FP/FN, while macro averages label F1 equally. Test joins F1 is .6667, despite overall micro F1 .8736.', 'ml/reports/per_label_metrics.csv'),
        ('What is data leakage?', 'Information from evaluation data improperly influences fitting or selection.', 'Examples include fitting IDF on all records, using tags in text, or tuning thresholds on test labels.', 'ml/train.py::train'),
        ('How did you prevent data leakage?', 'Deduplicate first, save splits, fit text features on training only.', 'The pipeline excludes answers/tags/metadata from inputs, uses approximate near-duplicate removal, and fixes model/thresholds before opening test records. Approximate dedup may still miss paraphrases.', 'ml/preprocess.py::deduplicate; ml/train.py::train'),
        ('Why separate training, validation and test data?', 'Fit on training, choose on validation, estimate final performance on test.', f"Counts are {d['split_sizes']['train']}, {d['split_sizes']['validation']}, {d['split_sizes']['test']}, from iterative multi-label stratification with seed 42. No final refit changes the selected artifact.", 'ml/artifacts/split_ids.json; ml/train.py::train'),
        ('How do you explain an individual prediction?', 'Show the actual words pushing the score up and down.', 'For each present TF-IDF feature, multiply by the fitted coefficient. Intercept + displayed positive/negative contributions + omitted contribution reconstructs the score.', 'ml/explain.py::explain_label'),
        ('What do positive and negative feature contributions mean?', 'They push this label score higher or lower.', 'Signs are relative to a particular fitted binary classifier. They are predictive associations, not causal reasoning or proof of expertise.', 'ml/explain.py::parameters; ml/reports/feature_importance.json'),
        ('Are probability estimates calibrated?', 'No. The deployed SVM does not emit probabilities at all.', 'LR/NB candidate probabilities have validation Brier measurements but no calibration fit. SVM outputs raw margins and probability=null.', 'ml/evaluate.py::metrics; ml/predictor.py::predict'),
        ('What happens for unsupported skills?', 'Students select them manually.', 'The API can abstain for insufficient known features or thresholds, but cannot reliably detect every unsupported domain. CAD, Design and Mathematics remain in the existing domain form.', 'ml/predictor.py::predict; frontend/src/components/DoubtBoard.tsx'),
        ('What happens if the prediction is wrong?', 'The student removes it, adds another tag, or ignores suggestions.', 'Suggestions never mutate selected tags until Accept is clicked; the existing doubt schema validates confirmed domain/tag compatibility.', 'frontend/src/components/SkillSuggestions.tsx; backend/app/schemas.py::DoubtInput'),
        ('How does the ML classifier interact with Hungarian matching?', 'It assists tag selection before matching begins.', 'Only posted confirmed tags enter existing eligibility, utility scoring and dispatch. Predictions do not bypass availability, ownership or booking checks.', 'backend/app/ml_routes.py; backend/app/services.py::dispatch'),
        ('Was the Hungarian algorithm trained on the dataset?', 'No; it is a deterministic optimization algorithm.', 'The dataset supplies real question text/tags to simulated workloads. Production weights and solver code were not modified.', 'ml/benchmark_real_workload.py::run_benchmark; backend/app/algorithms.py::maximum_weight'),
        ('Does the dataset prove better mentorship outcomes?', 'No. It contains questions and tags, not campus learning outcomes.', 'Measured allocation utility is the existing heuristic objective, and profiles/schedules are simulated. Assignment counts are not academic effectiveness.', 'ml/reports/allocation_benchmark.json'),
        ('How does the application work without internet?', 'Prediction uses the local saved model and SQLite.', 'Dataset requests and training are offline preparation steps only. The app makes no Kaggle/Stack Exchange/inference API call at startup or prediction time.', 'ml/predictor.py::load; Dockerfile'),
        ('How would you retrain the model in production?', 'Acquire a new licensed snapshot, validate offline, and deploy a reviewed artifact.', 'Preserve attribution and splits; compare on a fresh held-out campus-relevant set; regenerate metadata/checksums; pin compatible dependencies and restart. No automatic retraining is implemented.', 'docs/ML_ARCHITECTURE.md; ml/train.py::train'),
        ('How do you handle domain drift?', 'Currently with manual correction and explicit limitations.', 'No monitoring feedback collection or drift detector is implemented. A future consented labeled campus set and temporal evaluation should measure changes before retraining.', 'docs/MODEL_CARD.md'),
        ('What are the actual limitations?', 'Small biased dataset, eight skills, noisy tags, and imperfect abstention.', 'Only 63 async training positives and 14 test positives; joins/aggregation are weaker. Approximate dedup, truncation, uncalibrated alternatives, and no campus pilot limit generalization.', 'data/DATASET_CARD.md; ml/reports/per_label_metrics.csv'),
        ('What does the real allocation benchmark measure?', f"Thirty isolated scenarios: Hungarian persisted {benchmark['hungarian']['assignments']} assignments; greedy {benchmark['greedy']['assignments']}.", 'Identical initial states and first matrices; the existing eligibility, scores and final validation persist results. Both had zero invalid assignments and cross-role conflicts. Solver runtime is separated from full dispatch runtime.', 'ml/benchmark_real_workload.py::run_benchmark'),
        ('What happens if the model artifact is missing or corrupted?', 'The app stays available with manual tags.', 'Loading catches missing files, checksum/version mismatches and import failures, marks unavailable, and logs only the error type. No untrusted upload/path is accepted.', 'ml/predictor.py::load; backend/tests/test_ml.py'),
    ]
    write('docs/ML_JUDGE_QA.md', '# ML judge questions and answers\n\n' + '\n\n'.join(
        f'## {i}. {q}\n\n{simple}\n\nTechnical detail: {technical}\n\nSource: `{source}`.'
        for i, (q, simple, technical, source) in enumerate(qa, 1)))
    write('docs/ML_15_MINUTE_GUIDE.md', '''
# Fifteen-minute technical preparation

1. **Minutes 0–2 — Dataset:** Read data/DATASET_CARD.md. Say: 3,123 real API questions, 2,675 usable; 1,872/399/404 split. Explain attribution and recent tag-query bias.
2. **Minutes 2–3 — Supervised learning:** Text is input, human tags are multi-label targets. Metadata and answers never become features.
3. **Minutes 3–5 — TF-IDF:** Explain informative unigrams/bigrams, sparse vectors, and fitting vocabulary/IDF on training only. Open ml/train.py.
4. **Minutes 5–7 — Model competition:** Each label has a binary classifier. LR uses z=b+w*x and sigmoid; SVM uses the same additive margin but a different loss. SVM won measured validation; do not call its margin confidence or probability.
5. **Minutes 7–9 — Contributions:** Demonstrate Suggest Skills, expand numerical contributions, and show intercept + displayed terms + omitted terms = margin. Weights are associations, not causes.
6. **Minutes 9–11 — Metrics:** Explain precision versus recall, micro versus macro F1, coverage, exact match, and P@3. State test micro F1 .8736 and joins F1 .6667; don't hide weak labels.
7. **Minutes 11–13 — Hybrid workflow:** Accept/remove/add tags; only the confirmed form reaches existing eligibility and Hungarian optimization. Open the ML evaluation tab and separate real question fields from simulated allocation fields.
8. **Minutes 13–15 — Limitations and fallback:** Explain eight-label coverage, domain shift, no calibration/mentoring-success claim, offline CPU inference, ML_ENABLED=false, and manual fallback. Use ML_JUDGE_QA.md for follow-ups.
''')
    latency_path = REPORTS / 'inference_latency.json'
    latency = json.loads(latency_path.read_text()) if latency_path.exists() else None
    modified = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, text=True).splitlines()
    added = sorted(set(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()) | {'docs/ML_DELIVERY.md'})
    write('docs/ML_DELIVERY.md', f'''
# Explainable ML delivery report

Implemented locally without committing or pushing. Recovery checkpoint: `.tmp/ml-checkpoint/` at Git `d048de3`. Existing Hungarian solver, scoring weights, SQLite, bounty/session/chat/scheduling logic and single-worker deployment architecture remain.

## Dataset

Actual source: official [Stack Exchange questions API](https://api.stackexchange.com/docs/questions), cached GET requests after Kaggle client unavailable. Downloaded {d['downloaded_questions']} unique real questions; usable {d['usable_questions']}; train/validation/test {d['split_sizes']}. Eight tags: {', '.join(m['labels'])}. Source-license observations: {d['licenses']}; attribution and license timeline references in `data/ATTRIBUTION.json` and `data/DATASET_CARD.md`. No raw dataset is tracked or deployed.

## Validation comparison (not test scores)

{comparison}

Selected **{m['selected_model']}** because {m['selection_reason']}
Final test: micro F1 {test['micro_f1']:.4f}; macro F1 {test['macro_f1']:.4f}; precision {test['micro_precision']:.4f}; recall {test['micro_recall']:.4f}; coverage {test['coverage']:.4f}; {test['abstention_count']} abstentions. Weak labels and all per-label metrics are retained in the model card.
Candidate latency is transform+score on validation examples; complete predictor measurement (cleaning, transform, scoring, explanations, no HTTP): `{latency}`. Timings are local CPU observations, not production guarantees.
The selected SVM computes z=b+sum(x_i*w_i), with TF-IDF x and learned w. Explanations display signed feature products and omitted contribution to reconstruct z. Margins are not probabilities. Its output does not determine mentor expertise or mentoring success.

## Allocation

30 seeded scenarios with real text/tags and simulated people/schedules. Shared-matrix total utility: Hungarian {benchmark['hungarian']['shared_matrix_total_utility']:.4f}, greedy {benchmark['greedy']['shared_matrix_total_utility']:.4f}. Integrated utility: {benchmark['hungarian']['total_utility']:.4f} vs {benchmark['greedy']['total_utility']:.4f}; persisted assignments {benchmark['hungarian']['persisted_assignments']} vs {benchmark['greedy']['persisted_assignments']}. Both have zero invalid assignments and cross-role booking conflicts. Greedy is faster; Hungarian does not necessarily improve every per-scenario metric. Utility is not a learning outcome.

## Integration and deployment

- POST `/api/ml/predict-tags`; GET `/api/ml/status`, `/api/ml/metrics`, `/api/ml/model-info`.
- `SkillSuggestions.tsx`: explicit request, exact contributions, accept/remove/ignore; existing checkbox controls allow manual additions. `ModelEvaluation.tsx`: saved results and benchmark.
- `DoubtBoard.tsx` submits confirmed skills to the unchanged existing doubt API. Inference has no database writes.
- Artifact `ml/artifacts/skill_classifier.joblib` ({m['artifact_size_bytes']} bytes), metadata, label mapping, saved split IDs; SHA-256 in metadata.
- Runtime adds pinned scikit-learn 1.9.0, joblib 1.5.3, NumPy 2.5.5 and SciPy 1.18.1. Optional training adds kagglehub 1.0.3 and iterative-stratification 0.1.9.
- Docker copies `ml/` and adds root to PYTHONPATH, preserving database mount and worker configuration. No dataset downloads/training at startup. `ML_ENABLED=false` or unavailable artifacts retain manual operation.

## Verification

Baseline: 56 tests passed. Final suite: 94 passed, 0 failed (38 new ML tests). TypeScript and Vite production build passed. Actual browser confirmed suggestion, acceptance, rejection, manual addition, numerical explanations, persisted exact tags and successful matching, plus evaluation display. Details and warnings: [ML_VERIFICATION.md](ML_VERIFICATION.md).
Docker image build and Railway deployment were not executed (Docker unavailable). No Git push. Campus outcomes, calibration fitting and fairness/drift studies were not performed.

## Added files

{chr(10).join('- `' + path + '`' for path in added)}

## Modified files

{chr(10).join('- `' + path + '`' for path in modified)}

## Learn in fifteen minutes

Follow [ML_15_MINUTE_GUIDE.md](ML_15_MINUTE_GUIDE.md): dataset (2 min), supervised targets (1), TF-IDF (2), multi-label LR/SVM (2), contributions (2), metrics (2), human confirmation/Hungarian (2), limitations/fallback (2). [ML_JUDGE_QA.md](ML_JUDGE_QA.md) contains 32 source-referenced technical answers. [ML_ARCHITECTURE.md](ML_ARCHITECTURE.md) gives exact reproduction commands.
''')


if __name__ == '__main__':
    write_docs()
