from setuptools import setup
import versioneer

setup(
    name='gwyfile',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author='Tino Wagner',
    author_email='ich@tinowagner.com',
    package_dir = {'': '.'},
    packages = ['gwyfile'],
)
