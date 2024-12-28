VERSION = (0, 19, 2)
VERSION_STRING = '.'.join(str(x) for x in VERSION)
VERSION_DATE = '2024-12-28'

def get_version():
    """Returns the version string"""
    return VERSION_STRING

def get_version_with_date():
    """Returns the version string with date"""
    return f"V. {VERSION_STRING} [{VERSION_DATE}]"
