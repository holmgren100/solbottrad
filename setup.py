"""Setup configuration for Solana Trading Bot v2.0"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="solana-trading-bot",
    version="2.0.0",
    author="holmgren100",
    description="Solana trading bot with TIER 1 & TIER 2 filters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/holmgren100/solbottrad",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "solana>=0.30.0",
        "solders>=0.18.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "structlog>=23.1.0",
        "colorlog>=6.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.1",
            "mypy>=1.5.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
        ],
    },
)
