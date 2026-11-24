"""Download StackSample with a bounded attempt, then cache official API pages.

Run from the repository root: python scripts/download_dataset.py
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
TAGS = ['python', 'pandas', 'javascript', 'reactjs', 'sql', 'join', 'aggregate-functions', 'async-await']


def acquire(api_only=False, pages=4, kaggle_timeout=90):
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = RAW / 'acquisition.json'
    if manifest.exists():
        print('Reusing acquisition:', manifest)
        return
    free = shutil.disk_usage(RAW).free
    print(f'Free disk: {free / 1024**3:.1f} GiB', flush=True)
    reason = 'API explicitly requested'
    if not api_only and free > 8 * 1024**3:
        env = {**os.environ, 'KAGGLEHUB_CACHE': str(RAW / 'kaggle-cache')}
        code = "import kagglehub; print(kagglehub.dataset_download('stackoverflow/stacksample'))"
        try:
            # Capture logs locally: never print authentication-related exception details.
            with (RAW / 'kaggle-attempt.log').open('w', encoding='utf-8') as log:
                result = subprocess.run([sys.executable, '-c', code], env=env,
                                        stdout=log, stderr=log, timeout=kaggle_timeout)
            questions = list((RAW / 'kaggle-cache').rglob('Questions.csv'))
            if result.returncode == 0 and questions:
                source = {'source': 'StackSample', 'url': 'https://www.kaggle.com/datasets/stackoverflow/stacksample',
                          'questions_path': str(questions[0].relative_to(ROOT)), 'method': 'kagglehub.dataset_download'}
                manifest.write_text(json.dumps({**source, 'acquired_at': datetime.now(timezone.utc).isoformat()}, indent=2))
                print('StackSample acquired', flush=True)
                return
            reason = 'Kaggle download failed or no Questions.csv found'
        except subprocess.TimeoutExpired:
            reason = f'Kaggle exceeded {kaggle_timeout}s time budget'
    elif not api_only:
        reason = 'Insufficient disk for full StackSample'
    print(reason + '; using official API', flush=True)
    import httpx
    records = {}
    requests = []
    stop = False
    with httpx.Client(timeout=40, follow_redirects=True) as client:
        for page in range(1, pages + 1):
            for tag in TAGS:
                cache = RAW / f'api-{tag}-{page}.json'
                params = {'site': 'stackoverflow', 'tagged': tag, 'pagesize': 100,
                          'sort': 'creation', 'order': 'desc', 'page': page, 'filter': 'withbody',
                          'todate': 1795392000}  # fixed 2026-11-23 UTC sampling cutoff
                try:
                    if cache.exists():
                        payload = json.loads(cache.read_text(encoding='utf-8'))
                    else:
                        response = client.get('https://api.stackexchange.com/2.3/questions', params=params)
                        response.raise_for_status()
                        payload = response.json()
                        cache.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                        time.sleep(max(1.0, payload.get('backoff', 0)))
                    if 'error_id' in payload:
                        stop = True
                        break
                    for item in payload.get('items', []):
                        records[item['question_id']] = item
                    requests.append({'params': params, 'items': len(payload.get('items', [])),
                                     'quota_remaining': payload.get('quota_remaining')})
                    print(f'{tag} page {page}: {len(records)} unique questions', flush=True)
                    if payload.get('quota_remaining', 1) <= 1:
                        stop = True
                        break
                except (httpx.HTTPError, ValueError):
                    print('API request unavailable; preserving successfully acquired data', flush=True)
                    stop = True
                    break
            if stop:
                break
    if not records:
        raise SystemExit('No real dataset acquired. ML must remain unavailable.')
    (RAW / 'questions.json').write_text(json.dumps(list(records.values()), ensure_ascii=False), encoding='utf-8')
    manifest.write_text(json.dumps({'source': 'Stack Exchange API', 'url': 'https://api.stackexchange.com/docs/questions',
        'method': 'GET /2.3/questions; cached pages; sort=creation; fixed cutoff',
        'acquired_at': datetime.now(timezone.utc).isoformat(), 'fallback_reason': reason,
        'downloaded_questions': len(records), 'requests': requests}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-only', action='store_true')
    parser.add_argument('--pages', type=int, default=4)
    parser.add_argument('--kaggle-timeout', type=int, default=90)
    args = parser.parse_args()
    acquire(args.api_only, args.pages, args.kaggle_timeout)
