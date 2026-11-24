"""python -m ml.train -- runs three sparse classifiers and an independent keyword baseline."""
import csv
import hashlib
import importlib.metadata
import io
import json
import platform
from datetime import datetime, timezone
from time import perf_counter
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from .config import ARTIFACTS, REPORTS, PROCESSED, SEED, TOKEN_PATTERN, LABEL_DOMAINS, TAG_MAPPING
from .evaluate import scores_for, choose_thresholds, metrics, keyword_scores, METRIC_DEFINITIONS
from .explain import global_features


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def train():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    data = {name: json.loads((PROCESSED / f'{name}.json').read_text(encoding='utf-8')) for name in ('train', 'validation')}
    dataset = json.loads((PROCESSED / 'dataset_metadata.json').read_text(encoding='utf-8'))
    labels = dataset['labels']
    encoder = MultiLabelBinarizer(classes=labels)
    y_train = encoder.fit_transform([q['labels'] for q in data['train']])
    y_val = encoder.transform([q['labels'] for q in data['validation']])
    texts = {k: [q['text'] for q in v] for k, v in data.items()}
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=.98, max_features=30000,
                               sublinear_tf=True, lowercase=True, token_pattern=TOKEN_PATTERN)
    tick = perf_counter()
    x_train = vectorizer.fit_transform(texts['train'])
    vectorizer_seconds = perf_counter() - tick
    x_val = vectorizer.transform(texts['validation'])
    usable_val = x_val.getnnz(axis=1) >= 2
    candidates = {'naive_bayes': MultinomialNB(alpha=.5),
                  'logistic_regression': LogisticRegression(C=1, max_iter=1000, random_state=SEED),
                  'linear_svm': LinearSVC(C=1, random_state=SEED)}
    results, fitted = {}, {}
    keyword = keyword_scores(texts['validation'], labels)
    results['keyword'] = metrics(y_val, keyword, .5, labels)
    results['keyword'].update(training_seconds=0, model_size_bytes=0, explainability='Predefined lexical rules; no learned weights', deployment='No ML dependencies')
    latencies = []
    for text in texts['validation'][:100]:
        tick = perf_counter(); keyword_scores([text], labels); latencies.append((perf_counter()-tick)*1000)
    results['keyword']['median_inference_ms'] = float(np.median(latencies))
    for name, estimator in candidates.items():
        tick = perf_counter()
        classifier = OneVsRestClassifier(estimator).fit(x_train, y_train)
        duration = perf_counter() - tick + vectorizer_seconds
        probabilistic = name != 'linear_svm'
        scores = scores_for(classifier, x_val)
        thresholds = choose_thresholds(y_val, scores, probabilistic)
        result = metrics(y_val, scores, thresholds, labels, probabilistic, usable_val)
        result['default_threshold_metrics'] = metrics(y_val, scores, .5 if probabilistic else 0, labels, probabilistic)
        artifact = {'vectorizer': vectorizer, 'classifier': classifier, 'encoder': encoder, 'labels': labels,
                    'thresholds': thresholds, 'model_type': name, 'minimum_features': 2}
        stream = io.BytesIO(); joblib.dump(artifact, stream, compress=3)
        timings = []
        for text in texts['validation'][:100]:
            tick = perf_counter(); scores_for(classifier, vectorizer.transform([text])); timings.append((perf_counter()-tick)*1000)
        result.update(training_seconds=duration, vectorizer_seconds=vectorizer_seconds,
                      median_inference_ms=float(np.median(timings)), model_size_bytes=stream.tell(), thresholds=thresholds.tolist(),
                      explainability='Exact additive linear weights' if probabilistic and name != 'naive_bayes' else 'Log likelihood ratios' if name == 'naive_bayes' else 'Exact additive margin weights',
                      deployment='CPU scikit-learn + joblib; offline sparse inference')
        results[name] = result
        fitted[name] = artifact
        print(name, 'validation micro F1:', result['micro_f1'], flush=True)
    best = max(candidates, key=lambda name: results[name]['micro_f1'])
    selected = 'logistic_regression' if results['logistic_regression']['micro_f1'] >= results[best]['micro_f1'] - .02 else best
    reason = ('Prefer Logistic Regression within 0.02 absolute validation micro F1 of the best ML candidate for direct logit interpretation and probability estimates.'
              if selected == 'logistic_regression' else 'Best validation micro F1; Logistic Regression fell more than 0.02 behind. Mathematical explanations use selected model parameters.')
    artifact = fitted[selected]
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    artifact['model_version'] = version
    artifact_path = ARTIFACTS / 'skill_classifier.joblib'
    joblib.dump(artifact, artifact_path, compress=3)
    # Test labels are first opened after model and thresholds have been fixed.
    test = json.loads((PROCESSED / 'test.json').read_text(encoding='utf-8'))
    y_test = encoder.transform([q['labels'] for q in test])
    x_test = vectorizer.transform([q['text'] for q in test])
    scores = scores_for(artifact['classifier'], x_test)
    probabilistic = selected != 'linear_svm'
    test_result = metrics(y_test, scores, artifact['thresholds'], labels, probabilistic, x_test.getnnz(axis=1) >= 2)
    test_result['default_threshold_metrics'] = metrics(y_test, scores, .5 if probabilistic else 0, labels, probabilistic)
    test_result['selected_model'] = selected
    save_json(REPORTS / 'validation_results.json', results)
    save_json(REPORTS / 'test_results.json', test_result)
    fields = ['model', 'micro_f1', 'macro_f1', 'micro_precision', 'micro_recall', 'precision_at_3', 'training_seconds', 'median_inference_ms', 'model_size_bytes', 'explainability', 'deployment']
    with (REPORTS / 'model_comparison.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for name, result in results.items():
            writer.writerow({'model': name, **{key: result[key] for key in fields[1:]}})
    with (REPORTS / 'per_label_metrics.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['partition', 'model', 'label', 'precision', 'recall', 'f1', 'support']); writer.writeheader()
        for partition, values in [('validation', results), ('test', {selected: test_result})]:
            for name, result in values.items():
                for label, values in result['per_label'].items():
                    writer.writerow({'partition': partition, 'model': name, 'label': label, **values})
    importance = global_features(artifact['classifier'], vectorizer, labels, dataset['label_distribution']['train'])
    for label in labels:
        importance[label]['validation_metrics'] = results[selected]['per_label'][label]
        importance[label]['test_metrics'] = test_result['per_label'][label]
    save_json(REPORTS / 'feature_importance.json', importance)
    metadata = {'model_version': version, 'selected_model': selected, 'selection_reason': reason,
        'best_validation_model': best, 'dataset': {k: v for k, v in dataset.items() if k != 'split_ids'},
        'labels': labels, 'thresholds': artifact['thresholds'].tolist(), 'seed': SEED,
        'feature_extraction': 'Training-only TF-IDF; word 1-2 grams; technical token pattern; min_df=2; max_df=.98; max_features=30000; sublinear_tf',
        'feature_count': len(vectorizer.vocabulary_), 'training_configuration': {k: str(v) for k, v in candidates.items()},
        'trained_at': datetime.now(timezone.utc).isoformat(), 'python_version': platform.python_version(),
        'dependencies': {p: importlib.metadata.version(p) for p in ('scikit-learn', 'joblib', 'numpy', 'scipy', 'iterative-stratification')},
        'artifact_sha256': hashlib.sha256(artifact_path.read_bytes()).hexdigest(), 'artifact_size_bytes': artifact_path.stat().st_size,
        'split_ids_sha256': hashlib.sha256((ARTIFACTS / 'split_ids.json').read_bytes()).hexdigest(),
        'validation': results[selected], 'test': test_result, 'metric_definitions': METRIC_DEFINITIONS,
        'limitations': ['Stack Overflow differs from student doubts.', 'Only eight technical skills targeted; unsupported tags omitted.',
                       'Probability estimates are uncalibrated, not verified correctness.', 'Feature weights are associations, not causes.',
                       'Simple feature-count abstention cannot reliably detect all out-of-domain inputs.',
                       'Tag-specific recent sampling is not representative of all Stack Overflow.',
                       'Approximate near-duplicate detection may miss paraphrases.', 'No evidence of improved learning or mentoring success.']}
    save_json(ARTIFACTS / 'model_metadata.json', metadata)
    save_json(ARTIFACTS / 'label_mapping.json', {'source_tags': TAG_MAPPING, 'label_domains': {k: LABEL_DOMAINS[k] for k in labels}})
    predicted = scores >= artifact['thresholds']
    predicted[x_test.getnnz(axis=1) < 2] = False
    errors = ['# Held-out error analysis', '', 'First 12 non-exact predictions in saved test order; not selected for flattering results.',
              'Question text is not redistributed here. Follow attributed source links; local processed records preserve text and authors.', '']
    for i in np.flatnonzero(np.any(predicted != y_test, axis=1))[:12]:
        q = test[i]
        errors.append(f"- Question [{q['id']}]({q['url']}), author {q['owner'].get('display_name', q['owner'].get('user_id', 'unknown'))}, {q['license']}: true {q['labels']}; predicted {[labels[j] for j in np.flatnonzero(predicted[i])]}")
    errors.extend(['', 'Possible causes (hypotheses, not proven explanations): overlapping skills, missing context, rare labels, historical tagging omissions, long-body truncation, unfamiliar identifiers, and domain shift. See per_label_metrics.csv for every label, including weak ones.', '', 'Global associations are in feature_importance.json. Positive weights increase the label score; negative weights reduce it. They do not establish causation.'])
    (REPORTS / 'error_analysis.md').write_text('\n'.join(errors), encoding='utf-8')
    print('Selected:', selected, 'test micro F1:', test_result['micro_f1'], flush=True)


if __name__ == '__main__':
    train()
