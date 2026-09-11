SELECT 
    action_date,
    recipient_name,
    ticker,
    amount,
    agency,
    COALESCE(description, 'No contract description provided.') AS description,
    CASE 
        WHEN amount >= 1000000 THEN CONCAT('$', ROUND(amount / 1000000, 2), 'M')
        WHEN amount >= 1000 THEN CONCAT('$', ROUND(amount / 1000, 2), 'K')
        ELSE CONCAT('$', ROUND(amount, 2))
    END AS formatted_amount
FROM 
    `datascience-projects.gcp_shareloader.contract_signals`
WHERE 
    ticker = @ticker
    -- Cutoff at analysis date
    AND action_date <= SAFE_CAST(@analysis_date AS DATE)
    -- Enforce 90-day lookback window prior to analysis_date
    AND action_date >= DATE_SUB(SAFE_CAST(@analysis_date AS DATE), INTERVAL 90 DAY)
    AND amount IS NOT NULL
ORDER BY 
    action_date DESC, 
    amount DESC
LIMIT 10;