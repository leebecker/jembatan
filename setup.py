from setuptools import setup, find_packages

setup(name='jembatan',
      version='0.0.2',
      description='Jembatan - A framework for bridging NLP libraries',
      url='http://github.com/leebecker/jembatan',
      author='Lee Becker',
      license='Apache 2.0',
      packages=find_packages(),
      install_requires=[
          "bson",
          "spacy",
          "dataclasses-json",
          "typing_inspect"
      ],
      test_require=[
          "pytest"
      ],
      extras_require={
          ":python_version<'3.7'": ["dataclasses"]

      },
      zip_safe=False)
