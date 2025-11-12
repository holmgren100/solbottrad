from setuptools import setup, find_packages

setup(
    name="solana-trading-bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "scikit-learn",
        "numpy",
        "aiohttp",
        "python-dotenv",
        "pydantic",
        "pydantic-settings",
        "websockets",
        "requests",
        "pandas",
        "python-telegram-bot",
        "tweepy",
    ],
    python_requires=">=3.10",
    author="Your Name",
    description="A Solana-based trading bot for meme coins and small-cap tokens",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)