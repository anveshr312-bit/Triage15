# Fifteen-minute technical preparation

1. **Minutes 0–2 — Dataset:** Read data/DATASET_CARD.md. Say: 3,123 real API questions, 2,675 usable; 1,872/399/404 split. Explain attribution and recent tag-query bias.
2. **Minutes 2–3 — Supervised learning:** Text is input, human tags are multi-label targets. Metadata and answers never become features.
3. **Minutes 3–5 — TF-IDF:** Explain informative unigrams/bigrams, sparse vectors, and fitting vocabulary/IDF on training only. Open ml/train.py.
4. **Minutes 5–7 — Model competition:** Each label has a binary classifier. LR uses z=b+w*x and sigmoid; SVM uses the same additive margin but a different loss. SVM won measured validation; do not call its margin confidence or probability.
5. **Minutes 7–9 — Contributions:** Demonstrate Suggest Skills, expand numerical contributions, and show intercept + displayed terms + omitted terms = margin. Weights are associations, not causes.
6. **Minutes 9–11 — Metrics:** Explain precision versus recall, micro versus macro F1, coverage, exact match, and P@3. State test micro F1 .8736 and joins F1 .6667; don't hide weak labels.
7. **Minutes 11–13 — Hybrid workflow:** Accept/remove/add tags; only the confirmed form reaches existing eligibility and Hungarian optimization. Open the ML evaluation tab and separate real question fields from simulated allocation fields.
8. **Minutes 13–15 — Limitations and fallback:** Explain eight-label coverage, domain shift, no calibration/mentoring-success claim, offline CPU inference, ML_ENABLED=false, and manual fallback. Use ML_JUDGE_QA.md for follow-ups.
