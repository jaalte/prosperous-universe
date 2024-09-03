from setuptools import setup, find_packages

setup(
    name='prunpy',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # List any external dependencies here, e.g.,
        
        # api.py
        'requests', 'json', 'pandas', 're', 'os', 'io', 'urllib.parse', 'datetime',

        # pathfinding legacy
        'csv', 'heapq'

    ],
    entry_points={
        'console_scripts': [
            # 'command_name = module:function_name',
        ],
    },
    author='fishmodem',
    author_email='fishmodem@proton.me',
    description='A package for modeling systems within the game Prosperous Universe, and providing an interface for the FIO API.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/fishmodem/prun',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)
