"""Measure warm complete predictor latency separately from model-only comparison."""
import json
from pathlib import Path
import sys
from statistics import median
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.config import REPORTS
from ml.predictor import SkillPredictor


if __name__ == '__main__':
    predictor = SkillPredictor()
    if not predictor.status()['available']:
        raise SystemExit('Model unavailable; no latency reported')
    examples = [('React rendering', 'My useEffect updates React state repeatedly.'),
                ('Python pandas DataFrame', 'How do I merge pandas DataFrame columns in Python?'),
                ('SQL query joins', 'SELECT count(*) from users left join orders group by users.id')]
    for example in examples:
        predictor.predict(*example)
    timings = []
    for i in range(100):
        start = perf_counter()
        predictor.predict(*examples[i % len(examples)])
        timings.append((perf_counter() - start) * 1000)
    result = {'measurement': 'Warm local predictor including cleaning, transform, scoring and explanations; illustrative inputs; excludes HTTP',
              'median_ms': median(timings), 'p95_ms': sorted(timings)[94], 'calls': len(timings)}
    (REPORTS / 'inference_latency.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
