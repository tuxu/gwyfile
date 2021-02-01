gwyfile
=======

.. image:: https://img.shields.io/pypi/v/gwyfile.svg
    :target: https://pypi.python.org/pypi/gwyfile

.. image:: https://img.shields.io/pypi/l/gwyfile.svg
    :target: https://pypi.python.org/pypi/gwyfile

.. image:: https://img.shields.io/pypi/wheel/gwyfile.svg
    :target: https://pypi.python.org/pypi/gwyfile

.. image:: https://img.shields.io/pypi/pyversions/gwyfile.svg
    :target: https://pypi.python.org/pypi/gwyfile

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


Create a XYZ surface field:

.. code-block:: python

    import numpy as np
    from gwyfile.objects import GwyContainer, GwyDataField, GwySurface
    data = np.random.normal(size=(256, 256))  # test data
    coord0 = np.linspace(0.1, 0.2, data.shape[1])  # test coordinates, in physical space
    coord1 = np.linspace(0.1, 0.2, data.shape[0])

    # encode data to x,y,z triplets
    xyz_data = np.array([x for j in range(data.shape[1]) 
                            for i in range(data.shape[0]) 
                            for x in (coord0[i], coord1[j], data[j,i])]) 

    # create preview image
    img = GwyDataField(data=data, si_unit_xy='nm', si_unit_z='nm')
    img.xoff = coord0[0]
    img.xreal = coord0[-1] - coord0[0]  # lenth of measured x-coordinate
    img.yoff = coord1[0]
    img.yreal = coord1[-1] - coord1[0]  # lenth of measured y-coordinate

    # create surface object
    xyz = GwySurface(data=xyz_data, si_unit_xy='nm', si_unit_z='nm')

    # create container 
    obj = GwyContainer()    

    # image object alone 
    obj['/0/data/title'] = 'Measured height'
    obj['/0/data'] = img

    # add surface 
    # (note: 'surface' is the correct field, not 'xyz' as specified by gwyddion.net)
    obj['/surface/0/title'] = 'Measured height'
    obj['/surface/0'] = xyz
    obj['/surface/0/preview'] = img   # preview associated with xyz data
    obj['/surface/0/visible'] = True
    obj['/surface/0/meta'] = GwyContainer(data={ 'Start time': '20210105T220000',
                                                 'End time': '20210105T230500',
                                                 'Username': 'RexBarker'
                                                })
    obj.tofile('MyXYZmeasurement.gwy')



Create a GraphModel:

.. code-block:: python

    import numpy as np
    from gwyfile.objects import GwyContainer, GwyGraphModel, GwyGraphCurveModel, GwySIUnit

    # test data
    xdata = np.array([1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0])
    ydata=np.array([1.0,4.0,9.0,16.0,25.0,36.0,49.0,64.0,81.0,100.0])
    ymeas= ydata + np.random.normal(size=ydata.size)

    # multiple curves are to be created
    curves = []
    curve = GwyGraphCurveModel(xdata=xdata, ydata=ydata)
    curve['description'] = 'Theoretical data'

    # red points for theoretical data
    curve['color.red'] = 1.0   # color scales 0.0 -> 1.0
    curve['color.green'] = 0.0
    curve['color.blue'] = 0.0
    curve['type'] = 2       # solid line style  (no points)
    curve['line_style'] = 0 
    curves.append(curve)

    # a blue line for measured data  
    curve = GwyGraphCurveModel(xdata=xdata, ydata=ymeas)
    curve['description'] = 'Measured data'
    curve['color.red'] = 0.0   # color scales 0.0 -> 1.0
    curve['color.green'] = 0.0
    curve['color.blue'] = 1.0
    curve['type'] = 1       # scatter point style (no line)
    curve['line_style'] = 0 
    curves.append(curve)

    # create GraphModel object to hold curves
    graphobj = GwyGraphModel()
    graphobj['title'] = "Measurement 1, theory and measurement"
    graphobj['curves'] = curves
    graphobj['x_unit'] = GwySIUnit(unitstr='Hz')
    graphobj['y_unit'] = GwySIUnit(unitstr='c/s')
    graphobj['bottom_label'] = "TF frequency"
    graphobj['left_label'] = "Counts per second"

    # add graph model to container
    obj = GwyContainer()
    obj['/0/graph/graph/1'] = graphobj
    obj['/0/graph/graph/1/visible'] = True

    # write out
    obj.tofile('MyGraphMeasurement.gwy')

The Gwyddion manual has a nice `description of the file format
<http://gwyddion.net/documentation/user-guide-en/gwyfile-format.html>`_. See
there for further information on object properties.


Status
------

`GwyObject` serialization and deserialization should be complete. There
are specialized subclasses for `GwyDataField` and `GwySIUnit`. Current
implementation extended with GwySurface, GwyGraphModel, GwyGraphCurveModel.  
Furthermore, GwyBrick is implemented but not fully tested...no guarantees here.
Enumeration types were added, but not fully tested.


License
-------

This project is licensed under the MIT license. See `LICENSE.rst <LICENSE.rst>`_
for details.

© 2014-17 `Tino Wagner <http://www.tinowagner.com/>`_

revision 2021 `RexBarker <https://github.com/RexBarker>`_
