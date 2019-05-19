from setuptools import setup

setup(
    name='nrfeed',
    version='2.0',
    long_description=__doc__,
    packages=['server'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['Flask', 'BeautifulSoup4', 'requests', 'pickledb', 'flask_limiter']
)
