SELECT 
    ticker,
    action_date,
    agency,
    recipient_name,
    amount,
    COALESCE(description, 'No contract description provided.') AS description,
    -- Pre-format amount for easy consumption by LLM prompts
    CASE 
        WHEN amount >= 1000000 THEN CONCAT('$', ROUND(amount / 1000000, 2), 'M')
        WHEN amount >= 1000 THEN CONCAT('$', ROUND(amount / 1000, 2), 'K')
        ELSE CONCAT('$', ROUND(amount, 2))
    END AS formatted_amount
FROM 
    `datascience-projects.gcp_shareloader.contract_signals`
WHERE 
    ticker = @ticker
    AND action_date <= SAFE_CAST(@analysis_date AS DATE)
    AND amount IS NOT NULL
ORDER BY 
    action_date DESC, 
    amount DESC
LIMIT @limit_count;