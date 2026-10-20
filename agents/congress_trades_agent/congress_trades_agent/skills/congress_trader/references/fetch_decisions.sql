SELECT decision_snapshot, entry_price, decision_timestamp, ticker
FROM `{table_ref}`
WHERE 1=1
  AND (@ticker IS NULL OR ticker = @ticker)
  AND (@val_verdict IS NULL OR JSON_VALUE(decision_snapshot, '$.fundamentals.valuation_verdict') = @val_verdict)
  AND (@min_conviction IS NULL OR CAST(JSON_VALUE(decision_snapshot, '$.conviction_score') AS FLOAT64) >= @min_conviction)
ORDER BY decision_timestamp DESC
LIMIT @limit;