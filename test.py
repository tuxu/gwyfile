import gwyfile
import matplotlib.pyplot as plt

obj = gwyfile.GwyObject.fromfile('test.gwy')
channels = gwyfile.util.get_datafields(obj)
channel = channels['Test']
data = channel.get_data()

fig, ax = plt.subplots()
ax.imshow(data, interpolation='none', origin='upper',
          extent=(0, channel['xreal'], 0, channel['yreal']))
plt.show()
