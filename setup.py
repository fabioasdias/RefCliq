import setuptools
from glob import glob
from os.path import basename, dirname, join, splitext
from os import walk


with open("README.md", "r") as fh:
    long_description = fh.read()

#https://stackoverflow.com/questions/27664504/how-to-add-package-data-recursively-in-python-setup-py
def package_files(directory):
    paths = []
    for (path, directories, filenames) in walk(directory):
        for filename in filenames:
            paths.append(join('..', path, filename))
    return paths

extra_files = package_files('template')

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
    package_data={'': extra_files},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data = True,    
    scripts = ['refcliq.py', 'refcliqvis.py'],
    install_requires = [
        "python-louvain>=0.13",
        "numpy>=1.16.2",
        "pybtex>=0.22.2",
        "nltk>=3.4",
        "tqdm>=4.31.1",
        "titlecase>=0.12.0",
        "fuzzywuzzy[speedup]>=0.17.0",
        "klepto>=0.1.6",
        "h5py>=2.9.0",
        "spacy>=2.1.3",
        # "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-2.1.0/en_core_web_sm-2.1.0.tar.gz",
        "googlemaps>=3.0.2",
        "scikit-learn>=0.20.3"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)