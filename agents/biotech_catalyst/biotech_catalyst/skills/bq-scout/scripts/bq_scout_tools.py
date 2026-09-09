from typing import List
from typing import List, Optional
from google.cloud import bigquery
import logging
import os
import sys

logger = logging.getLogger(__name__)


# Dynamically resolve and add the correct directory containing schemas.py to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up from scripts/ -> bq-scout/ -> skills/ -> biotech_catalyst/
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from schemas import ClinicalSignalRecord
from typing import List, Optional
from google.cloud import bigquery

def load_sql_query() -> str:
    """Reads the SQL query from the resources/bq.sql directory relative to this script."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(current_dir, "resources", "bq.sql")
    with open(sql_path, "r") as f:
        return f.read()



def fetch_clinical_signals(reference_date: Optional[str] = None) -> List[ClinicalSignalRecord]:
    """
    Queries BigQuery using the SQL template stored in resources/bq.sql 
    and returns a list of validated ClinicalSignalRecord objects.
    """
    client = bigquery.Client()
    raw_query = load_sql_query()
    
    job_config = None
    if reference_date:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("reference_date", "TIMESTAMP", reference_date)
            ]
        )
    
    # Debug logging for query text and parameters
    logger.info("Executing BigQuery query with reference_date: %s", reference_date)
    logger.debug("Full SQL Query Text:\n%s", raw_query)
    
    query_job = client.query(raw_query, job_config=job_config)
    results = query_job.result()
    
    records = []
    for row in results:
        record = ClinicalSignalRecord(
            ticker=row.ticker,
            cusip=row.cusip,
            sponsor=row.sponsor,
            failure_status=row.failure_status,
            failure_post_date=row.failure_post_date,
            nct_id=row.nct_id,
            trial_title=row.trial_title,
            failure_reason=row.failure_reason
        )
        records.append(record)
        
    return records