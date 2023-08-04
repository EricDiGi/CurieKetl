# A simple setup script
from setuptools import setup, find_packages

setup(name='curie',
      version='0.1',
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'curie = curie.__main__:main'
          ]
      }
)