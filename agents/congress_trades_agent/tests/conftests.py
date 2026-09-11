# conftest.py
import sys
from pathlib import Path

# Locate the root project directory
root_dir = Path(__file__).resolve().parent

# Add congress-researcher scripts directory to sys.path
congress_researcher_scripts = (
    root_dir / "congress_trades_agent" / "skills" / "congress-researcher" / "scripts"
)
if congress_researcher_scripts.exists() and str(congress_researcher_scripts) not in sys.path:
    sys.path.append(str(congress_researcher_scripts))

# Add insider-analyst scripts directory to sys.path (for upcoming insider_analyst tests)
insider_analyst_scripts = (
    root_dir / "congress_trades_agent" / "skills" / "insider-analyst" / "scripts"
)
if insider_analyst_scripts.exists() and str(insider_analyst_scripts) not in sys.path:
    sys.path.append(str(insider_analyst_scripts))