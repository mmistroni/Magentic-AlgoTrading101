INSERT INTO `{table_ref}` (
    decision_id, 
    ticker, 
    decision_timestamp, 
    action, 
    conviction_score, 
    entry_price, 
    decision_snapshot
)
VALUES (
    @decision_id, 
    @ticker, 
    CAST(@decision_timestamp AS TIMESTAMP), 
    @action, 
    @conviction_score, 
    @entry_price, 
    PARSE_JSON(@decision_snapshot_json)
);