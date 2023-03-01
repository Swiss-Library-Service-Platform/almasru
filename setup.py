from setuptools import find_packages, setup
import almasru

# read the contents of your README file
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.rst").read_text()

setup(name='almasru',
      version=almasru.__version__,
      long_description=long_description,
      long_description_content_type='text/reST',
      packages=find_packages(),
      py_modules=['almasru'],
      author_email='raphael.rey@slsp.ch'
      )