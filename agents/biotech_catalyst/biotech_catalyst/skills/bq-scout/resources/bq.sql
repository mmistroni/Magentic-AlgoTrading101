SELECT
    scraped_at,
    nct_id,
    sponsor,
    title,
    status,
    negative_reason
FROM
    `datascience-projects.gcp_shareloader.biotech_catalysts`
WHERE
    status IN ('TERMINATED', 'SUSPENDED')
    -- Safe 3-day lookback window to prevent missing data if a daily run fails
    AND scraped_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
ORDER BY
    scraped_at DESC;