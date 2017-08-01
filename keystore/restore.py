from __future__ import absolute_import, division, print_function

import logging
import os
import shutil

from . import utils
from .fs import KeystoreFS, validate_keystore_attached_or_exit


class Restore(object):
  description = "restore files stored in the rootfs directory on the keystore"

  DIRNAME = "rootfs"

  def __init__(self, parser):
    parser.add_argument("-R", "--root", nargs="?", default="/", help="the root to restore to, by default it is at /")
    parser.add_argument("-x", "--execute", action="store_true", help="actually execute the restore as oppose to doing it as a dry run")
    parser.add_argument("name", help="name of the keystore")

  def validate_args(self, args):
    utils.validate_dir_or_exit(args.root)
    validate_keystore_attached_or_exit(args.name)
    args.fs = KeystoreFS(args.name)
    args.source_path = os.path.join(args.fs.mnt_path, self.DIRNAME)
    utils.validate_dir_or_exit(args.source_path)

  def run(self, args):
    logger = logging.getLogger()
    for dirpath, dirnames, filenames in os.walk(args.source_path):
      target_dirpath = os.path.join(args.root, dirpath.replace(args.source_path, "").lstrip("/"))
      for dirname in dirnames:
        source_path = os.path.join(dirpath, dirname)
        target_path = os.path.join(target_dirpath, dirname)
        stat = os.stat(source_path)
        logger.info("new directory -> {} (owner={}, group={}, mode={})".format(target_path, stat.st_uid, stat.st_gid, oct(stat.st_mode)))
        if args.execute:
          utils.mkdir_p(target_path)
          os.chown(target_path, stat.st_uid, stat.st_gid)
          os.chmod(target_path, stat.st_mode)

      for filename in filenames:
        source_path = os.path.join(dirpath, filename)
        target_path = os.path.join(target_dirpath, filename)
        stat = os.stat(source_path)
        logger.info("{} -> {} (owner={}, group={}, mode={})".format(source_path.replace(args.source_path, "").lstrip("/"), target_path, stat.st_uid, stat.st_gid, oct(stat.st_mode)))
        if args.execute:
          shutil.copy2(source_path, target_path)
