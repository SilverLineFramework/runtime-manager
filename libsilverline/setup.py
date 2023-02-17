"""Install SilverLine client."""

from setuptools import setup


with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="libsilverline",
    version="2.0.0",
    packages=["libsilverline"],
    license="BSD 3-Clause License",
    install_requires=requirements,
    author='Tianshu Huang',
    author_email='tianshu2@andrew.cmu.edu',
    description="SilverLine Python Client",
    classifiers=['Programming Language :: Python :: 3']
)
