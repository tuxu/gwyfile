""" Gwyddion object definitions.

    See <http://gwyddion.net/documentation/user-guide-en/gwyfile-format.html>
    for a specification of Gwyddion native data files.
"""
import sys
import struct
import numpy as np
from collections import OrderedDict

from six import BytesIO
from six.moves import range


class GwyObject(OrderedDict):
    def __init__(self, name, data=None, types=None):
        OrderedDict.__init__(self)
        self.name = name
        # For each object attribute, we (optionally) store its type
        self.types = {}
        if isinstance(data, dict):
            self.update(data)
        if isinstance(types, dict):
            self.types.update(types)

    def __repr__(self):
        return '<GwyObject "%s">(%s)' % (
            self.name,
            ', '.join("'%s'" % k for k in self.keys())
        )

    @classmethod
    def frombuffer(cls, buf, return_size=False):
        """ Interpret a buffer as a serialized GwyObject.

        :param return_size: if ``True``, the size of the object within the
        buffer is returned as well.
        """
        pos = buf.find(b'\0')
        name = buf[:pos].decode('utf-8')
        size = struct.unpack('<I', buf[pos + 1:pos + 5])[0]
        object_data = buf[pos + 5:pos + 5 + size]
        buf = object_data
        data = OrderedDict()
        types = {}
        while len(buf) > 0:
            (component_name, component_data, component_typecode,
             component_size) = component_from_buffer(buf, return_size=True)
            data[component_name] = component_data
            types[component_name] = component_typecode
            buf = buf[component_size:]
        if name == 'GwyDataField':
            obj = GwyDataField(data=data, types=types)
        elif name == 'GwySIUnit':
            obj = GwySIUnit(data=data, types=types)
        else:
            obj = cls(name, data, types=types)
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
        io = BytesIO()
        for k in self.keys():
            try:
                typecode = self.types[k]
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


class GwyDataField(GwyObject):
    def __init__(self, data=None, xreal=1.0, yreal=1.0, types=None):
        super(GwyDataField, self).__init__('GwyDataField', types=types)
        if isinstance(data, OrderedDict):
            self.update(data)
        else:
            assert(isinstance(data, np.ndarray) and len(data.shape) == 2)
            yres, xres = data.shape
            self['xres'], self['yres'] = xres, yres
            self['xreal'], self['yreal'] = xreal, yreal
            self['data'] = data.flatten()

    def get_data(self):
        xres, yres = self['xres'], self['yres']
        return self['data'].reshape((yres, xres))


class GwySIUnit(GwyObject):
    def __init__(self, data=None, unitstr='', types=None):
        super(GwySIUnit, self).__init__('GwySIUnit', types=types)
        if isinstance(data, OrderedDict):
            self.update(data)
        else:
            self.types['unitstr'] = 's'
            self.unitstr = unitstr

    @property
    def unitstr(self):
        return self['unitstr']

    @unitstr.setter
    def unitstr(self, s):
        self['unitstr'] = s


def component_from_buffer(buf, return_size=False):
    """ Interpret a buffer as a serialized component.

    :param return_size: if ``True``, the size of the component within
    the buffer is returned as well.
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
        data = np.frombuffer(buf[pos:endpos], dtype=dtype)
    elif typecode == 'S':
        numitems = struct.unpack('<I', buf[pos:pos + 4])[0]
        endpos += 4
        data = []
        for i in range(numitems):
            pos = endpos
            endpos = buf.find(b'\0', pos)
            data.append(buf[pos:endpos].decode('utf-8'))
            endpos += 1
    elif typecode == 'O':
        numitems = struct.unpack('<I', buf[pos:pos + 4])[0]
        endpos += 4
        data = []
        for i in range(numitems):
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
    if isinstance(value, GwyObject):
        return 'o'
    elif type(value) is str:
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
        raise NotImplementedError


def serialize_component(key, value, typecode=None):
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
        buf = struct.pack('<%s' % typecode, value)
    elif typecode in 'CIQD':
        typelookup = {
            'C': np.dtype('<S'), 'I': np.dtype('<i4'),
            'Q': np.dtype('<i8'), 'D': np.dtype('<f8')
        }
        data = value.astype(typelookup[typecode]).data
        buf = b''.join([
            struct.pack('<I', len(value)),
            data.tobytes() if sys.version > '3' else str(data)
        ])
    elif typecode == 'S':
        data = [struct.pack('<I', len(value)), ]
        data += [s.encode('utf-8') + b'\0' for s in value]
        buf = b''.join(data)
    else:
        raise NotImplementedError
    return b''.join([
        key.encode('utf-8'), b'\0',
        typecode.encode('utf-8'),
        buf
    ])
