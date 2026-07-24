-- skills/CongressResearcher/references/fetch_net_buy_signals.sql

DECLARE run_date DATE DEFAULT PARSE_DATE('%Y-%m-%d', @analysis_date);

WITH clean_data AS (
    SELECT
        AS_OF_DATE AS trade_date,
        CASE
            WHEN DISCLOSURE LIKE '%Purchase%' THEN 'Buy'
            WHEN DISCLOSURE LIKE '%Sale%' THEN 'Sell'
            ELSE 'Other'
        END AS action,
        TRIM(REPLACE(TICKER, 'Ticker:', '')) AS ticker
    FROM `datascience-projects.gcp_shareloader.senate_disclosures`
    WHERE
        TICKER IS NOT NULL
        AND AS_OF_DATE IS NOT NULL
        AND AS_OF_DATE >= DATE_SUB(run_date, INTERVAL 90 DAY)
        AND AS_OF_DATE <= run_date
)

SELECT
    run_date AS signal_date,
    ticker,
    COUNTIF(action = 'Buy') AS purchase_count,
    COUNTIF(action = 'Sell') AS sale_count,
    (COUNTIF(action = 'Buy') - COUNTIF(action = 'Sell')) AS net_buy_activity,
    COUNT(DISTINCT CASE WHEN action='Buy' THEN trade_date END) as buying_days_count,
    MAX(trade_date) AS last_trade_date
FROM clean_data
WHERE
    LOWER(ticker) NOT IN (
        'vti', 'spy', 'voo', 'qqq', 'ivv', 'spxl', 'spxs',
        'tqqq', 'sqqq', 'dia', 'iwm', 'dow', 'shv', 'bnd'
    )
    AND TRIM(ticker) != ''
    AND ticker IS NOT NULL
    AND LENGTH(ticker) <= 4 
    AND NOT REGEXP_CONTAINS(ticker, r'[^a-zA-Z]') 
GROUP BY ticker, run_date
HAVING
    buying_days_count >= 2
    AND net_buy_activity >= 5
    AND last_trade_date >= DATE_SUB(run_date, INTERVAL 90 DAY)
    AND (
        COUNTIF(action = 'Sell') = 0
        OR (COUNTIF(action = 'Buy') * 1.0 / GREATEST(COUNTIF(action = 'Sell'), 1)) >= 2.0
    )
ORDER BY buying_days_count DESC, net_buy_activity DESC
LIMIT 10;