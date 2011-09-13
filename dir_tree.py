"""This module provides class DirTree which represents the directory tree."""
from __future__ import print_function
import os
import sys
import subprocess
import re
from os.path import join as ospjoin

PREFIX_SUFFIX_LENGTH = 3
COMPRESSION_TYPE = {
        "gzip": "-z",
        "bzip": "-j",
        "xz": "-J",
        }
COMPRESSION_EXT = {
        "gzip": ".gz",
        "bzip": ".bz",
        "xz": ".xz",
        "none": "",
        }

class ArchivingProblemError(Exception):
    """Exception for problems with archiving."""
    pass

class NoMatchingError(Exception):
    """Exception for problems with find matching directory."""
    pass

def _call_tar(args, verbose=False):
    """
    Function that uses subprocess.call() to call tar
    @param args: args to be passed to tar
    @type args: list
    @param verbose: whether to pipe tar's output to /dev/null or not
    @type verbose: boolean

    """
    cmd = ["tar"]
    cmd.extend(args)
    if verbose:
        subprocess.call(cmd)
    else:
        null_file = file("/dev/null", "w")
        subprocess.call(cmd, stdout=null_file)
        null_file.close()

def _find_matching_item(name_part, dest):
    """
    Function that finds directory in dest directory whose name matches the first
    argument.

    @param name_part: part of the name to be matched
    @type name_part: string
    @param dest: destination directory where to look for
    @type dest: string
    @return: full path of the matching directory (if any)
    @raise NoMatchError: if destination directory doesn't contain any matching
                          directory

    """

    try:
        for item in os.listdir(dest):
            if re.match(name_part + ".*", item, re.IGNORECASE):
                return ospjoin(dest, item)
        raise NoMatchError("No matching directory found.")
    except IOError as ioerr:
        raise NoMatchError(str(ioerr))


class _DirNode(object):
    """This class represents a single directory in DirTree."""
    def __init__(self, path, parent=None):
        """
        Constructor of the DirNode object. If parent is None this node is
        considered to be the root of the DirTree.

        @param path: path to the directory
        @type path: string
        @param parent: DirNode that has this node in children
        @type parent: DirNode

        """

        self.path = path
        self.parent = parent

        self.name = os.path.basename(self.path.rstrip("/"))
        self.children = []
        self.files = []

    def _get_items(self, take_hidden=False):
        """
        Method that populates self.children with directories contained in itself
        as a list of DirNodes and self.files with files contained in itself as a
        list of path strigs.

        @param skip_hidden: whether to skip hidden directories or not
        @type skip_hidden: boolean

        """

        for item in os.listdir(self.path):
            if item.startswith(".") and not take_hidden:
                continue
            if os.path.isdir(ospjoin(self.path, item)):
                child_path = ospjoin(self.path, item)
                self.children.append(_DirNode(child_path, self))
            else:
                self.files.append(item)

    def build_subtree(self, take_hidden=False):
        """Method that builds a subtree of directories and files."""
        self._get_items(take_hidden)

        for child in self.children:
            child.build_subtree()

    def _draw_node(self, indent, counts=False):
        """
        Method that prints textual representation of the node.

        @param indent: how many spaces will be printed before the name
        @type indent: int

        """

        spaces = indent * " "
        suffix = ""
        if self.children:
            suffix = " +"
        elif not self.files and not counts:
            suffix = " o"
        else:
            suffix = " :"
            if counts:
                suffix += " {0}".format(len(self.files))
        print("{0}| {1}{2}".format(spaces, self.name, suffix))


    def _draw_files(self, indent):
        """
        Method that prints textual representation of contained files.

        @param indent: how many spaces will be printed before filenames
        @type indent: int

        """

        spaces = indent * " "
        for file_ in self.files:
            print("{0}* {1}".format(spaces, file_))

    def draw_subtree(self, indent, draw_files=False, counts=False):
        """
        Method that prints textual representation of the subtree.

        @param indent: how many spaces will be used before directory's name
        @type indent: int
        @param draw_files: whether files shoudl be also printed or not
        @type draw_files: boolean

        """

        self._draw_node(indent, counts)
        if draw_files:
            self._draw_files(indent + len(self.name) +
                    PREFIX_SUFFIX_LENGTH)
        for child in self.children:
            child.draw_subtree(indent + len(self.name) +
                    PREFIX_SUFFIX_LENGTH, draw_files, counts)



    def archive_subtree(self, dest, compression="gzip", verbose=False):
        """
        Method that archives subtree. It makes tarballs from directories
        containing only files or it makes same-named directories in the
        destination directory for directories containing subdirectories and it
        makes tarballs from files contained in these directories.

        @param dest: destination directory where to make subtree
        @type dest: string
        @param compression: compression algorithm to be used (possible values
                            are "gzip", "bzip", "xz", "none")
        @type compression: string
        @param verbose: whether to pipe tar's output to stdin or not
        @type verbose: boolean
        @raise ArchivingProblemError: in case there was some problem while
                                      archiving (i.e. tar's return code was
                                      not 0)

        """

        print("Archiving files in {0}...".format(self.path), end="")
        sys.stdout.flush()
        retcode = 0
        args = []
        if verbose:
            args.append("-v")
        if compression != "none":
            args.append(COMPRESSION_TYPE[compression])
        if not self.children:
            args.extend([
                "-c",
                #don't want absolute paths
                "-C", os.path.dirname(self.path.rstrip("/")),
                "-f",
                ospjoin(dest,
                    self.name + ".tar" + COMPRESSION_EXT[compression]),
                #option -C changes directory, so we can use names
                self.name,
                ])
            _call_tar(args, verbose)
        else:
            if not os.path.exists(ospjoin(dest, self.name)):
                try:
                    os.mkdir(ospjoin(dest, self.name))
                except OSError as oserr:
                    raise ArchivingProblemError(
                            "Cannot create directory {0}.\n{1}".format(
                                ospjoin(dest, self.name), oserr)
                            )
            if self.files:
                args.extend([
                    "-c",
                    "-C", self.path,
                    "-f",
                    ospjoin(dest, self.name,
                        self.name + ".tar" + COMPRESSION_EXT[compression]),
                    ])
                args.extend(self.files)
                _call_tar(args, verbose)

        print("done")
        if retcode != 0:
            raise ArchivingProblemError(
                "Return code of tar (archiving {0}) was: {1}".format(
                    self.path, retcode)
                )

        for child in self.children:
            child.archive_subtree(ospjoin(dest, self.name),
                    compression, verbose)

