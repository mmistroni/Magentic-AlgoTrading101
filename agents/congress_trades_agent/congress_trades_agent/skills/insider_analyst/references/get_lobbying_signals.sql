SELECT 
  filing_date,
  registrant_name,
  client_name,
  ticker,
  general_issues,
  amount,
  --timestamp_inserted
FROM 
  `datascience-projects.gcp_shareloader.lobbying_signals`
--WHERE 
  -- Looks at rows inserted or updated in the last 7 days
  --filing_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY 
  filing_date DESC