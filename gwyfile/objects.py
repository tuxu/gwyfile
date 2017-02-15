"""Gwyddion object definitions.

See <http://gwyddion.net/documentation/user-guide-en/gwyfile-format.html>
for a specification of Gwyddion native data files.
"""
import struct
from collections import OrderedDict
import numpy as np

from six import BytesIO, string_types
from six.moves import range


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

    @classmethod
    def fromfile(cls, filename):
        with open(filename, 'rb') as f:
            data = f.read()
        assert(data[:4] == b'GWYP')
        return cls.frombuffer(data[4:])

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

    def tofile(self, filename):
        with open(filename, 'wb') as f:
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
        data = buf[pos]
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
    'GwySIUnit': GwySIUnit,
}
