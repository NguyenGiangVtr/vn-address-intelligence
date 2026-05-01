- [x] Review numeric logger statements in `app/ai/production_pipeline.py`
- [x] Apply formatted-number logging (`:,`) for all numeric values in log messages
- [x] Verify consistency of number formatting across log lines

- [x] Update NER loading flow to avoid loading `vinai/phobert-base` for token-classification when fine-tuned model is missing
- [x] Improve NER logging message to clarify fallback behavior (Regex fallback, not model error)
- [x] Update pipeline initialization to pass only local fine-tuned path (or force fallback)
- [x] Mark completion after quick consistency review
