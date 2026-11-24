"""Shared metrics; test data is evaluated only after validation-based selection."""
import re
import numpy as np
from sklearn.metrics import (precision_recall_fscore_support, f1_score, hamming_loss, accuracy_score)
from .config import ALIASES


def keyword_scores(texts, labels):
    return np.array([[float(any(re.search(r'(?<!\w)' + re.escape(a) + (r'(?!\w)' if a[-1].isalnum() else ''),
                                         text.lower()) for a in ALIASES[label]))
                      for label in labels] for text in texts])


def scores_for(classifier, x):
    if hasattr(classifier, 'predict_proba'):
        return classifier.predict_proba(x)
    return classifier.decision_function(x)


def choose_thresholds(y, scores, probabilistic):
    grid = np.arange(.1, .81, .05) if probabilistic else np.arange(-1, 1.01, .1)
    # Per-label F1 on validation only; ties prefer the higher, more selective threshold.
    return np.array([max(grid, key=lambda t: (f1_score(y[:, j], scores[:, j] >= t, zero_division=0), t))
                     for j in range(y.shape[1])])


def metrics(y, scores, thresholds, labels, probabilistic=False, usable=None):
    predicted = scores >= thresholds
    if usable is not None:
        predicted[~usable] = False
    result = {}
    for average in ('micro', 'macro', 'samples'):
        p, r, f, _ = precision_recall_fscore_support(y, predicted, average=average, zero_division=0)
        result.update({f'{average}_precision': float(p), f'{average}_recall': float(r), f'{average}_f1': float(f)})
    k = min(3, len(labels))
    top = np.argsort(-scores, axis=1, kind='stable')[:, :k]
    covered = predicted.any(axis=1)
    result.update(hamming_loss=float(hamming_loss(y, predicted)), exact_match_accuracy=float(accuracy_score(y, predicted)),
                  precision_at_3=float(np.take_along_axis(y, top, axis=1).sum() / (len(y) * k)),
                  coverage=float(covered.mean()), abstention_count=int((~covered).sum()),
                  covered_micro_f1=float(f1_score(y[covered], predicted[covered], average='micro', zero_division=0)) if covered.any() else None)
    p, r, f, support = precision_recall_fscore_support(y, predicted, average=None, zero_division=0)
    result['per_label'] = {label: {'precision': float(p[i]), 'recall': float(r[i]), 'f1': float(f[i]), 'support': int(support[i])}
                           for i, label in enumerate(labels)}
    if probabilistic:
        result['brier_score'] = float(np.mean((y - scores) ** 2))
        result['probability_notice'] = 'Uncalibrated estimates; Brier score measured, no calibration fitted.'
    return result


METRIC_DEFINITIONS = {
    'micro_precision': 'Correct positive labels / all positive predictions, pooled across labels.',
    'micro_recall': 'Correct positive labels / all true positive labels, pooled across labels.',
    'micro_f1': 'Harmonic mean of pooled precision and recall.',
    'macro_f1': 'Unweighted mean of each label F1; exposes weak minority labels.',
    'macro_precision': 'Unweighted mean of each label precision.',
    'macro_recall': 'Unweighted mean of each label recall.',
    'samples_f1': 'Mean per-question F1; zero division is scored zero.',
    'hamming_loss': 'Fraction of question-label binary decisions that are wrong.',
    'exact_match_accuracy': 'Fraction with the entire label set exactly correct.',
    'precision_at_3': 'Mean relevant labels among top three / 3, before thresholding. Not recall@3.',
    'coverage': 'Fraction of questions receiving at least one recommendation.',
    'covered_micro_f1': 'Micro F1 only on questions receiving recommendations; report with coverage.',
    'brier_score': 'Mean squared error of per-label probability estimates (lower is better).',
    'default_threshold_metrics': 'Counterfactual using 0.5 probabilities or zero SVM margins, with no feature abstention gate.',
}
