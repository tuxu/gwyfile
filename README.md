gwyfile
=======

- Author: Tino Wagner <ich@tinowagner.com>

A pure Python interface to reading and writing [Gwyddion][gwyddion] files.


Usage
-----

At the heart of this module is the `GwyObject` class, derived from
`collections.OrderedDict`. Gwyddion files are just serialized copies of
`GwyObject`s.

Here is a simple example that shows how to load a file and display a data
channel:

```python
import gwyfile

# Load a Gwyddion file into memory
obj = gwyfile.GwyObject.fromfile('test.gwy')
# Return a dictionary with the datafield titles as keys and the
# datafield objects as values.
channels = gwyfile.util.get_datafields(obj)
channel = channels['Test']
# Datafield objects have an `get_data()` method to access their
# two-dimensional data as numpy arrays.
data = channel.get_data()

# Plot the data using matplotlib.
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.imshow(data, interpolation='none', origin='upper',
          extent=(0, channel['xreal'], 0, channel['yreal']))
plt.show()
```

The Gwyddion manual has a nice [description of the file format][gwyddion-file].
See there for further information on object properties.


Status
------

`GwyObject` serialization and deserialization should be complete. There
are specialized subclasses for `GwyDataField` and `GwySIUnit`, but other
convenience wrappers e.g. for `GwyBrick` are missing.


[gwyddion]: http://www.gwyddion.net
[gwyddion-file]: http://gwyddion.net/documentation/user-guide-en/gwyfile-format.html
