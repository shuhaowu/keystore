from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
import errno
import hashlib
import os
import subprocess
import sys


def fatal(message):
  print("error: {}".format(message), file=sys.stderr)
  sys.exit(1)


def quiet_call(command):
  return subprocess.call(command, shell=True, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, "wb"))


@contextmanager
def chdir(path):
  old_cwd = os.getcwd()
  try:
    os.chdir(path)
    yield
  finally:
    os.chdir(old_cwd)


def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise


def hash_file(path, chunk_size=2**20):
  h = hashlib.sha256()
  with open(path, "rb") as f:
    while True:
      buf = f.read(chunk_size)
      if not buf:
        break
      h.update(buf)

  return h.hexdigest()


def sanity_check():
  if os.geteuid() != 0:
    fatal("keystore must be run as root, preferably in xterm")

  os.umask(int("077", 8))


def validate_file_or_exit(path):
  if not os.path.isfile(path):
    fatal("{0} is not a valid file".format(path))


def validate_dir_or_exit(path):
  if not os.path.isdir(path):
    fatal("{0} is not a valid directory".format(path))


def validate_exists_or_exit(path):
  if not os.path.exists(path):
    fatal("{0} does not exist".format(path))
