"""Gwyddion object definitions.

See <http://gwyddion.net/documentation/user-guide-en/gwyfile-format.html>
for a specification of Gwyddion native data files.

Revision 14-Jan-2021: added GwySurface 
Revision 29-Jan-2021: added GwyBrick, GwyGraphModel, GwyGraphCurveModel
"""
import struct
from collections import OrderedDict
import numpy as np

from six import BytesIO, string_types
from six.moves import range
from enum import Enum


class GwyObject(OrderedDict):
    """GwyObject.

    Parameters
    ----------
    name : str
        Type name.
    data : dict
        Dictionary of components.
    typecodes : dict
        Dictionary of component typecodes.
    """
    def __init__(self, name, data=None, typecodes=None):
        OrderedDict.__init__(self)
        self.name = name
        # For each object attribute, we (optionally) store its type
        self.typecodes = {}
        if isinstance(data, dict):
            self.update(data)
        if isinstance(typecodes, dict):
            self.typecodes.update(typecodes)

    def __str__(self):
        return '<GwyObject "{name}">({keys})'.format(
            name=self.name,
            keys=', '.join("'{}'".format(k) for k in self.keys())
        )

    @classmethod
    def frombuffer(cls, buf, return_size=False):
        """Interpret a buffer as a serialized GwyObject.

        Parameters
        ----------
        buf : buffer_like
            Buffer.
        return_size : bool
            If `True`, the size of the component within the buffer is returned as
            well.
        """
        pos = buf.find(b'\0')
        name = buf[:pos].decode('utf-8')
        size = struct.unpack('<I', buf[pos + 1:pos + 5])[0]
        object_data = buf[pos + 5:pos + 5 + size]
        buf = object_data
        data = OrderedDict()
        typecodes = {}
        while len(buf) > 0:
            (component_name, component_data, component_typecode,
             component_size) = component_from_buffer(buf, return_size=True)
            data[component_name] = component_data
            typecodes[component_name] = component_typecode
            buf = buf[component_size:]
        try:
            # Initialize corresponding Gwyddion object
            type_class = _gwyddion_types[name]
            obj = type_class(data=data, typecodes=typecodes)
        except KeyError:
            obj = GwyObject(name, data, typecodes=typecodes)
        if return_size:
            return obj, len(name) + 5 + size
        return obj

    def serialize(self):
        """Return the binary representation."""
        io = BytesIO()
        for k in self.keys():
            try:
                typecode = self.typecodes[k]
            except KeyError:
                typecode = None
            io.write(serialize_component(k, self[k], typecode))
        buf = io.getvalue()
        return b''.join([
            self.name.encode('utf-8'),
            b'\0',
            struct.pack('<I', len(buf)),
            buf
        ])

    @classmethod
    def fromfile(cls, file):
        """Create a GwyObject from the data stored in `file`.

        Parameters
        ----------
        file : file or str
            File object or filename.
        """
        if isinstance(file, string_types):
            with open(file, 'rb') as f:
                return GwyObject._read_file(f)
        return GwyObject._read_file(file)

    def tofile(self, file):
        """Write GwyObject with header to file.

        Parameters
        ----------
        file : file or str
            File object or filename.
        """
        if isinstance(file, string_types):
            with open(file, 'wb') as f:
                self._write_file(f)
        else:
            self._write_file(file)

    @classmethod
    def _read_file(cls, f):
        data = f.read()
        assert data[:4] == b'GWYP'
        return cls.frombuffer(data[4:])

    def _write_file(self, f):
        f.write(b'GWYP')
        f.write(self.serialize())


class GwyContainer(GwyObject):
    """GwyContainer.

    Parameters
    ----------
    data : dict
        Dictionary of components.
    typecodes : dict
        Dictionary of component typecodes.
    """
    def __init__(self, data=None, typecodes=None):
        super(GwyContainer, self).__init__('GwyContainer', data, typecodes)

    @property
    def filename(self):
        """Associated container filename."""
        return self.get('/filename', None)

    @filename.setter
    def filename(self, name):
        self['/filename'] = name


