#!/usr/bin/env python
import os
import sys
import setuptools


if sys.argv[-1] == "publish":
    os.system("python setup.py bdist_wheel")
    os.system("python -m twine upload dist/*")
    sys.exit(0)


setuptools.setup(
    name="async_django_user",
    version="0.1.0",
    description="Django user for async frameworks",
    long_description=open("./README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/imbolc/async-django-user",
    packages=["async_django_user"],
    author="Imbolc",
    author_email="imbolc@imbolc.name",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
