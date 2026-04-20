VERSION = (1, 1, 1)
VERSION_STRING = '.'.join(str(x) for x in VERSION)
VERSION_DATE = '2026-04-19'

# Data schema version 
SCHEMA_VERSION = (1, 0, 0)
SCHEMA_VERSION_STRING = '.'.join(str(x) for x in SCHEMA_VERSION)
SCHEMA_VERSION_DATE = '2026-04-17'

def get_version():
    """Returns the code version string"""
    return VERSION_STRING

def get_version_with_date():
    """Returns the code version string with date"""
    return f"V. {VERSION_STRING} [{VERSION_DATE}]"

def get_schema_version():
    """Returns the data schema version string."""
    return SCHEMA_VERSION_STRING
