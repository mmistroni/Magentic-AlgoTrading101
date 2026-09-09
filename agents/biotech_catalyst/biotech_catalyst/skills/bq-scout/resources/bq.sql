WITH public_clinical_failures AS (
  SELECT 
    c.scraped_at AS failure_post_date,
    c.nct_id,
    c.sponsor,
    m.ticker,
    m.cusip,
    c.title AS trial_title,
    c.status AS failure_status,
    c.negative_reason AS failure_reason
  FROM `datascience-projects.gcp_shareloader.biotech_catalysts` c
  INNER JOIN `datascience-projects.gcp_shareloader.map_cusip_ticker` m
    ON REGEXP_REPLACE(LOWER(c.sponsor), r'[^a-z0-9]', '') LIKE CONCAT('%', REGEXP_REPLACE(LOWER(m.description), r'[^a-z0-9]', ''), '%')
    OR REGEXP_REPLACE(LOWER(m.description), r'[^a-z0-9]', '') LIKE CONCAT('%', REGEXP_REPLACE(LOWER(c.sponsor), r'[^a-z0-9]', ''), '%')
  WHERE c.status IN ('TERMINATED', 'SUSPENDED', 'WITHDRAWN')
    -- Directly filter using a parameter with a fallback expression
    AND c.scraped_at >= TIMESTAMP_SUB(COALESCE(@reference_date, CURRENT_TIMESTAMP()), INTERVAL 5 DAY)
    AND c.scraped_at <= COALESCE(@reference_date, CURRENT_TIMESTAMP())
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