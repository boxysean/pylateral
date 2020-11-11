import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name='pylateral',
    version='1.0.0',
    description='Intuitive multi-threaded task processing in python.',
    long_description=README,
    long_description_content_type="text/markdown",
    url='https://boxysean.github.io/pylateral/',
    author='Sean McIntyre',
    author_email='boxysean@gmail.com',
    license='MIT',
    tests_require=[
        'pytest',
    ],
    packages=find_packages(),
)

