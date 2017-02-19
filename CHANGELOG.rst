Change Log
##########

0.2.0
=====

Added
-----

* Properties `data`, `xreal`, `yreal`, ... to `GwyDataField`.
* `GwyContainer` subclass.
* Docstrings for `gwyfile.objects`.
* `gwyfile.load` convenience method for loading files.

Changed
-------

* Removed imports of classes from `gwyfile.objects` to `gwyfile`.
* Removed `GwyDataField.get_data()`. Dropped in favor of properties.
* `GwyObject.fromfile` and `GwyObject.tofile` now also take file-like objects.

0.1.0
=====

* Initial version with basic functionality. No public release.
