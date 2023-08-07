# A simple setup script
from setuptools import setup, find_packages

setup(name='curie',
      version='0.0.1',
      author='Eric DiGioacchino',
      url='https://github.com/EricDiGi/CurieKetl',
      keywords=['etl', 'data', 'data engineering', 'data science', 'mlops', 'devops'],
      classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3"
        ],
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'curie = curie.__main__:main'
          ]
      }
)