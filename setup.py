import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    "nose2",
    "mock"
]

description = 'A plugin for nose2 implementing behavior-driven testing.'

setup(name='planterbox',
      version='0.1',
      description=description,
      classifiers=[
          "Programming Language :: Python",
      ],
      author='Nick Pilon',
      author_email='npilon@gmail.com',
      url='https://github.com/npilon/planterbox',
      keywords='testing test bdd lettuce cucumber gherkin nosetests nose2',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='planterbox',
      install_requires=requires,
      )

