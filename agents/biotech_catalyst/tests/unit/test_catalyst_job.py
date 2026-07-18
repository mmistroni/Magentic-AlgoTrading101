import datetime
import pytest
import httpx

# Absolute import matching your structural update
from agents.short_selling_agent.catalyst_job.catalyst_download import ClinicalCatalyst, ClinicalTrialsClient

@pytest.fixture
def mock_ticker_map():
    return {
        "novocure ltd": "NVCR",
        "pfizer inc": "PFE"
    }

def test_true():
    """A simple test to ensure the testing framework is functioning correctly."""
    assert True
    
def test_pydantic_date_parsing():
    """Verify that YYYY-MM string dates are parsed correctly into datetime.date objects."""
    catalyst = ClinicalCatalyst(
        nct_id="NCT12345678",
        ticker="NVCR",
        sponsor_name="NovoCure Ltd",
        primary_completion_date="2026-06",
        phase="PHASE3",
        condition_targeted="Glioblastoma"
    )
    assert catalyst.primary_completion_date == datetime.date(2026, 6, 1)

@pytest.mark.asyncio
async def test_client_filters_unmapped_tickers(mock_ticker_map, respx_mock):
    """Ensure that sponsors not matching the SEC ticker registry are safely ignored."""
    mock_payload = {
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT99999"},
                    "statusModule": {"primaryCompletionDateStruct": {"date": "2026-08"}},
                    "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Pfizer Inc"}},
                    "conditionsModule": {"conditions": ["Oncology"]}
                }
            },
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT00000"},
                    "statusModule": {"primaryCompletionDateStruct": {"date": "2027-01"}},
                    "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Private Venture Group"}},
                    "conditionsModule": {"conditions": ["Cardiology"]}
                }
            }
        ]
    }
    
    # Intercepting live network requests via respx
    respx_mock.get("https://clinicaltrials.gov/api/v2/studies").mock(
        return_value=httpx.Response(200, json=mock_payload)
    )
    
    client = ClinicalTrialsClient(ticker_map=mock_ticker_map)
    results = await client.fetch_phase3_catalysts()
    
    # Assertions
    assert len(results) == 1
    assert results[0].ticker == "PFE"
    assert results[0].nct_id == "NCT99999"
