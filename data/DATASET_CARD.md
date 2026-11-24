# Triage15 real-question dataset card

Actual source: **Stack Exchange API**, [official questions API](https://api.stackexchange.com/docs/questions).
Acquired: 2026-11-24T06:56:26.695741+00:00. These are real Stack Overflow questions, not generated examples.
Acquisition: `scripts/download_dataset.py::acquire`, GET /2.3/questions; cached pages; sort=creation; fixed cutoff.
The primary [StackSample dataset](https://www.kaggle.com/datasets/stackoverflow/stacksample) was attempted with kagglehub, but the package was not yet available during the bounded attempt. We immediately used the authorized API fallback. No Kaggle data was used in these results.

Downloaded unique questions: **3123**. Usable labeled questions after cleaning and deduplication: **2675**.
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
Vocabulary is predefined, and labels require >=20 training positives; no label was removed in this run. Iterative multi-label stratification uses seed 42, approximately 70/15/15: **{'train': 1872, 'validation': 399, 'test': 404}**. Discrete stratification causes small deviations from exact percentages.
Split IDs and checksum: `ml/artifacts/split_ids.json`, `model_metadata.json`. Test labels do not select models, thresholds, features, or vocabulary. TF-IDF fits training only.

| Label | App domain | Train positives | Validation positives | Test positives |
|---|---|---:|---:|---:|
| aggregation | SQL | 220 | 47 | 48 |
| async | JavaScript | 63 | 13 | 14 |
| javascript | JavaScript | 436 | 93 | 94 |
| joins | SQL | 169 | 36 | 36 |
| pandas | Python | 302 | 65 | 65 |
| python | Python | 625 | 134 | 134 |
| react | JavaScript | 290 | 62 | 62 |
| sql | SQL | 661 | 142 | 142 |


## License and attribution

Observed usable-record license metadata: `{'CC BY-SA 4.0': 2267, 'see post timeline': 408}`. Do not assume absent license fields mean public domain or CC0.
[Stack Overflow licensing policy](https://stackoverflow.com/help/licensing) specifies CC BY-SA 2.5 before April 8, 2011, CC BY-SA 3.0 until May 2, 2018, and CC BY-SA 4.0 afterward; individual revisions' licenses should be checked on their timelines. [CC BY-SA 4.0 terms](https://creativecommons.org/licenses/by-sa/4.0/) require attribution and ShareAlike when applicable.
`data/ATTRIBUTION.json` preserves each retained question URL, author/name/link where supplied, creation timestamp and reported license. Raw records preserve additional original metadata. For the 408 records lacking API license metadata, consult the linked source revision before redistribution.
Full question bodies and raw/processed datasets are not committed or shipped. Error analysis links to source questions rather than redistributing their text. Text transformations are described above; do not redistribute transformed question datasets without preserving attribution and applicable license obligations. Attribution metadata is included with the small learned artifact; do not interpret its inclusion as changing source-content licenses.

## Limitations and coverage

Queries oversample eight requested tags, and recent creation order samples different historical periods for high- and low-volume tags. This is neither a random sample of all Stack Overflow nor a campus cohort. Tags can be incomplete, noisy, or historically inconsistent; truncated bodies can lose context. Popular developer languages dominate; CAD, Design, Mathematics and many existing manual tags are unsupported by ML. No mentoring-session outcomes are present. Author metadata is used for attribution only, never model features.
