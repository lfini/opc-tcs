"""
Setup file da usare solo per py2exe.
"""

import sys
import os
from distutils.core import setup

import py2exe

def get_files(adir):
    "Lista dei file della directory data"
    return [os.path.join(adir, x) for x in os.listdir(adir)]

MODULES = ["astro", "interpolator", "telecomm", "widgets"]
TABLES = get_files("tables")
ICONS = get_files("icons")
setup(windows=["dtracker.py"],
      version="1.0",
      description="Asservimento cupola-telescopio",  
      author="Luca Fini",
      author_email="luca.fini@gmail.com",
      url="https://github.com/lfini/opc-tcs",
      py_modules=MODULES,
      data_files=[("tables", TABLES),
                  ("icons", ICONS)],
      options={"py2exe": {"optimize": 2, 
                          "unbuffered": True,
                          "skip_archive": True}}
)
