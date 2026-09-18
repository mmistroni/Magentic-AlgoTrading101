WITH raw_insider AS (
  SELECT 
    ticker,
    issuer,
    owner_name AS insider_name,
    officer_title,
    is_officer,
    is_director,
    transaction_side, -- 'BUY' or 'SELL'
    shares,
    price,
    COALESCE(total_value, ROUND(shares * price, 2)) AS transaction_value,
    filing_date
  FROM `datascience-projects.gcp_shareloader.form4_master`
  WHERE filing_date >= DATE_SUB(@eval_date, INTERVAL @lookback_days DAY)
    AND (@ticker IS NULL OR ticker = @ticker)
),
aggregated_insider AS (
  SELECT 
    ticker,
    MAX(issuer) AS issuer,
    
    -- Net Buy Value: BUY total value minus SELL total value
    SUM(CASE WHEN transaction_side = 'BUY' THEN transaction_value ELSE 0 END) -
    SUM(CASE WHEN transaction_side = 'SELL' THEN transaction_value ELSE 0 END) AS net_buy_value,
    
    -- Distinct Buyers
    COUNT(DISTINCT CASE WHEN transaction_side = 'BUY' THEN insider_name END) AS unique_buyers,
    
    -- High-Conviction C-Suite Flag
    MAX(CASE 
      WHEN transaction_side = 'BUY' AND (
        is_officer = TRUE OR 
        LOWER(officer_title) LIKE '%ceo%' OR 
        LOWER(officer_title) LIKE '%chief executive%' OR 
        LOWER(officer_title) LIKE '%cfo%' OR 
        LOWER(officer_title) LIKE '%chief financial%'
      ) THEN 1 ELSE 0 
    END) AS is_c_suite_buy,

    -- Trade counts
    COUNTIF(transaction_side = 'BUY') AS buy_count,
    COUNTIF(transaction_side = 'SELL') AS sell_count
  FROM raw_insider
  GROUP BY ticker
)
SELECT 
  ticker,
  issuer,
  net_buy_value,
  unique_buyers,
  is_c_suite_buy,
  buy_count,
  sell_count,
  CASE WHEN unique_buyers >= 3 THEN TRUE ELSE FALSE END AS is_cluster_buy,
  ROUND(
    (net_buy_value / 100000) + 
    (unique_buyers * 10) + 
    (is_c_suite_buy * 20)
  ) AS insider_activity_score
FROM aggregated_insider
WHERE net_buy_value > 0
ORDER BY insider_activity_score DESC;