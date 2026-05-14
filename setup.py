from setuptools import setup, find_packages

setup(
    name="syllabreak",
    version="0.18.0",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
        # `regex` (not stdlib `re`) gives us \p{M} for Hebrew points, Arabic
        # harakat, Devanagari matras to attach to the preceding letter.
        "regex>=2024.0",
    ],
    python_requires=">=3.9",
    author="Apakabar.fm team",
    description="A library for syllable breaking and language detection",
    package_data={
        "syllabreak": ["data/*.yaml"],
    },
)