import unittest
import os

import gwyfile


class TestGwyObject(unittest.TestCase):

    def setUp(self):
        filename = os.path.realpath(
            '{}/test.gwy'.format(
                os.path.dirname(os.path.realpath(__file__))
            )
        )
        self.obj = gwyfile.GwyObject.fromfile(filename)

    def test_datafield(self):
        channels = gwyfile.util.get_datafields(self.obj)
        self.assertEqual('Test' in channels, True)
        test = channels['Test']
        data = test.get_data()
        self.assertEqual(data.shape, (128, 128))

    def test_tofile(self):
        import tempfile
        handle, filename = tempfile.mkstemp()
        self.obj.tofile(filename)
