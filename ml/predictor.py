"""One trusted local artifact per process; unavailable ML never blocks manual tags."""
import hashlib
import importlib.metadata
import json
import logging
import os
from threading import Lock
from .config import ARTIFACTS, LABEL_DOMAINS, REPORTS
from .preprocess import model_text

log = logging.getLogger(__name__)


class SkillPredictor:
    def __init__(self, artifact_dir=ARTIFACTS):
        self.artifact_dir = artifact_dir
        self.artifact = None
        self.metadata = None
        self.loading_status = 'not_loaded'
        self._lock = Lock()

    def load(self):
        with self._lock:
            if self.loading_status != 'not_loaded':
                return
            if os.getenv('ML_ENABLED', 'true').lower() in ('0', 'false', 'no'):
                self.loading_status = 'disabled'
                return
            try:
                metadata = json.loads((self.artifact_dir / 'model_metadata.json').read_text(encoding='utf-8'))
                path = self.artifact_dir / 'skill_classifier.joblib'
                if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['artifact_sha256']:
                    raise ValueError('Artifact checksum mismatch')
                for package in ('scikit-learn', 'joblib', 'numpy', 'scipy'):
                    if importlib.metadata.version(package) != metadata['dependencies'][package]:
                        raise ValueError('Incompatible inference dependency')
                import joblib
                # Only our packaged artifact is accepted; no user path or upload endpoint.
                artifact = joblib.load(path)
                from backend.app.config import DOMAINS
                if not all(label in DOMAINS[LABEL_DOMAINS[label]] for label in artifact['labels']):
                    raise ValueError('Unsupported skill vocabulary')
                self.metadata = metadata
                self.artifact = artifact
                self.loading_status = 'loaded'
            except Exception as exc:
                self.loading_status = 'unavailable'
                log.warning('Optional skill model unavailable (%s); manual tags remain enabled.', type(exc).__name__)

    def status(self):
        self.load()
        return {'available': self.artifact is not None, 'loading_status': self.loading_status,
                'model_type': self.artifact['model_type'] if self.artifact else None,
                'model_version': self.artifact['model_version'] if self.artifact else None,
                'supported_labels': self.artifact['labels'] if self.artifact else []}

    def predict(self, title, description):
        status = self.status()
        result = {**status, 'suggestions': [], 'abstained': True,
                  'manual_action': 'Select or confirm skill tags manually before posting.'}
        if not self.artifact:
            return {**result, 'reason': 'model_unavailable'}
        from .evaluate import scores_for
        from .explain import explain_label
        artifact = self.artifact
        text = model_text(title, description)
        row = artifact['vectorizer'].transform([text])
        if row.nnz < artifact['minimum_features']:
            return {**result, 'reason': 'insufficient_known_features'}
        values = scores_for(artifact['classifier'], row)[0]
        names = artifact['vectorizer'].get_feature_names_out()
        probabilistic = artifact['model_type'] != 'linear_svm'
        for i, label in enumerate(artifact['labels']):
            if values[i] < artifact['thresholds'][i]:
                continue
            explanation = explain_label(artifact['classifier'].estimators_[i], row, names)
            result['suggestions'].append({'label': label, 'domain': LABEL_DOMAINS[label], **explanation,
                'model_probability_estimate': float(values[i]) if probabilistic else None,
                'threshold': float(artifact['thresholds'][i]),
                'score_scale': ('Uncalibrated probability estimate; decision score is log odds.' if probabilistic
                                else 'Linear SVM margin, not a probability.'),
                'explanation_method': 'NB log prior and log likelihood ratios' if artifact['model_type'] == 'naive_bayes' else 'TF-IDF times learned linear coefficients'})
        result['suggestions'].sort(key=lambda s: s['model_probability_estimate'] if probabilistic else s['decision_score'], reverse=True)
        result['abstained'] = not bool(result['suggestions'])
        result['reason'] = 'below_validation_thresholds' if result['abstained'] else 'confirm_before_use'
        return result

    def reports(self):
        status = self.status()
        if not self.artifact:
            return {**status, 'validation': {}, 'test': {}, 'feature_importance': {}, 'allocation_benchmark': None}
        def read(name, default):
            try:
                return json.loads((REPORTS / name).read_text(encoding='utf-8'))
            except (OSError, ValueError):
                return default
        return {**status, 'validation': read('validation_results.json', {}), 'test': self.metadata['test'],
                'feature_importance': read('feature_importance.json', {}),
                'allocation_benchmark': read('allocation_benchmark.json', None),
                'predictor_latency': read('inference_latency.json', None),
                'metric_definitions': self.metadata['metric_definitions']}


predictor = SkillPredictor()
