WITH current_period AS (
  SELECT 
    ticker,
    client_name,
    STRING_AGG(DISTINCT general_issues, ', ') AS key_issues,
    SUM(amount) AS current_spend
  FROM `datascience-projects.gcp_shareloader.lobbying_signals`
  WHERE filing_date BETWEEN DATE_SUB(PARSE_DATE('%Y-%m-%d', @analysis_date), INTERVAL @lookback_days DAY) 
                        AND PARSE_DATE('%Y-%m-%d', @analysis_date)
    AND (@ticker IS NULL OR ticker = @ticker)
  GROUP BY ticker, client_name
),
prior_period AS (
  SELECT 
    ticker,
    SUM(amount) AS prior_spend
  FROM `datascience-projects.gcp_shareloader.lobbying_signals`
  WHERE filing_date BETWEEN DATE_SUB(PARSE_DATE('%Y-%m-%d', @analysis_date), INTERVAL (@lookback_days * 2) DAY) 
                        AND DATE_SUB(PARSE_DATE('%Y-%m-%d', @analysis_date), INTERVAL @lookback_days DAY)
    AND (@ticker IS NULL OR ticker = @ticker)
  GROUP BY ticker
)
SELECT 
  c.ticker,
  c.client_name,
  c.key_issues,
  c.current_spend,
  COALESCE(p.prior_spend, 0) AS prior_spend,
  ROUND(
    CASE 
      WHEN COALESCE(p.prior_spend, 0) = 0 THEN 100.0
      ELSE ((c.current_spend - p.prior_spend) / p.prior_spend) * 100.0
    END, 2
  ) AS spend_growth_pct
FROM current_period c
LEFT JOIN prior_period p ON c.ticker = p.ticker
WHERE c.current_spend > 0
ORDER BY c.current_spend DESC
LIMIT 10;