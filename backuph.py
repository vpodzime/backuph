#!/usr/bin/python
"""Source file containing main part"""
from __future__ import print_function
import sys
import os
import dir_tree
import optparse

if __name__ == "__main__":
    parser = optparse.OptionParser(usage="usage: %prog [options] arg1 [arg2]"+
                                    "\n   Use --help for more information")
    parser.add_option(
            "-d", "--draw-only", action="store_true", default=False,
            dest="draw_only",
            help="Only draw directory tree",
            )
    parser.add_option(
            "-F", "--display-files", action="store_true", default=False,
            dest="display_files",
            help="Display also files",
            )
    parser.add_option(
            "-a", "--all", action="store_true", default=False,
            dest="all_",
            help="Take all files and directories (include .*)",
            )
    parser.add_option(
            "-n", "--nums", action="store_true", default=False,
            dest="counts",
            help="Show number of files for each directory",
            )
    parser.add_option(
            "-v", "--verbose", action="store_true", default=False,
            dest="verbose",
            help="Show the tar's verbose output",
            )
    parser.add_option(
            "-q", "--quiet", action="store_true", default=False,
            dest="quiet",
            help="Print only error messages",
            )
    parser.add_option(
            "-c", "--compress", action="store", default="gzip",
            dest="compression",
            help="Compression algorithm to be used.\
                    Possible values are: gzip, bzip, xz, none",
            )

    opts, args = parser.parse_args()
    if (opts.draw_only and (len(args) != 1)) or\
            (not opts.draw_only and (len(args) != 2)):
        parser.print_usage()
        sys.exit(2)

    if opts.quiet:
        sys.stdout = file("/dev/null", "w")

    path = args[0]
    dest = ""

    try:
        curr_dir_tree = dir_tree.DirTree(path, opts.all_)
    except OSError:
        print("Directory {0} doesn't exist.".format(path))
        parser.print_usage()
        sys.exit(3)

    curr_dir_tree.draw_tree(opts.display_files, opts.counts)
    if opts.draw_only:
        sys.exit(0)
    else:
        dest = args[1]

    if not os.path.exists(dest):
        try:
            os.makedirs(dest)
        except OSError:
            print("Destination directory {0} doesn't exist and\
                        cannot be created.".format(dest), file=sys.stderr)
            parser.print_usage()
            sys.exit(4)

    print("Will be archived to {0}.".format(dest))

    if not opts.quiet:
        confirm = raw_input("Continue? [Y/n] ")
        if confirm in ["n", "no", "N", "NO"]:
            sys.exit(1)

    try:
        curr_dir_tree.archive_tree(dest, opts.compression, opts.verbose)
    except dir_tree.ArchivingProblemError as aperr:
        print(aperr, file=sys.stderr)
        sys.exit(4)

