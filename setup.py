from setuptools import setup, find_packages

setup(
    name="coda-app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "redis",
        "music21",
        "numpy",
        "werkzeug",
        "python-multipart",
    ],
) 