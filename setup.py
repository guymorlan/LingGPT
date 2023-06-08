from setuptools import setup, find_packages

setup(
    name='LingGPT',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
    ],
    entry_points={
        'console_scripts': [
            'linggpt=LingGPT.run:main',
        ],
    },
)

