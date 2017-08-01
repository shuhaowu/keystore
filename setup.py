#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
  name="keystore",
  version="1.0",
  description="keystore",
  author="Shuhao Wu",
  author_email="shuhao@shuhaowu.com",
  url="https://github.com/shuhaowu/keystore",
  packages=list(find_packages()),
  include_package_data=True,
  entry_points={
    "console_scripts": [
      "keystore = keystore.cmds:main"
    ]
  },
)
