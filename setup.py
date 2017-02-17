from setuptools import setup
import versioneer

setup(
    name='gwyfile',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Pure Python implementation of the Gwyddion file format',
    long_description=open('README.rst').read(),
    author='Tino Wagner',
    author_email='ich@tinowagner.com',
    url='https://github.com/tuxu/gwyfile',
    packages=['gwyfile'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
    ],
    keywords='gwyddion file format',
    platforms='any',
    license='MIT',
    install_requires=['numpy', 'six'],
)
