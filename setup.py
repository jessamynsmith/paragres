from setuptools import setup, find_packages
import os.path as p

with open(p.join(p.dirname(__file__), 'requirements.txt'), 'r') as reqs:
    install_requires = [line.strip() for line in reqs]

setup(
    name='paragres',
    version='0.1',
    author='Jessamyn Smith',
    author_email='jessamyn.smith@gmail.com',
    url='https://github.com/jessamynsmith/paragres',
    download_url='https://github.com/jessamynsmith/paragres/tarball/0.1',
    description='Utility for synchronizing parallel PostgreSQL databases on Heroku and localhost',
    keywords=['postgresql', 'postgres', 'psql', 'pgbackups', 'database', 'heroku'],

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        'License :: OSI Approved :: MIT License',
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],

    install_requires=install_requires,

    packages=find_packages(exclude=['*test*']),

    entry_points={
        'console_scripts': [
            'paragres = paragres.cli:main'
        ],
    },
)
