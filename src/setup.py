# A simple setup script
from setuptools import setup, find_packages

setup(name='pycurie',
      version='0.1.12',
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
      install_requires=[
          'PyYAML',
          'Jinja2',
          'boto3',
          'python-dotenv'
      ],
      entry_points={
          'console_scripts': [
              'curie = curie.__main__:main'
          ]
      },
      package_data={
            "curie.static": ["*"],
            "curie.static.jinja": ["*.md.j2", "*.yaml.j2", "*.yml.j2"]
      }
)