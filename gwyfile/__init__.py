from . import objects
from . import util

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


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
