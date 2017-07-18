import shelve
import os


def all_files_exist(*f):
    """True when all files in the list exist on disk

    Args:
        *f:

    Returns:

    """
    for file in f:
        if not os.path.isfile(file):
            return False
    return True
