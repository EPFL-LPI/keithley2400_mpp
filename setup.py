import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="keithley2400_mpp",
    version="0.0.1",
    author="Brian Carlsen",
    author_email="carlsen.bri@gmail.com",
    description="MPP Tracking implemented on a Keithley 2400 SourceMeter.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=[],
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha"
    ],
    install_requires=[
        'numpy',
        'pymeasure'
    ],
    package_data={
    }
)