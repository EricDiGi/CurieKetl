# A simple setup script
from setuptools import setup, find_packages

setup(name='pycurie',
      version='0.0.1',
      author='Eric DiGioacchino',
      url='https://github.com/EricDiGi/CurieKetl',
      keywords=['etl', 'data', 'data engineering', 'data science', 'mlops', 'devops'],
      classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3"
        ],
        long_description=open('../README.md').read(),
        long_description_content_type='text/markdown',
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'curie = curie.__main__:main'
          ]
      }
)