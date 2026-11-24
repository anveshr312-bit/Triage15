"""Inspect source schemas, preserve technical text, deduplicate, and split offline."""
import csv
import hashlib
import html
from html.parser import HTMLParser
import json
import random
import re
import zlib
from collections import Counter, defaultdict
from .config import ROOT, PROCESSED, SEED, TAG_MAPPING, LABEL_DOMAINS


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean_html(value):
    parser = TextExtractor()
    parser.feed(value or '')
    return re.sub(r'\s+', ' ', html.unescape(' '.join(parser.parts))).strip()


def model_text(title, description):
    return (clean_html(title)[:150] + ' ' + clean_html(description)[:3000]).strip()


def normalize_tags(tags):
    tags = {str(t).lower().strip() for t in tags}
    labels = {TAG_MAPPING[t] for t in tags if t in TAG_MAPPING}
    # The app's async skill belongs to JavaScript, not Python/C#/Java async APIs.
    if not tags.intersection({'javascript', 'reactjs', 'react-hooks'}):
        labels.discard('async')
    # A generic join/aggregation tag can describe pandas, Spark, or other systems.
    if 'sql' not in labels:
        labels.difference_update({'joins', 'aggregation'})
    return sorted(labels)


def source_records(manifest):
    raw = ROOT / 'data' / 'raw'
    if manifest['source'] == 'Stack Exchange API':
        items = json.loads((raw / 'questions.json').read_text(encoding='utf-8'))
        print('Actual API schema:', sorted(items[0]))
        for q in items:
            yield {'id': str(q['question_id']), 'title': q.get('title', ''), 'body': q.get('body', ''),
                   'tags': q.get('tags', []), 'created_at': q.get('creation_date'),
                   'url': q.get('link'), 'owner': q.get('owner', {}), 'license': q.get('content_license', 'see post timeline')}
    else:
        path = ROOT / manifest['questions_path']
        tags = defaultdict(list)
        # Streaming readers keep the multi-GB questions file out of memory.
        with (path.parent / 'Tags.csv').open(encoding='latin-1', newline='') as f:
            reader = csv.DictReader(f)
            print('Actual tags schema:', reader.fieldnames)
            if not {'Id', 'Tag'} <= set(reader.fieldnames or []):
                raise ValueError('Unexpected Tags.csv schema')
            for row in reader:
                if row['Tag'] in TAG_MAPPING:
                    tags[row['Id']].append(row['Tag'])
        with path.open(encoding='latin-1', newline='') as f:
            reader = csv.DictReader(f)
            print('Actual questions schema:', reader.fieldnames)
            if not {'Id', 'Title', 'Body'} <= set(reader.fieldnames or []):
                raise ValueError('Unexpected Questions.csv schema')
            for q in reader:
                if q['Id'] in tags:
                    yield {'id': q['Id'], 'title': q['Title'], 'body': q['Body'], 'tags': tags[q['Id']],
                           'created_at': q.get('CreationDate'), 'url': 'https://stackoverflow.com/questions/' + q['Id'],
                           'owner': {'user_id': q.get('OwnerUserId')}, 'license': 'CC BY-SA; see source post timeline'}


def deduplicate(records):
    kept, fingerprints, titles, buckets, shingles = [], {}, {}, defaultdict(set), []
    duplicates = 0
    for q in records:
        text = q['text'].casefold()
        digest = hashlib.sha256(text.encode()).hexdigest()
        title = re.sub(r'\W+', ' ', clean_html(q['title']).casefold()).strip()
        words = text.split()
        grams = {zlib.crc32(' '.join(words[i:i+5]).encode()) for i in range(max(0, len(words)-4))}
        signature = sorted(grams)[:8]
        match = fingerprints.get(digest, titles.get(title) if len(title) > 15 else None)
        if match is None and len(grams) >= 10:
            candidates = set().union(*(buckets[g] for g in signature))
            for i in sorted(candidates):
                other = shingles[i]
                if len(grams & other) / max(1, len(grams | other)) >= .9:
                    match = i
                    break
        if match is not None:
            duplicates += 1
            kept[match]['labels'] = sorted(set(kept[match]['labels']) | set(q['labels']))
            kept[match].setdefault('duplicate_source_ids', []).append(q['id'])
            continue
        index = len(kept)
        fingerprints[digest] = index
        titles[title] = index
        for g in signature:
            buckets[g].add(index)
        shingles.append(grams)
        kept.append({**q, 'text_sha256': digest})
    return kept, duplicates


def prepare():
    import numpy as np
    from sklearn.preprocessing import MultiLabelBinarizer
    from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit
    manifest = json.loads((ROOT / 'data/raw/acquisition.json').read_text(encoding='utf-8'))
    rng = random.Random(SEED)
    records, original, eligible = [], 0, 0
    # Reservoir sample before splitting, independent of question difficulty or test metrics.
    for q in source_records(manifest):
        original += 1
        labels = normalize_tags(q['tags'])
        text = model_text(q['title'], q['body'])
        if labels and text:
            eligible += 1
            item = {**q, 'labels': labels, 'text': text}
            if len(records) < 20000:
                records.append(item)
            else:
                position = rng.randrange(eligible)
                if position < 20000:
                    records[position] = item
    records, removed = deduplicate(records)
    # Vocabulary is predeclared in config, never selected from test performance.
    labels = sorted(LABEL_DOMAINS)
    encoder = MultiLabelBinarizer(classes=labels)
    y = encoder.fit_transform([q['labels'] for q in records])
    indices = np.arange(len(records))
    splitter = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=.3, random_state=SEED)
    train, rest = next(splitter.split(indices, y))
    splitter = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=.5, random_state=SEED)
    val, test = next(splitter.split(rest, y[rest]))
    partitions = {'train': train, 'validation': rest[val], 'test': rest[test]}
    # Training support alone determines removal. Never drop hard test questions.
    supported = [label for j, label in enumerate(labels) if y[train, j].sum() >= 20]
    if len(supported) < 2:
        raise ValueError('Insufficient real training support; leave model unavailable')
    for q in records:
        q['labels'] = [label for label in q['labels'] if label in supported]
    PROCESSED.mkdir(parents=True, exist_ok=True)
    distribution = {}
    split_ids = {}
    for name, ids in partitions.items():
        subset = [records[i] for i in ids]
        (PROCESSED / f'{name}.json').write_text(json.dumps(subset, ensure_ascii=False), encoding='utf-8')
        distribution[name] = dict(Counter(label for q in subset for label in q['labels']))
        split_ids[name] = [q['id'] for q in subset]
        assert all(distribution[name].get(label, 0) > 0 for label in supported), f'Missing label in {name}'
    metadata = {'source': manifest, 'source_records_scanned': original,
                'downloaded_questions': manifest.get('downloaded_questions', original),
                'usable_questions': len(records), 'duplicates_removed': removed, 'labels': supported,
                'split_sizes': {k: len(v) for k, v in partitions.items()}, 'label_distribution': distribution,
                'split_ids': split_ids, 'seed': SEED,
                'licenses': dict(Counter(q['license'] for q in records))}
    (PROCESSED / 'dataset_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    from .config import ARTIFACTS
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / 'split_ids.json').write_text(json.dumps(split_ids, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in metadata.items() if k not in ('source', 'split_ids')}, indent=2))


if __name__ == '__main__':
    prepare()
