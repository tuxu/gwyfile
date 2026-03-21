from . import objects
from . import util

__version__ = __import__("importlib.metadata", fromlist=["version"]).version("gwyfile")


def load(file_or_filename):
    """Load a Gwyddion object or container from a `.gwy` file.

    Parameters
    ----------
    file_or_filename : file or str
        File object or filename.

    Returns
    -------
    result : gwyfile.objects.GwyObject
        Gwyddion object or container with the data stored in the file.
    """
    return objects.GwyObject.fromfile(file_or_filename)
