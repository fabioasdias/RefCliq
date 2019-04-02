import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="refcliq",
    version="0.0.9",
    author="Fabio Dias",
    author_email="fabio.dias@gmail.com",
    description="Community analysis in bibliographical references",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fabioasdias/RefCliq",
    packages=setuptools.find_packages(),
    scripts=['run-refcliq.py'],
    install_requires=[
        "python-louvain",
        "numpy",
        "pybtex",
        "nltk",
        "tqdm",
        "titlecase",
        "fuzzywuzzy[speedup]"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)