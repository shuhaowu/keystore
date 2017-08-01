"""
A utility to help store encrypted backups of important files like
SSH keys, OTR keys, GPG keys.
"""
from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import sys

from .utils import *  # NOQA
from .fs import KeystoreFS, execute, validate_keystore_attached_or_exit, validate_keystore_not_attached_or_exit
from .restore import Restore


class Attach(object):
  description = "open a keystore file and mount it"

  def __init__(self, parser):
    parser.add_argument("path", help="the path to the keystore file")
    parser.add_argument("-w", "--writable", action="store_true", help="make the keystore writable")
    self.parser = parser

  def validate_args(self, args):
    validate_file_or_exit(args.path)
    validate_keystore_not_attached_or_exit(args.path)

  def run(self, args):
    fs = KeystoreFS.attach(args.path, writable=args.writable)
    logging.info("keystore '{}' attached and mounted at '{}'".format(fs.name, fs.mnt_path))
    verified = fs.verify()
    if args.writable and verified:
      fs.set_readonly(False)
    else:
      fs.set_readonly(True)


class Detach(object):
  description = "umount a keystore file and close it"

  def __init__(self, parser):
    parser.add_argument("name", help="name of the keystore")
    self.parser = parser

  def validate_args(self, args):
    validate_keystore_attached_or_exit(args.name)

  def run(self, args):
    KeystoreFS.detach(args.name)
    logging.info("keystore '{}' detached!".format(args.name))


class Create(object):
  description = "create a new keystore"

  def __init__(self, parser):
    parser.add_argument(
      "-s", "--size", nargs="?",
      default=1024 * 1024 * 1024,  # 1024MB
      type=int,
      help="the size of the keystore in bytes (defaults to 1024MB)"
    )

    parser.add_argument(
      "path",
      help="the path to the keystore file to be created. ensure the parent of this path is owned by root"
    )

  def validate_args(self, args):
    if os.path.exists(args.path):
      fatal("{0} already exists".format(args.path))

    validate_keystore_not_attached_or_exit(args.path)

    parent_dir = os.path.dirname(os.path.abspath(args.path))
    if not os.path.isdir(parent_dir):
      fatal("{0} is not a directory".format(parent_dir))

    parent_stat = os.stat(parent_dir)
    if parent_stat.st_uid != 0 or parent_stat.st_gid != 0:
      fatal("{} must be owned by root".format(parent_dir))

  def run(self, args):
    fs = KeystoreFS.create(args.path, args.size)
    os.mkdir(os.path.join(fs.mnt_path, "rootfs"))

    logger = logging.getLogger()
    logger.info("")
    logger.info("===========================")
    logger.info("KEYSTORE BOOTSTRAP COMPLETE")
    logger.info("===========================")
    logger.info("")
    logger.info("Done creating keystore. It should be mounted at:")
    logger.info(fs.mnt_path)
    logger.info("")
    logger.info("You might need to change the permission of the `rootfs` directory.")
    logger.info("")
    logger.info("To unmount, do:")
    logger.info("# keystore detach {}".format(fs.name.split("-", 1)[1]))


class Open(object):
  description = "xdg-open the keystore path"

  def __init__(self, parser):
    parser.add_argument("name", help="name of the keystore")

  def validate_args(self, args):
    validate_keystore_attached_or_exit(args.name)

  def run(self, args):
    execute("xdg-open {}".format(KeystoreFS(args.name).mnt_path))


class Verify(object):
  description = "zfs scrub the partition"

  def __init__(self, parser):
    parser.add_argument("name", help="name of the keystore")

  def validate_args(self, args):
    validate_keystore_attached_or_exit(args.name)

  def run(self, args):
    fs = KeystoreFS(args.name)
    fs.set_readonly(False)
    fs.verify()
    fs.set_readonly(True)


commands = [
  Attach,
  Detach,
  Create,
  Restore,
  Open,
  Verify,
]


def main():
  sanity_check()

  parser = argparse.ArgumentParser(description=__doc__.strip())
  subparsers = parser.add_subparsers()
  for command_cls in commands:
    name = command_cls.__name__.lower()
    subparser = subparsers.add_parser(name, help=command_cls.description)
    command = command_cls(subparser)
    subparser.set_defaults(cmd=command, which=name)

  args = parser.parse_args()

  if len(vars(args)) == 0:
    # If you call this with no arguments, it will break like this:
    # https://bugs.python.org/issue16308
    parser.print_usage()
    print("{}: error: too few arguments".format(parser.prog), file=sys.stderr)
    sys.exit(1)

  logging.basicConfig(format="[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG)

  args.cmd.validate_args(args)
  args.cmd.run(args)