class GwyDataField(GwyObject):
    """GwyDataField.

    Parameters
    ----------
    data : np.ndarray, shape=(yres, xres)
        2-dimensional field data.
    xreal : float
        Width in physical units.
    yreal : float
        Height in physical units.
    xoff : float
        Horizontal offset of top-left corner in physical units.
    yoff : float
        Vertical offset of top-left corner in physical units.
    si_unit_xy : GwySIUnit
        Lateral unit.
    si_unit_z : GwySIUnit
        Data value unit.
    typecodes : dict
        Dictionary of component typecodes.
    """
    def __init__(self, data,
                 xreal=1.0, yreal=1.0, xoff=0, yoff=0,
                 si_unit_xy=None, si_unit_z=None,
                 typecodes=None):
        super(GwyDataField, self).__init__('GwyDataField', typecodes=typecodes)
        if isinstance(data, OrderedDict):
            self.update(data)
        else:
            assert isinstance(data, np.ndarray) and len(data.shape) == 2
            self.xreal, self.yreal = xreal, yreal
            self.xoff, self.yoff = xoff, yoff
            self.si_unit_xy, self.si_unit_z = si_unit_xy, si_unit_z
            self.data = data
        self.typecodes.update({
            'xres': 'i', 'yres': 'i',
            'xreal': 'd', 'yreal': 'd',
            'xoff': 'd', 'yoff': 'd',
        })

    @property
    def data(self):
        """Container data."""
        xres, yres = self['xres'], self['yres']
        return self['data'].reshape((yres, xres))

    @data.setter
    def data(self, new_data):
        assert isinstance(new_data, np.ndarray) and new_data.ndim == 2
        yres, xres = new_data.shape
        self['xres'], self['yres'] = xres, yres
        self['data'] = new_data.flatten()

    @property
    def xreal(self):
        """Width in physical units."""
        return self.get('xreal', None)

    @xreal.setter
    def xreal(self, width):
        if width is None:
            if 'xreal' in self:
                del self['xreal']
        else:
            self['xreal'] = width

    @property
    def yreal(self):
        """Height in physical units."""
        return self.get('yreal', None)

    @yreal.setter
    def yreal(self, height):
        if height is None:
            if 'yreal' in self:
                del self['yreal']
        else:
            self['yreal'] = height

    @property
    def xoff(self):
        """Horizontal offset of top-left corner in physical units."""
        return self.get('xoff', 0)

    @xoff.setter
    def xoff(self, offset):
        self['xoff'] = offset

    @property
    def yoff(self):
        """Vertical offset of top-left corner in physical units."""
        return self.get('yoff', 0)

    @yoff.setter
    def yoff(self, offset):
        self['yoff'] = offset

    @property
    def si_unit_xy(self):
        """Unit of lateral dimensions."""
        return self.get('si_unit_xy', None)

    @si_unit_xy.setter
    def si_unit_xy(self, unit):
        if unit is None:
            if 'si_unit_xy' in self:
                del self['si_unit_xy']
        elif isinstance(unit, string_types):
            self['si_unit_xy'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_xy'] = unit

    @property
    def si_unit_z(self):
        """Unit of data values."""
        return self.get('si_unit_z', None)

    @si_unit_z.setter
    def si_unit_z(self, unit):
        if unit is None:
            if 'si_unit_z' in self:
                del self['si_unit_z']
        elif isinstance(unit, string_types):
            self['si_unit_z'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_z'] = unit


class GwySurface(GwyObject):
    """GwySurface.

    Parameters
    ----------
    data : np.ndarray, shape=(zres, yres, xres)
        3-dimensional field data.
    si_unit_xy : GwySIUnit
        Lateral unit.
    si_unit_z : GwySIUnit
        Data value unit.
    typecodes : dict
        Dictionary of component typecodes.
    """
    def __init__(self, data,
                 xreal=1.0, yreal=1.0, xoff=0, yoff=0,
                 si_unit_xy=None, si_unit_z=None,
                 typecodes=None):
        super(GwySurface, self).__init__('GwySurface', typecodes=typecodes)
        if isinstance(data, OrderedDict):
            self.update(data)
        else:
            assert isinstance(data, np.ndarray)
            self.si_unit_xy, self.si_unit_z = si_unit_xy, si_unit_z
            self.data = data

    @property
    def data(self):
        """Container data."""
        return self['data']

    @data.setter
    def data(self, new_data):
        assert isinstance(new_data, np.ndarray)
        self['data'] = new_data.flatten()

    @property
    def si_unit_xy(self):
        """Unit of lateral dimensions."""
        return self.get('si_unit_xy', None)

    @si_unit_xy.setter
    def si_unit_xy(self, unit):
        if unit is None:
            if 'si_unit_xy' in self:
                del self['si_unit_xy']
        elif isinstance(unit, string_types):
            self['si_unit_xy'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_xy'] = unit

    @property
    def si_unit_z(self):
        """Unit of data values."""
        return self.get('si_unit_z', None)

    @si_unit_z.setter
    def si_unit_z(self, unit):
        if unit is None:
            if 'si_unit_z' in self:
                del self['si_unit_z']
        elif isinstance(unit, string_types):
            self['si_unit_z'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_z'] = unit


class GwyBrick(GwyObject):
    """GwyBrick.

    Parameters
    ----------
    data : np.ndarray, shape=(zres, yres, xres)
        3-dimensional field data.
    si_unit_ : GwySIUnit
        Lateral unit.
    si_unit_y : GwySIUnit
        Longitudinal unit.
    si_unit_z : GwySIUnit
        Data value unit.
    typecodes : dict
        Dictionary of component typecodes.
    """
    def __init__(self, data,
                 xres=None, yres=None, zres=None,
                 xreal=None, yreal=None, zreal=None,
                 xoff=None, yoff=None, zoff=None,
                 si_unit_x=None, si_unit_y=None, 
                 si_unit_z=None, si_unit_w=None,
                 typecodes=None):
        super(GwyBrick, self).__init__('GwyBrick', typecodes=typecodes)
        if isinstance(data, OrderedDict):
            self.update(data)
        else:
            assert isinstance(data, np.ndarray)
            self.xres, self.yres, self.zres = xres, yres, zres
            self.xreal, self.yreal, self.zreal = xreal, yreal, zreal 
            self.xoff, self.yoff, self.zoff = xoff, yoff, zoff 
            self.si_unit_x = si_unit_x
            self.si_unit_y = si_unit_y
            self.si_unit_z = si_unit_z
            self.si_unit_w = si_unit_w
            self.data = data
        self.typecodes.update({
            'xres': 'i', 'yres': 'i', 'zres': 'i',
            'xreal': 'd', 'yreal': 'd', 'zreal': 'd',
            'xoff': 'd', 'yoff': 'd', 'zoff': 'd'
        })

    @property
    def data(self):
        """Container data."""
        return self['data']

    @data.setter
    def data(self, new_data):
        assert isinstance(new_data, np.ndarray)
        self['data'] = new_data.flatten()
        
    @property
    def xres(self):
        """Width in physical units."""
        return self.get('xres', None)

    @xres.setter
    def xres(self, width):
        if width is None:
            if 'xres' in self:
                del self['xres']
        else:
            self['xres'] = width
            
    @property
    def yres(self):
        """Width in physical units."""
        return self.get('yres', None)

    @yres.setter
    def yres(self, width):
        if width is None:
            if 'yres' in self:
                del self['yres']
        else:
            self['yres'] = width

    @property
    def zres(self):
        """Width in physical units."""
        return self.get('zres', None)

    @zres.setter
    def zres(self, width):
        if width is None:
            if 'zres' in self:
                del self['zres']
        else:
            self['zres'] = width

    @property
    def xreal(self):
        """Width in physical units."""
        return self.get('xreal', None)

    @xreal.setter
    def xreal(self, width):
        if width is None:
            if 'xreal' in self:
                del self['xreal']
        else:
            self['xreal'] = width

    @property
    def yreal(self):
        """Height in physical units."""
        return self.get('yreal', None)

    @yreal.setter
    def yreal(self, height):
        if height is None:
            if 'yreal' in self:
                del self['yreal']
        else:
            self['yreal'] = height

    @property
    def zreal(self):
        """Depth in physical units."""
        return self.get('zreal', None)

    @zreal.setter
    def zreal(self, depth):
        if depth is None:
            if 'zreal' in self:
                del self['zreal']
        else:
            self['zreal'] = depth 

    @property
    def xoff(self):
        """Horizontal offset of top-left corner in physical units."""
        return self.get('xoff', 0)

    @xoff.setter
    def xoff(self, offset):
        self['xoff'] = offset

    @property
    def yoff(self):
        """Vertical offset of top-left corner in physical units."""
        return self.get('yoff', 0)

    @yoff.setter
    def yoff(self, offset):
        self['yoff'] = offset

    @property
    def zoff(self):
        """Value offset of top-left corner in physical units."""
        return self.get('zoff', 0)

    @zoff.setter
    def zoff(self, offset):
        self['zoff'] = offset

    @property
    def si_unit_x(self):
        """Unit of lateral dimensions."""
        return self.get('si_unit_x', None)

    @si_unit_x.setter
    def si_unit_x(self, unit):
        if unit is None:
            if 'si_unit_x' in self:
                del self['si_unit_x']
        elif isinstance(unit, string_types):
            self['si_unit_x'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_x'] = unit
            
    @property
    def si_unit_y(self):
        """Unit of longitudinal dimensions."""
        return self.get('si_unit_x', None)

    @si_unit_y.setter
    def si_unit_y(self, unit):
        if unit is None:
            if 'si_unit_y' in self:
                del self['si_unit_y']
        elif isinstance(unit, string_types):
            self['si_unit_y'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_y'] = unit

    @property
    def si_unit_z(self):
        """Unit of depth values."""
        return self.get('si_unit_z', None)

    @si_unit_z.setter
    def si_unit_z(self, unit):
        if unit is None:
            if 'si_unit_z' in self:
                del self['si_unit_z']
        elif isinstance(unit, string_types):
            self['si_unit_z'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_z'] = unit

    @property
    def si_unit_w(self):
        """Unit of measurement values."""
        return self.get('si_unit_w', None)

    @si_unit_w.setter
    def si_unit_w(self, unit):
        if unit is None:
            if 'si_unit_w' in self:
                del self['si_unit_w']
        elif isinstance(unit, string_types):
            self['si_unit_w'] = GwySIUnit(unitstr=unit)
        else:
            self['si_unit_w'] = unit



class GwyGraphModel(GwyObject):
    """GwyGraphModel.

    Parameters
    ----------
    xdata: np.ndarray, shape(xres)
        1-D data of Abscissa
    ydata: np.ndarray, shape(yres)  (note: xres=yres)
        1-D data of Ordinate 
    typecodes : dict
        Dictionary of component typecodes.
    """
    def __init__(self,data=None, 
                 x_min=None, y_min=None, 
                 x_max=None, y_max=None, 
                 x_min_set=None, y_min_set=None, 
                 x_max_set=None, y_max_set=None, 
                 x_unit=None, y_unit=None,
                 title=None,
                 top_label=None, bottom_label=None,
                 left_label=None, right_label=None,
                 typecodes=None):
        super(GwyGraphModel, self).__init__('GwyGraphModel', typecodes=typecodes)
        self.x_min, self.y_min = x_min, y_min 
        self.x_max, self.y_max = x_max, y_max 
        self.x_min_set, self.y_min_set = x_min_set, y_min_set
        self.x_max_set, self.y_max_set = x_max_set, y_max_set
        self.x_unit, self.y_unit = x_unit, y_unit 
        self.typecodes.update({
            'x_min': 'd', 'y_min': 'd',
            'x_max': 'd', 'y_max': 'd',
            'x_min_set': 'b', 'y_min_set': 'b',
            'x_max_set': 'b', 'y_max_set': 'b',
            'title': 's',
            'top_label': 's', 'bottom_label': 's',
            'left_label': 's', 'right_label': 's',
            'curves': 'O'
        })

    @property
    def x_min(self):
        return self.get('x_min', None)

    @x_min.setter
    def x_min(self, value):
        if value is None:
            if 'x_min' in self:
                del self['x_min']
        else:
            self['x_min'] = value 

    @property
    def y_min(self):
        return self.get('y_min', None)

    @y_min.setter
    def y_min(self, value):
        if value is None:
            if 'y_min' in self:
                del self['y_min']
        else:
            self['y_min'] = value 

    @property
    def x_max(self):
        return self.get('x_max', None)

    @x_max.setter
    def x_max(self, value):
        if value is None:
            if 'x_max' in self:
                del self['x_max']
        else:
            self['x_max'] = value 

    @property
    def y_max(self):
        return self.get('y_max', None)

    @y_max.setter
    def y_max(self, value):
        if value is None:
            if 'y_max' in self:
                del self['y_max']
        else:
            self['y_max'] = value 

    @property
    def x_min_set(self):
        return self.get('x_min_set', False)

    @x_min_set.setter
    def x_min_set(self, value):
        if value is None:
            if 'x_min_set' in self:
                del self['x_min_set']
        else:
            self['x_min_set'] = value 
            
    @property
    def y_min_set(self):
        return self.get('y_min_set', False)

    @y_min_set.setter
    def y_min_set(self, value):
        if value is None:
            if 'y_min_set' in self:
                del self['y_min_set']
        else:
            self['y_min_set'] = value 

    @property
    def x_max_set(self):
        return self.get('x_max_set', False)

    @x_max_set.setter
    def x_max_set(self, value):
        if value is None:
            if 'x_max_set' in self:
                del self['x_max_set']
        else:
            self['x_max_set'] = value 
            
    @property
    def y_max_set(self):
        return self.get('y_max_set', False)

    @y_max_set.setter
    def y_max_set(self, value):
        if value is None:
            if 'y_max_set' in self:
                del self['y_max_set']
        else:
            self['y_max_set'] = value 

    @property
    def x_unit(self):
        """Unit of lateral dimensions."""
        return self.get('x_unit', None)

    @x_unit.setter
    def x_unit(self, unit):
        if unit is None:
            if 'x_unit' in self:
                del self['x_unit']
        elif isinstance(unit, string_types):
            self['x_unit'] = GwySIUnit(unitstr=unit)
        else:
            self['x_unit'] = unit

    @property
    def y_unit(self):
        """Unit of data values."""
        return self.get('y_unit', None)

    @y_unit.setter
    def y_unit(self, unit):
        if unit is None:
            if 'y_unit' in self:
                del self['y_unit']
        elif isinstance(unit, string_types):
            self['y_unit'] = GwySIUnit(unitstr=unit)
        else:
            self['y_unit'] = unit

    @property
    def title(self):
        """ Graph title"""
        return self.get('title',None)

    @title.setter
    def title(self,value):
        if value is None:
            if 'title' in self:
                del self['title']
        else:
            self['title'] = value 

    @property
    def top_label(self):
        """ Graph top_label"""
        return self.get('top_label',None)

    @top_label.setter
    def top_label(self,value):
        if value is None:
            if 'top_label' in self:
                del self['top_label']
        else:
            self['top_label'] = value 

    @property
    def bottom_label(self):
        """ Graph bottom_label"""
        return self.get('bottom_label',None)

    @bottom_label.setter
    def bottom_label(self,value):
        if value is None:
            if 'bottom_label' in self:
                del self['bottom_label']
        else:
            self['bottom_label'] = value 

    @property
    def left_label(self):
        """ Graph left_label"""
        return self.get('left_label',None)

    @left_label.setter
    def left_label(self,value):
        if value is None:
            if 'left_label' in self:
                del self['left_label']
        else:
            self['left_label'] = value 

    @property
    def right_label(self):
        """ Graph right_label"""
        return self.get('right_label',None)

    @right_label.setter
    def right_label(self,value):
        if value is None:
            if 'right_label' in self:
                del self['right_label']
        else:
            self['right_label'] = value 


class GwyGraphCurveModel(GwyObject):
    """GwyGraphCurveModel.

    Parameters
    ----------
    xdata : np.ndarray, shape=(xres)
        1-dimensional field data.
    ydata : np.ndarray, shape=(yres) (yres=xres)
        1-dimensional field data.
    description : string
        Description of curve 
    type : int
        Curve mode (points, lines, etc), from GwyGraphCurveType enum
    point_type : int
        point type from GwyGraphPointType enum
    line_type : int
        point type from GwyGraphLineType enum
    line_size : int
        width of lines  
    typecodes : dict
        Dictionary of component typecodes.
    """
    def __init__(self, data=None,
                 xdata=None, ydata=None, type=None, 
                 point_type=None,  point_size=None, line_type=None, line_size=None,
                 color_red=None, color_green=None, color_blue=None,
                 typecodes=None):
        super(GwyGraphCurveModel, self).__init__('GwyGraphCurveModel', typecodes=typecodes)
        if isinstance(data, dict):
            self.update(data)

        if xdata is not None:
            assert isinstance(xdata, np.ndarray) and len(xdata.shape) == 1
            self.xdata = xdata

        if ydata is not None:
            assert isinstance(ydata, np.ndarray) and len(ydata.shape) == 1
            self.ydata = ydata

        self.point_type, self.point_size = point_type, point_size 
        self.line_type, self.line_size = line_type, line_size 
        self.typecodes.update({
            'point_type': 'i', 'point_size': 'i',
            'line_type': 'i', 'line_size': 'i'
        })

    @property
    def xdata(self):
        """Container data."""
        return self['xdata']

    @xdata.setter
    def xdata(self, new_data):
        assert isinstance(new_data, np.ndarray)
        self['xdata'] = new_data.flatten()

    @property
    def ydata(self):
        """Container data."""
        return self['ydata']

    @ydata.setter
    def ydata(self, new_data):
        assert isinstance(new_data, np.ndarray)
        self['ydata'] = new_data.flatten()

    @property
    def point_type(self):
        return self['point_type']

    @point_type.setter
    def point_type(self,ptype):
        if ptype is None:
            if 'point_type' in self:
                del self['point_type']
        elif isinstance(ptype, GwyGraphPointType):
            self['point_type'] = ptype.value
        else:
            self['point_type'] = ptype 

    @property
    def point_size(self):
        return self['point_size']

    @point_size.setter
    def point_size(self,psize):
        if psize is None:
            if 'point_size' in self:
                del self['point_size']
        else:
            self['point_size'] = psize 

    @property
    def line_type(self):
        return self['line_type']

    @line_type.setter
    def line_type(self,ltype):
        if ltype is None:
            if 'line_type' in self:
                del self['line_type']
        elif isinstance(ltype, GwyGraphLineType):
            self['line_type'] = ltype.value
        else:
            self['line_type'] = ltype 

    @property
    def line_size(self):
        return self['line_size']

    @line_size.setter
    def line_size(self,lsize):
        if lsize is None:
            if 'line_size' in self:
                del self['line_size']
        else:
            self['line_size'] = lsize 


class GwySIUnit(GwyObject):
    def __init__(self, data=None, unitstr='', typecodes=None):
        super(GwySIUnit, self).__init__('GwySIUnit', typecodes=typecodes)
        if isinstance(data, OrderedDict):
            self.update(data)
        else:
            self.typecodes['unitstr'] = 's'
            self.unitstr = unitstr

    @property
    def unitstr(self):
        return self['unitstr']

    @unitstr.setter
    def unitstr(self, s):
        self['unitstr'] = s

class GwyGraphPointType(Enum):
    """GwyGraphPointType enumerations
        according to documentation: 
         - http://gwyddion.net/documentation/libgwydgets/libgwydgets-gwydgetenums.php
        additional references from:
         - https://sourceforge.net/p/gwyddion/code/HEAD/tarball?path=/trunk/gwyddiono
         - trunk/libgwydgets/gwydgetenums.h
    """
    GWY_GRAPH_POINT_SQUARE                = 0
    GWY_GRAPH_POINT_CROSS                 = 1
    GWY_GRAPH_POINT_CIRCLE                = 2
    GWY_GRAPH_POINT_STAR                  = 3
    GWY_GRAPH_POINT_TIMES                 = 4
    GWY_GRAPH_POINT_TRIANGLE_UP           = 5
    GWY_GRAPH_POINT_TRIANGLE_DOWN         = 6
    GWY_GRAPH_POINT_DIAMOND               = 7
    GWY_GRAPH_POINT_FILLED_SQUARE         = 8
    GWY_GRAPH_POINT_DISC                  = 9
    GWY_GRAPH_POINT_FILLED_CIRCLE         = GWY_GRAPH_POINT_DISC
    GWY_GRAPH_POINT_FILLED_TRIANGLE_UP    = 10
    GWY_GRAPH_POINT_FILLED_TRIANGLE_DOWN  = 11
    GWY_GRAPH_POINT_FILLED_DIAMOND        = 12
    GWY_GRAPH_POINT_TRIANGLE_LEFT         = 13
    GWY_GRAPH_POINT_FILLED_TRIANGLE_LEFT  = 14
    GWY_GRAPH_POINT_TRIANGLE_RIGHT        = 15
    GWY_GRAPH_POINT_FILLED_TRIANGLE_RIGHT = 16
    GWY_GRAPH_POINT_ASTERISK              = 17

class GwyGraphLineType(Enum):
    """GwyGraphLineType enumerations
        not actually defined in documentation: 
         - http://gwyddion.net/documentation/libgwydgets/libgwydgets-gwydgetenums.php
        or in the repo
         - https://sourceforge.net/p/gwyddion/code/HEAD/tarball?path=/trunk/gwyddiono
        so this is back-extrapolated by experiment, could have other values
    """
    GWY_LINE_TYPE_HIDDEN = 0 
    GWY_LINE_TYPE_POINTS = 1
    GWY_LINE_TYPE_LINE = 2


class GwyGraphCurveType(Enum):
    """GwyCurveType enumerations
        according to documentation: 
         - http://gwyddion.net/documentation/libgwydgets/libgwydgets-gwydgetenums.php
        additional references from:
         - https://sourceforge.net/p/gwyddion/code/HEAD/tarball?path=/trunk/gwyddiono
         - trunk/libgwydgets/gwydgetenums.h
    """
    GWY_GRAPH_CURVE_HIDDEN      = 0
    GWY_GRAPH_CURVE_POINTS      = 1
    GWY_GRAPH_CURVE_LINE        = 2
    GWY_GRAPH_CURVE_LINE_POINTS = 3


class GwyCurveType(Enum):
    """GwyCurveType enumerations
        according to documentation: 
         - http://gwyddion.net/documentation/libgwydgets/libgwydgets-gwydgetenums.php
        additional references from:
         - https://sourceforge.net/p/gwyddion/code/HEAD/tarball?path=/trunk/gwyddiono
         - trunk/libgwydgets/gwydgetenums.h
    """
    GWY_CURVE_TYPE_LINEAR = 0 
    GWY_CURVE_TYPE_SPLINE = 1
    GWY_CURVE_TYPE_FREE = 2


def component_from_buffer(buf, return_size=False):
    """Interpret a buffer as a serialized component.

    Parameters
    ----------
    return_size : bool
        If `True`, the size of the component within the buffer is returned as
        well.
    """
    pos = buf.find(b'\0')
    name = buf[:pos].decode('utf-8')
    typecode = buf[pos+1:pos+2].decode('utf-8')
    pos += 2
    data = None
    endpos = pos
    if typecode == 'o':
        data, size = GwyObject.frombuffer(buf[pos:], return_size=True)
        endpos += size
    elif typecode == 's':
        # NUL-terminated string
        endpos = buf.find(b'\0', pos)
        data = buf[pos:endpos].decode('utf-8')
        endpos += 1
    elif typecode == 'b':
        # Boolean
        data = ord(buf[pos:pos+1]) != 0
        endpos += 1
    elif typecode == 'c':
        data = struct.unpack('<c',buf[pos:pos+1])[0].decode('utf-8')
        endpos += 1
    elif typecode == 'i':
        data = struct.unpack('<i', buf[endpos:endpos + 4])[0]
        endpos += 4
    elif typecode == 'q':
        data = struct.unpack('<q', buf[endpos:endpos + 8])[0]
        endpos += 8
    elif typecode == 'd':
        data = struct.unpack('<d', buf[endpos:endpos + 8])[0]
        endpos += 8
    elif typecode in 'CIQD':
        numitems = struct.unpack('<I', buf[pos:pos + 4])[0]
        endpos += 4
        typelookup = {
            'C': np.dtype('<S'), 'I': np.dtype('<i4'),
            'Q': np.dtype('<i8'), 'D': np.dtype('<f8')
        }
        dtype = typelookup[typecode]
        pos, endpos = endpos, endpos + dtype.itemsize * numitems
        data = np.fromstring(buf[pos:endpos], dtype=dtype)
    elif typecode == 'S':
        numitems = struct.unpack('<I', buf[pos:pos + 4])[0]
        endpos += 4
        data = []
        for _ in range(numitems):
            pos = endpos
            endpos = buf.find(b'\0', pos)
            data.append(buf[pos:endpos].decode('utf-8'))
            endpos += 1
    elif typecode == 'O':
        numitems = struct.unpack('<I', buf[pos:pos + 4])[0]
        endpos += 4
        data = []
        for _ in range(numitems):
            pos = endpos
            objdata, size = GwyObject.frombuffer(buf[pos:], return_size=True)
            data.append(objdata)
            endpos += size
    else:
        raise NotImplementedError
    if return_size:
        return name, data, typecode, endpos
    return name, data, typecode


def guess_typecode(value):
    """Guess Gwyddion typecode for `value`."""
    if np.isscalar(value) and hasattr(value, 'item'):
        # Seems to be a numpy type -- convert
        value = value.item()
    if isinstance(value, GwyObject):
        return 'o'
    elif isinstance(value, string_types):
        if len(value) == 1:
            return 'c'
        else:
            return 's'
    elif type(value) is bool:
        return 'b'
    elif type(value) is int:
        if abs(value) < 2**31:
            return 'i'
        else:
            return 'q'
    elif type(value) is float:
        return 'd'
    elif type(value) is np.ndarray:
        t = value.dtype.type
        if t == np.dtype('f8'):
            return 'D'
        elif t == np.dtype('i8'):
            return 'Q'
        elif t == np.dtype('i4'):
            return 'I'
        elif t == np.dtype('S'):
            return 'C'
        else:
            raise NotImplementedError
    elif type(value) is list:
        return 'O'
    else:
        raise NotImplementedError('{}, type: {}'.format(value,
                                                        type(value)))


def serialize_component(name, value, typecode=None):
    """Serialize `value` to a Gwyddion component.

    Parameters
    ----------
    name : str
        Component name.
    value : serializable
        Data to serialize.
    typecode : str
        Type code. If not provided, this is inferred from type(value).
    """
    if typecode is None:
        typecode = guess_typecode(value)
    if typecode == 'o':
        buf = value.serialize()
    elif typecode == 's':
        buf = b''.join([value.encode('utf-8'), b'\0'])
    elif typecode == 'c':
        buf = value.encode('utf-8')
    elif typecode == 'b':
        buf = chr(value).encode('utf-8')
    elif typecode in 'iqd':
        buf = struct.pack('<' + typecode, value)
    elif typecode in 'CIQD':
        typelookup = {
            'C': np.dtype('<S'), 'I': np.dtype('<i4'),
            'Q': np.dtype('<i8'), 'D': np.dtype('<f8')
        }
        data = value.astype(typelookup[typecode]).data
        buf = b''.join([
            struct.pack('<I', len(value)),
            memoryview(data).tobytes()
        ])
    elif typecode == 'S':
        data = [struct.pack('<I', len(value)), ]
        data += [s.encode('utf-8') + b'\0' for s in value]
        buf = b''.join(data)
    elif typecode == 'O':
        data = [struct.pack('<I', len(value)), ]
        data += [obj.serialize() for obj in value]
        buf = b''.join(data)
    else:
        raise NotImplementedError('name: {}, typecode: {}, type: {}'
                                  .format(name, typecode, type(value)))
    return b''.join([
        name.encode('utf-8'), b'\0',
        typecode.encode('utf-8'),
        buf
    ])


# Type lookup table
_gwyddion_types = {
    'GwyContainer': GwyContainer,
    'GwyDataField': GwyDataField,
    'GwySurface': GwySurface,
    'GwyBrick': GwyBrick,
    'GwyGraphModel': GwyGraphModel,
    'GwyGraphCurveModel': GwyGraphCurveModel,
    'GwySIUnit': GwySIUnit,
}
