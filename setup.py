from distutils.core import setup

from setuptools import find_packages


DEPENDENCIES = [
    'aiohttp',
    'aiopg',
    'aioredis',
    'aiohttp_jinja2',
    'gunicorn',
    'pydantic',
    'python-dotenv',
    'sqlalchemy',
]


EXTRAS_STYLE = [
    'isort',
    'flake8',
    'flake8-import-order',
]


EXTRAS_DEV = [
    *EXTRAS_STYLE,
]


setup(
    name='application',
    version='0.1.0',
    install_requires=DEPENDENCIES,
    include_package_data=True,
    extras_require={
        'style': EXTRAS_STYLE,
        'dev': EXTRAS_DEV,
    },
    packages=find_packages(include=['app', 'app.*']),
    entry_points={
        'console_scripts': ['my_super_app=app.main:run']
    },
)
