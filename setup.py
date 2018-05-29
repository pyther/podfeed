from setuptools import setup

setup(
    name='nrfeed',
    version='1.1',
    long_description=__doc__,
    packages=['app'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['Flask', 'flask-caching', 'requests', 'flask_limiter']
)
