from setuptools import setup, find_packages
import os.path as p

version = "0.6.2"

with open(p.join(p.dirname(__file__), "requirements", "package.txt"), "r") as reqs:
    install_requires = [line.strip() for line in reqs]

tests_require = []
try:
    with open(p.join(p.dirname(__file__), "requirements", "test.txt"), "r") as reqs:
        tests_require = [line.strip() for line in reqs]
except IOError:
    pass


setup(
    name="paragres",
    version=version,
    author="Jessamyn Smith",
    author_email="jessamyn.smith@gmail.com",
    url="https://github.com/jessamynsmith/paragres",
    download_url="https://github.com/jessamynsmith/paragres/archive/v{0}.tar.gz".format(version),
    license="MIT",
    description="Utility for synchronizing parallel PostgreSQL databases on Heroku, local, "
                "and remote servers",
    long_description=open("README.rst").read(),
    keywords=["postgresql", "postgres", "psql", "pgbackups", "database", "heroku"],

    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],

    install_requires=install_requires,
    tests_require=tests_require,

    packages=find_packages(exclude=["*test*"]),

    entry_points={
        "console_scripts": [
            "paragres = paragres.cli:main"
        ],
    },
)
