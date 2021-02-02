from setuptools import setup

setup(
    name='podfeed',
    version='1.0',
    long_description=__doc__,
    packages=['server'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['flask', 'BeautifulSoup4', 'requests', 'podgen', 'cachetools', 'diskcache']
)
