from setuptools import setup, find_packages

setup(
    name="snake-lang",
    version="0.1.0",
    description="A statically typed superset of Python",
    author="Snake Team",
    packages=find_packages(),
    install_requires=[
        "astor>=0.8.1",
    ],
    entry_points={
        'console_scripts': [
            'snake=snake.cli:main',
            'snakelib=snake.snakelib:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    scripts=['bin/snakelib'],
)