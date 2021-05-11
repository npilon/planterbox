import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    "nose2>=0.6.0",
    "mock",
    "six",
]

description = 'A plugin for nose2 implementing behavior-driven testing.'

with open("README.rst", "r") as readme:
    long_description = readme.read()


setup(name='planterbox',
      version='0.7.2',
      description=description,
      long_description=long_description,
      license='MIT',
      classifiers=[
          "Intended Audience :: Developers",
          'Topic :: Software Development :: Testing',
          "Programming Language :: Python",
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
      ],
      author='Nick Pilon',
      author_email='npilon@gmail.com',
      url='https://github.com/npilon/planterbox',
      keywords='testing test bdd lettuce cucumber gherkin nosetests nose2',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=True,
      test_suite='planterbox',
      install_requires=requires,
      )
