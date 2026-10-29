SELECT 
    decision_id,
    ticker,
    decision_timestamp,
    action,
    conviction_score,
    entry_price,
    decision_snapshot_json  -- <-- Updated from decision_snapshot
FROM `{table_ref}`
WHERE ticker = @ticker
  AND conviction_score >= @min_conviction
ORDER BY decision_timestamp DESC
LIMIT @limit;