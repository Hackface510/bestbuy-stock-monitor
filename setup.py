from setuptools import setup, find_packages

setup(
    name="bestbuy-stock-monitor",
        version="1.0.1",
            description="Best Buy local stock monitor with Discord alerts",
                packages=find_packages(),
                    install_requires=[
                            "playwright>=1.40.0",
                                    "playwright-stealth>=1.0.0",
                                            "aiohttp>=3.9.0",
                                                    "python-dotenv>=1.0.0",
                                                        ],
                                                            entry_points={
                                                                    "console_scripts": [
                                                                                "bestbuy-monitor=monitor.cli:main",
                                                                                        ],
                                                                                            },
                                                                                                python_requires=">=3.9",
                                                                                                )
