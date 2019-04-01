import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="refcliq",
    version="0.0.1",
    author="Fabio Dias",
    author_email="fabio.dias@gmail.com",
    description="Community analysis in bibliographical references",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fabioasdias/RefCliq",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)