import setuptools
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="refcliq",
    version="0.0.10",
    author="Fabio Dias",
    author_email="fabio.dias@gmail.com",
    description="Community analysis in bibliographical references",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fabioasdias/RefCliq",
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,    
    scripts=['refcliq.py'],
    install_requires=[
        "python-louvain",
        "numpy",
        "pybtex",
        "nltk",
        "tqdm",
        "titlecase",
        "fuzzywuzzy[speedup]",
        "klepto",
        "h5py",
        "spacy",
        "googlemaps"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)