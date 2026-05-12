from setuptools import setup, find_packages

setup(
    name="syllabreak",
    version="0.6.0",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
    ],
    python_requires=">=3.9",
    author="Apakabar.fm team",
    description="A library for syllable breaking and language detection",
    package_data={
        "syllabreak": ["data/*.yaml"],
    },
)