class DirTree(_DirNode):
    """
    This class represents a directory tree. In fact, it's just a wrapper
    around the _DirNode class.

    """

    def __init__(self, path, take_hidden=False):
        """
        Constructor of this class.

        @param path: path to the root of the directory tree
        @type path: string
        @param skip_hidden: whether also include hidden directories or not
        @type skip_hidden: boolean

        """

        super(DirTree, self).__init__(path)
        self.build_subtree(take_hidden)

    def draw_tree(self, draw_files=False, counts=False):
        """
        Prints textual representation of the directory tree.

        @param draw_files: whether also print contained files or not
        @type draw_files: boolean

        """

        self.draw_subtree(0, draw_files, counts)

    def archive_tree(self, dest, compression="gzip", verbose=False):
        """
        Archives the directory tree to the destination directory.

        @param dest: destination directory
        @type dest: string
        @param compression: type of compression to be used
        @type compression: string
        @param verbose: whether to show tar's output or not
        @type verbose: boolean

        """

        self.archive_subtree(dest, compression, verbose)

class DirList(object):
    """
    This class represents a set of directories. Compared to DirTree it doesn't
    need root directory so it's items doesn't have to have common parent dir.

    """

    def __init__():
        """Constructor of the class DirSet that only initializes atributes."""
        self.items = [] #list of tuples (_DirNode, dest_path)

    def list_from_file(self, path):
        """
        Method that populates self.items with directories listed with their
        destination directoreis (see documentation for more details) in a file.

        @param path: path of the file listing directories
        @type path: string
        @raise IOError: when file doesn't exist

        """

        list_file = open(path, "r")
        for line in list_file:
            path, dest = line.split(" -> ", 2)
            if os.path.abspath(path):
                self.items.append((_DirNode(path), dest))
            else:
                full_path = ospjoin(os.path.getcwd(), path)
                self.items.append(_DirNode(full_path, dest))

    def list_by_prefix(self, source, dest, delimiter="__"):
        for item in os.listdir(source):
            parts = item.split(delimiter)
            #find match for all parts except the last
            pass

    def archive_list(self, compression="gzip", verbose="False"):
        """
        Method that archives list of directories and their subdirectories. See
        documentation of method _DirNode.archive() for more details.

        """

        for (dirnode, dest) in self.items():
            dirnode.archive_subtree(dest, compression, verbose)
