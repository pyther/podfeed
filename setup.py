from setuptools import setup

setup(
    name='nrfeed',
    version='3.1',
    long_description=__doc__,
    packages=['server'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['flask', 'BeautifulSoup4', 'requests', 'jsonpickle']
)
