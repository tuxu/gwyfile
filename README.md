gwyfile
-------

A pure Python interface to reading and writing Gwyddion files.

At the heart of this module is the `GwyObject` class, derived from a
`collections.OrderedDict`. Gwyddion files are just serialized copies of
`GwyObject`s.
