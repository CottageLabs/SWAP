from setuptools import setup, find_packages

setup(
    name = 'swap',
    version = '0.0.1',
    packages = find_packages(),
    install_requires = [
        "Flask==0.8",
        "Flask-Login==0.2.6",
        "Flask-WTF==0.8.4",
        "requests==2.20.0"
    ],
    url = 'http://cottagelabs.com/',
    author = 'Cottage Labs',
    author_email = 'us@cottagelabs.com',
    description = 'A web API layer over an ES backend, with various useful plugins',
    license = 'Copyheart',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: Copyheart',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
