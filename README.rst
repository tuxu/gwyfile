gwyfile
=======

A pure Python interface to reading and writing `Gwyddion
<http://www.gwyddion.net>`_ files.


Installation
------------

.. code-block:: console

    $ pip install gwyfile


Usage
-----

At the heart of this module is the `GwyObject` class, derived from
`collections.OrderedDict`. Gwyddion files are just serialized copies of
`GwyObject`\ s and its subclasses (`GwyContainer`, `GwyDataField`, ...).

Here is a simple example that shows how to load a file and display a data
channel:

.. code-block:: python

    import gwyfile

    # Load a Gwyddion file into memory
    obj = gwyfile.load('test.gwy')
    # Return a dictionary with the datafield titles as keys and the
    # datafield objects as values.
    channels = gwyfile.util.get_datafields(obj)
    channel = channels['Test']
    # Datafield objects have a `data` property to access their
    # two-dimensional data as numpy arrays.
    data = channel.data

    # Plot the data using matplotlib.
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.imshow(data, interpolation='none', origin='upper',
            extent=(0, channel.xreal, 0, channel.yreal))
    plt.show()

It is also possible to manipulate and save objects:

.. code-block:: python

    import numpy as np
    from gwyfile.objects import GwyContainer, GwyDataField
    obj = GwyContainer()
    obj['/0/data/title'] = 'Noise'
    data = np.random.normal(size=(256, 256))
    obj['/0/data'] = GwyDataField(data)
    obj.tofile('noise.gwy')

The Gwyddion manual has a nice `description of the file format
<http://gwyddion.net/documentation/user-guide-en/gwyfile-format.html>`_. See
there for further information on object properties.


Status
------

`GwyObject` serialization and deserialization should be complete. There
are specialized subclasses for `GwyDataField` and `GwySIUnit`, but other
convenience wrappers e.g. for `GwyBrick` are missing.


License
-------

This project is licensed under the MIT license. See `LICENSE.rst <LICENSE.rst>`_
for details.

© 2014-17 `Tino Wagner <http://www.tinowagner.com/>`_
