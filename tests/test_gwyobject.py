import os
import pytest
import gwyfile


@pytest.fixture(scope="module")
def test_data():
    filename = os.path.realpath(
        '{}/test.gwy'.format(
            os.path.dirname(os.path.realpath(__file__))
        )
    )
    return gwyfile.load(filename)


def test_datafield(test_data):
    channels = gwyfile.util.get_datafields(test_data)
    assert 'Test' in channels
    test_channel = channels['Test']
    data = test_channel.data
    assert data.shape == (128, 128)
    assert data[0][0] == pytest.approx(0.00082494, 1E-5)
    assert data[44][33] == pytest.approx(0.00085301, 1E-5)


def test_tofile(test_data, tmpdir):
    filename = str(tmpdir.join('output.gwy'))
    test_data.tofile(filename)
