from __future__ import absolute_import, division, print_function

import logging
import os
import os.path
import subprocess
import time

from .utils import fatal


class SystemExecuteError(RuntimeError):
  pass


def execute(command, logger=None, raises=True):
  logger = logger or logging.getLogger()
  logger.info("EXECUTING: {}".format(command))
  status = os.system(command)
  if raises and status != 0:
    raise SystemExecuteError("executing `{}` failed with status {}".format(command, status))
  else:
    return status


def create_sparse_file(path, size):
  with open(path, "w") as f:
    f.seek(size - 1)
    f.write('\0')


def validate_keystore_not_attached_or_exit(name):
  if KeystoreFS.attached(KeystoreFS.normalize_name(name)):
    fatal("keystore '{}' already attached. use a different name for your keystore or detach via `keystore detach`".format(name))


def validate_keystore_attached_or_exit(name):
  if not KeystoreFS.attached(KeystoreFS.normalize_name(name)):
    fatal("keystore '{}' is not attached. use `keystore attach` to attach".format(name))


class KeystoreFS(object):
  MNT_PREFIX = "/mnt"

  @staticmethod
  def normalize_name(path):
    return "keystore-{}".format(os.path.splitext(os.path.basename(path))[0])

  @staticmethod
  def attached(name):
    return os.path.exists("/dev/mapper/{}".format(name)) or os.path.exists("{}/{}".format(KeystoreFS.MNT_PREFIX, name))

  @classmethod
  def create(cls, path, size):
    fs = cls(path, path)
    fs._create(size)
    return fs

  @classmethod
  def attach(cls, path, writable=False):
    fs = cls(path, path)
    fs._attach(writable=writable)
    return fs

  @classmethod
  def detach(cls, name):
    fs = cls(name)
    return fs._detach()

  def __init__(self, name, path=None):
    self.logger = logging.getLogger()
    self.name = self.normalize_name(name)
    self.path = path

    self.mapper_path = os.path.join("/dev", "mapper", self.name)
    self.mnt_path = "{}/{}".format(self.MNT_PREFIX, self.name)

  def verify(self):
    execute("zpool scrub {}".format(self.name))
    while True:
      output = subprocess.check_output(["zpool", "status", self.name]).decode("utf-8")
      if "scrub in progress" in output.lower():
        time.sleep(0.5)
        continue

      break

    output = subprocess.check_output(["zpool", "status", "-x", self.name]).decode("utf-8")
    print(output.strip())
    return "healthy" in output

  def set_readonly(self, readonly):
    if readonly:
      value = "on"
    else:
      value = "off"

    execute("zfs set readonly={} {}".format(value, self.name))

  def _create(self, size):
    self.logger.info("creating sparse file")
    create_sparse_file(self.path, size)

    self.logger.info("setting up LUKS on file")
    execute("cryptsetup luksFormat {}".format(self.path))
    execute("cryptsetup luksOpen {} {}".format(self.path, self.name))

    self.logger.info("setting up ZFS")
    execute("zpool create -m {} {} {}".format(self.mnt_path, self.name, self.mapper_path))
    execute("zfs set compression=on {}".format(self.name))

    # Must do this now as ZFS preserves the permission bits
    os.chmod(self.mnt_path, int("0700", 8))

  def _attach(self, writable=False):
    execute("cryptsetup luksOpen {} {}".format(self.path, self.name))
    execute("zpool import -d /dev/mapper {}".format(self.name))

  def _detach(self):
    execute("zpool export {}".format(self.name))
    os.rmdir(self.mnt_path)
    execute("cryptsetup luksClose {}".format(self.name))
