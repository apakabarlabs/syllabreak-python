from setuptools import find_packages, setup

setup(
    name="syllabreak",
    version="0.19.1",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
        "regex>=2024.0",
    ],
    python_requires=">=3.10",
    author="Apakabarlabs",
    description="A library for syllable breaking and language detection",
    package_data={
        "syllabreak": ["data/*.yaml"],
    },
)
