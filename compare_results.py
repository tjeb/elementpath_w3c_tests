#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys


class WorkingDirectory(object):
    def __init__(self, new_directory):
        self.new_directory = new_directory
        self.original_directory = os.getcwd()

    def __enter__(self):
        os.chdir(self.new_directory)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_directory)


def compare_reports(report_file_a, report_file_b):
    with open(report_file_a, 'r') as infile:
        report_a = json.load(infile)
    with open(report_file_b, 'r') as infile:
        report_b = json.load(infile)

    fields = []
    for f in report_a["summary"].keys():
        if f not in ['read', 'ignored', 'run', 'skipped']:
            fields.append(f)

    print("Summary of differences:")
    for field in fields:
        val_a = report_a["summary"][field]
        val_b = report_b["summary"][field]
        diff = val_b - val_a
        if diff > 0:
            diffstr = "+%d" % diff
        elif diff < 0:
            diffstr = "%d" % diff
        else:
            diffstr = "no change"
        print("    status %s: %s" % (field, diffstr))
    print("")

    move_report = {}
    for field in fields:
        for name in report_a[field]:
            if name not in report_b[field]:
                # print("No longer in %s: %s" % (field, name))
                for new_field in fields:
                    if name in report_b[new_field]:
                        # print("now in %s" % new_field)
                        key = (field, new_field)
                        if key in move_report:
                            move_report[key].append(name)
                        else:
                            move_report[key] = [name]
    for key, names in move_report.items():
        for name in names:
            print("%s was %s, is now %s" % (name, key[0], key[1]))


def change_git_branch(path, branch):
    with WorkingDirectory(path):
        process = subprocess.Popen(['git', 'checkout', branch],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            sys.stdout.write(stderr.decode('utf-8'))
        if process.returncode != 0:
            print("Could not change git branch, aborting")
            sys.exit(3)


def run_testsuite(catalog_file, report_file, force):
    if os.path.exists(report_file) and not force:
        print("%s already exists, not running test suite again" % report_file)
        return
    process = subprocess.Popen(['./execute_tests.py', '-v0', '-r', report_file, catalog_file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if stdout:
        sys.stdout.write(stdout.decode('utf-8'))
    if stderr:
        sys.stderr.write(stderr.decode('utf-8'))
    if process.returncode != 0:
        print("Error executing test suite")
        sys.exit(4)
    print("Created report: %s" % report_file)


def compare_repository_branches(catalog_file, path, old, new, force):
    if not os.path.exists(path) or not os.path.isdir(path):
        print("Error: %s not found or not a directory" % path)
        sys.exit(2)
    report_file_old = '/tmp/report_%s.json' % old
    report_file_new = '/tmp/report_%s.json' % new
    change_git_branch(path, old)
    run_testsuite(catalog_file, report_file_old, force)
    change_git_branch(path, new)
    run_testsuite(catalog_file, report_file_new, force)
    compare_reports(report_file_old, report_file_new)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('old', help='The old branch or report')
    parser.add_argument('new', help='The new branch or report')
    parser.add_argument('-c', '--catalog-file', help='the file of the catalog.xml to read (the main file of the test suite), defaults to ../qt3tests/catalog.xml', default='../qt3tests/catalog.xml')
    parser.add_argument('-g', '--git-repository', help='path of the repository (old and new are now branch names)')
    parser.add_argument('-r', '--reports', action="store_true", help='path of the repository (old and new are now report file names)')
    parser.add_argument('-f', '--force', action="store_true", help='force running of test suite if report file already exists')
    args = parser.parse_args()

    if args.reports:
        if args.git_repository:
            print("You can only specify -g or -r, not both")
            sys.exit(1)
        compare_reports(args.old, args.new)
    elif args.git_repository:
        compare_repository_branches(args.catalog_file, args.git_repository, args.old, args.new, args.force)
    else:
        print("You must specify either -g or -r")


if __name__ == '__main__':
    main()
