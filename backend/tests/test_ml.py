import json
from pathlib import Path
import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from ml.config import ARTIFACTS, LABEL_DOMAINS, TOKEN_PATTERN
from ml.preprocess import clean_html, model_text, normalize_tags, deduplicate
from ml.explain import explain_label
from ml.predictor import SkillPredictor
from app.config import DOMAINS
from app import ml_routes
from conftest import headers


@pytest.mark.parametrize('value,expected', [('', ''), (None, ''), ('<p>Hello &amp; world</p>', 'Hello & world'),
    ('<code>C++ C# .NET Node.js React</code>', 'C++ C# .NET Node.js React'),
    ('<pre>if x &lt; 3: raise ValueError(&quot;bad&quot;)</pre>', 'if x < 3: raise ValueError("bad")')])
def test_clean_technical_text(value, expected):
    assert clean_html(value) == expected


def test_technical_tokenization_and_length():
    vectorizer = TfidfVectorizer(token_pattern=TOKEN_PATTERN)
    names = vectorizer.fit(['C++ C# .NET Node.js React useEffect']).get_feature_names_out()
    assert {'c++', 'c#', '.net', 'node.js', 'react', 'useeffect'} <= set(names)
    assert len(model_text('t'*200, 'b'*4000)) == 3151


@pytest.mark.parametrize('tags,expected', [(['python-3.x', 'pandas'], ['pandas', 'python']),
    (['reactjs', 'javascript', 'async-await'], ['async', 'javascript', 'react']),
    (['c#', 'asynchronous'], []), (['pandas', 'aggregate-functions'], ['pandas']),
    (['postgresql', 'join'], ['joins', 'sql']), (['biology'], [])])
def test_tag_mapping(tags, expected):
    assert normalize_tags(tags) == expected


def test_duplicate_removal_and_label_union():
    a = {'id': '1', 'title': 'Python pandas dataframe issue', 'text': 'same technical question text', 'labels': ['python']}
    b = {**a, 'id': '2', 'labels': ['pandas']}
    rows, removed = deduplicate([a, b])
    assert removed == 1
    assert rows[0]['labels'] == ['pandas', 'python']
    assert rows[0]['duplicate_source_ids'] == ['2']


def test_saved_partitions_disjoint():
    ids = json.loads((ARTIFACTS / 'split_ids.json').read_text())
    assert not set(ids['train']) & set(ids['test'])
    assert not set(ids['validation']) & set(ids['test'])
    assert not set(ids['train']) & set(ids['validation'])
    processed = ARTIFACTS.parents[1] / 'data' / 'processed'
    if processed.exists():
        parts = [{q['text_sha256'] for q in json.loads((processed / f'{part}.json').read_text(encoding='utf-8'))} for part in ids]
        assert not parts[0] & parts[1] and not parts[0] & parts[2] and not parts[1] & parts[2]


@pytest.mark.parametrize('estimator', [LogisticRegression(), LinearSVC(), MultinomialNB()])
def test_explanations_reconstruct_actual_model(estimator):
    texts = ['python pandas dataframe']*5 + ['javascript react component']*5
    vectorizer = TfidfVectorizer()
    x = vectorizer.fit_transform(texts)
    estimator.fit(x, [1]*5 + [0]*5)
    row = vectorizer.transform(['python pandas react component'])
    result = explain_label(estimator, row, vectorizer.get_feature_names_out(), limit=1)
    assert result['positive_features'] and result['negative_features']
    displayed = sum(f['contribution'] for f in result['positive_features'] + result['negative_features'])
    assert result['intercept'] + displayed + result['omitted_contribution'] == pytest.approx(result['decision_score'])
    if hasattr(estimator, 'decision_function'):
        expected = estimator.decision_function(row)[0]
    else:
        probabilities = estimator.predict_log_proba(row)[0]
        expected = probabilities[1] - probabilities[0]
    assert result['decision_score'] == pytest.approx(expected)
    for feature in result['positive_features'] + result['negative_features']:
        assert feature['contribution'] == pytest.approx(feature['tfidf_value'] * feature['weight'])


@pytest.fixture(scope='module')
def predictor():
    result = SkillPredictor()
    assert result.status()['available']
    return result


def test_prediction_deterministic_and_supported(predictor):
    args = ('Python pandas DataFrame problem', 'In Python pandas how can I merge DataFrame columns and filter rows using pandas?')
    first = predictor.predict(*args)
    assert first == predictor.predict(*args)
    assert len(first['suggestions']) >= 2
    for suggestion in first['suggestions']:
        assert suggestion['label'] in DOMAINS[suggestion['domain']]
        if first['model_type'] == 'linear_svm':
            assert suggestion['model_probability_estimate'] is None
            assert 'not a probability' in suggestion['score_scale']


@pytest.mark.parametrize('title,body', [('', ''), ('zzzzzz', 'qxqzv zzzzxv qqqqqq')])
def test_abstention(predictor, title, body):
    result = predictor.predict(title, body)
    assert result['abstained'] and not result['suggestions']
    assert result['reason'] == 'insufficient_known_features'


