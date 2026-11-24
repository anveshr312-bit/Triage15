"""Exact additive attributions, not keyword surrogates."""
import numpy as np


def parameters(estimator):
    if hasattr(estimator, 'coef_'):
        return estimator.coef_[0], float(estimator.intercept_[0])
    # Binary NB log posterior odds = prior log odds + token log-likelihood ratios.
    return estimator.feature_log_prob_[1] - estimator.feature_log_prob_[0], float(estimator.class_log_prior_[1] - estimator.class_log_prior_[0])


def explain_label(estimator, row, feature_names, limit=6):
    weights, intercept = parameters(estimator)
    contributions = row.data * weights[row.indices]
    order = np.argsort(contributions)
    positive = [int(i) for i in order[::-1] if contributions[i] > 0][:limit]
    negative = [int(i) for i in order if contributions[i] < 0][:limit]
    shown = positive + negative
    def entry(i):
        return {'feature': str(feature_names[row.indices[i]]), 'contribution': float(contributions[i]),
                'tfidf_value': float(row.data[i]), 'weight': float(weights[row.indices[i]])}
    return {'intercept': intercept, 'decision_score': float(intercept + contributions.sum()),
            'positive_features': [entry(i) for i in positive], 'negative_features': [entry(i) for i in negative],
            'omitted_contribution': float(contributions.sum() - contributions[shown].sum()),
            'total_feature_contribution': float(contributions.sum())}


def global_features(classifier, vectorizer, labels, support):
    names = vectorizer.get_feature_names_out()
    output = {}
    for label, estimator in zip(labels, classifier.estimators_):
        weights, intercept = parameters(estimator)
        order = np.argsort(weights)
        output[label] = {'intercept': intercept, 'training_examples': support[label],
            'positive': [{'feature': str(names[i]), 'weight': float(weights[i])} for i in order[::-1][:15] if weights[i] > 0],
            'negative': [{'feature': str(names[i]), 'weight': float(weights[i])} for i in order[:15] if weights[i] < 0]}
    return output
