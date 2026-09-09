import sys
from pathlib import Path

# Automatically locate and register the hyphenated skill path into sys.modules
# so Python can resolve 'bq_scout' cleanly without importlib boilerplate.
current_dir = Path(__file__).resolve().parent
skills_dir = current_dir.parent / "skills" / "bq-scout" / "scripts"

if str(skills_dir) not in sys.path:
    sys.path.append(str(skills_dir))

# Now you can import your script directly and normally in your tests!
import bq_scout_tools