def test_missing_artifact_and_disabled(tmp_path, monkeypatch):
    p = SkillPredictor(tmp_path)
    assert not p.status()['available']
    assert p.predict('Hello', 'Question body')['reason'] == 'model_unavailable'
    monkeypatch.setenv('ML_ENABLED', 'false')
    assert SkillPredictor().status()['loading_status'] == 'disabled'


def test_corrupted_artifact_is_not_loaded(tmp_path):
    (tmp_path / 'model_metadata.json').write_bytes((ARTIFACTS / 'model_metadata.json').read_bytes())
    (tmp_path / 'skill_classifier.joblib').write_bytes(b'untrusted invalid pickle')
    assert not SkillPredictor(tmp_path).status()['available']


def test_missing_inference_dependency_falls_back(monkeypatch):
    import importlib.metadata
    def missing(*args):
        raise importlib.metadata.PackageNotFoundError('scikit-learn')
    monkeypatch.setattr(importlib.metadata, 'version', missing)
    assert not SkillPredictor().status()['available']


@pytest.mark.parametrize('mode', ['disabled', 'missing'])
def test_application_startup_without_model(clean, tmp_path, monkeypatch, mode):
    from fastapi.testclient import TestClient
    from app import main
    if mode == 'disabled':
        monkeypatch.setenv('ML_ENABLED', 'false')
    service = SkillPredictor(tmp_path if mode == 'missing' else ARTIFACTS)
    monkeypatch.setattr(main, 'predictor', service)
    monkeypatch.setattr(ml_routes, 'predictor', service)
    with TestClient(main.app) as running:
        assert running.get('/api/health').json()['status'] == 'ok'
        assert not running.get('/api/ml/status').json()['available']
        assert running.get('/api/domains').json()['Mathematics']


def test_api_status_metrics_and_read_only_prediction(client):
    assert client.get('/api/ml/status').json()['available']
    assert client.get('/api/ml/metrics').json()['test']['micro_f1'] >= 0
    assert client.get('/api/ml/model-info').json()['metadata']['dataset']['split_sizes']['train'] > 0
    before = client.get('/api/doubts').json()
    result = client.post('/api/ml/predict-tags', json={'title': 'React rendering', 'description': 'React useEffect updates state repeatedly.'})
    assert result.status_code == 200
    assert client.get('/api/doubts').json() == before


@pytest.mark.parametrize('body', [{}, {'title': 'x', 'description': 'body text'},
    {'title': 'valid title', 'description': ''}, {'title': 'valid title', 'description': '     '},
    {'title': 'valid title', 'description': 'x'*3001}, {'title': 'x'*151, 'description': 'valid text'},
    {'title': 'valid title', 'description': 'valid text', 'skills': ['react']}])
def test_api_input_validation(client, body):
    assert client.post('/api/ml/predict-tags', json=body).status_code == 422


def test_unavailable_api_manual_flow(clean, tmp_path, monkeypatch):
    monkeypatch.setattr(ml_routes, 'predictor', SkillPredictor(tmp_path))
    assert not clean.get('/api/ml/status').json()['available']
    assert not clean.get('/api/ml/metrics').json()['available']
    assert clean.post('/api/ml/predict-tags', json={'title': 'Python help', 'description': 'Please explain this code.'}).json()['abstained']
    response = clean.post('/api/doubts', headers=headers(), json={'title': 'Manual algebra help',
        'description': 'Help with solving quadratic equations.', 'domain': 'Mathematics', 'skills': ['algebra']})
    assert response.status_code == 201


@pytest.mark.parametrize('confirmed', [['python', 'pandas'], ['python'], ['python', 'debugging']])
def test_only_confirmed_tags_enter_existing_workflow(clean, confirmed):
    clean.post('/api/ml/predict-tags', json={'title': 'Python pandas help', 'description': 'Python pandas DataFrame merge and filter rows.'})
    response = clean.post('/api/doubts', headers=headers(), json={'title': 'Python pandas help',
        'description': 'Python pandas DataFrame merge and filter rows.', 'domain': 'Python', 'skills': confirmed})
    assert response.status_code == 201
    assert set(response.json()['skills']) == set(confirmed)
    assert clean.post('/api/dispatch/run', headers=headers()).status_code == 200


def test_real_workload_report_integrity():
    report = json.loads((ARTIFACTS.parent / 'reports/allocation_benchmark.json').read_text())
    assert len(report['scenarios']) >= 30
    for scenario in report['scenarios']:
        for solver in ('hungarian', 'greedy'):
            values = scenario[solver]
            assert values['invalid_assignments'] == 0
            assert values['cross_role_booking_conflicts'] == 0
            assert values['persisted_assignments'] == values['assignments']
            assert values['assignments'] + values['unassigned'] == scenario['request_count']
        matrix = scenario.get('shared_matrix')
        if matrix:
            assert matrix['hungarian']['total_utility'] + 1e-4 >= matrix['greedy']['total_utility']
