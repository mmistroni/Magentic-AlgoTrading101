DECLARE query_anchor TIMESTAMP;

-- If a reference parameter is passed, use it; otherwise default to current time
SET query_anchor = COALESCE(@reference_date, CURRENT_TIMESTAMP());

WITH public_clinical_failures AS (
  SELECT 
    c.scraped_at AS failure_post_date,
    c.nct_id,
    c.sponsor,
    -- Pull the mapped ticker and CUSIP directly
    m.ticker,
    m.cusip,
    c.title AS trial_title,
    c.status AS failure_status,
    c.negative_reason AS failure_reason
  FROM `datascience-projects.gcp_shareloader.biotech_catalysts` c
  INNER JOIN `datascience-projects.gcp_shareloader.map_cusip_ticker` m
    -- Strip punctuation and match the sponsor string against the company description
    ON REGEXP_REPLACE(LOWER(c.sponsor), r'[^a-z0-9]', '') LIKE CONCAT('%', REGEXP_REPLACE(LOWER(m.description), r'[^a-z0-9]', ''), '%')
    OR REGEXP_REPLACE(LOWER(m.description), r'[^a-z0-9]', '') LIKE CONCAT('%', REGEXP_REPLACE(LOWER(c.sponsor), r'[^a-z0-9]', ''), '%')
  WHERE c.status IN ('TERMINATED', 'SUSPENDED', 'WITHDRAWN')
    -- BOUNDARY CONDITION: Use the dynamic anchor instead of CURRENT_TIMESTAMP()
    AND c.scraped_at >= TIMESTAMP_SUB(query_anchor, INTERVAL 5 DAY)
    AND c.scraped_at <= query_anchor
)
SELECT 
  ticker,
  cusip,
  sponsor,
  failure_status,
  failure_post_date,
  nct_id,
  trial_title,
  failure_reason
FROM public_clinical_failures
ORDER BY failure_post_date DESC;