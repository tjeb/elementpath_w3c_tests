#!/usr/bin/env python3

import argparse
import sys
import traceback

from collections import OrderedDict
from lxml import etree

from test_harness import *
from util import WorkingDirectory



SKIP_TESTS = [
    'fn-subsequence.cbcl-subsequence-010',
    'fn-subsequence.cbcl-subsequence-011',
    'fn-subsequence.cbcl-subsequence-012',
    'fn-subsequence.cbcl-subsequence-013',
    'fn-subsequence.cbcl-subsequence-014',
    'prod-NameTest.NodeTest004'
]


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('filename', help='the file of the catalog.xml to read (the main file of the test suite)')
    parser.add_argument('testcase', nargs='?', help='a specific testset or testcase to run (match on substring of testset + testcase name)')
    parser.add_argument('-r', '--report', help="Write a report (JSON format) to the given file")
    parser.add_argument('-v', '--verbose', type=int, default=1, help='verbosity')
    parser.epilog = """
Verbosity levels:\n
0: no output
1: print summary (default)
2: print execution failures
3: print test failures
4: reserved
5: print detailed debug information
"""
    args = parser.parse_args()

    test_name = args.testcase

    report = OrderedDict()
    report["parse_error"] = []
    report["evaluate_error"] = []
    report["execute_error"] = []
    report["testcode_error"] = []
    report["success"] = []
    report["failed"] = []

    full_path = os.path.abspath(args.filename)
    if not os.path.exists(full_path):
        print("Error: %s does not exist" % args.filename)
        sys.exit(1)
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    with WorkingDirectory(directory):
        catalog_xml = etree.parse(filename)

        environments = {}
        testsets = {}

        for environment_xml in catalog_xml.getroot().findall("environment", namespaces=nsmap):
            environment = Environment(environment_xml)
            environments[environment.name] = environment

        for testset_xml in catalog_xml.getroot().findall("test-set", namespaces=nsmap):
            testset = TestSet(testset_xml)
            testsets[testset.name] = testset

        count_all = 0
        count_ignore = 0
        count = 0
        count_true = 0
        count_false = 0
        count_none = 0
        count_parse_error = 0
        count_evaluate_error = 0
        count_other_execution_error = 0
        other_failure = 0
        for ts in testsets.values():
            # ignore test cases for XQuery, and 3.0
            ignore_all_in_testset = False
            if ts.spec_dependencies:
                if ('XQ10' in ts.spec_dependencies or
                        'XQ10+' in ts.spec_dependencies or
                        'XP30' in ts.spec_dependencies or
                        'XP30+' in ts.spec_dependencies or
                        'XQ30' in ts.spec_dependencies or
                        'XQ30+' in ts.spec_dependencies or
                        'XP31' in ts.spec_dependencies or
                        'XP31+' in ts.spec_dependencies or
                        'XQ31' in ts.spec_dependencies or
                        'XQ31+' in ts.spec_dependencies
                ):
                    ignore_all_in_testset = True
            for tc in ts.testcases:
                if test_name is None or test_name in tc.name:
                    count_all += 1
                    if ignore_all_in_testset:
                        count_ignore += 1
                        continue
                    # ignore test cases for XQuery, and 3.0
                    if tc.spec_dependencies:
                        if ('XQ10' in tc.spec_dependencies or
                                'XQ10+' in tc.spec_dependencies or
                                'XP30' in tc.spec_dependencies or
                                'XP30+' in tc.spec_dependencies or
                                'XQ30' in tc.spec_dependencies or
                                'XQ30+' in tc.spec_dependencies or
                                'XP31' in tc.spec_dependencies or
                                'XQ31' in tc.spec_dependencies or
                                'XQ31+' in tc.spec_dependencies
                        ):
                            count_ignore += 1
                            continue
                        # print("DEPS: " + str(tc.spec_dependencies))
                    # ignore tests that rely on higher-order function such as array:sort()
                    if tc.feature_dependencies:
                        if 'higherOrderFunctions' in tc.feature_dependencies:
                            count_ignore += 1
                            continue
                    if tc.name in SKIP_TESTS:
                        count_none += 1
                        continue
                    test_context = TestContext(environments, ts, tc, verbose=args.verbose)
                    try:
                        result = tc.run(test_context)
                        if result is None:
                            count_none += 1
                        if result is False:
                            if args.report:
                                report["failed"].append(tc.name)
                            count_false += 1
                        if result is True:
                            if args.report:
                                report["success"].append(tc.name)
                            count_true += 1
                        count += 1
                    except ParseError as parseError:
                        if args.verbose >= 2:
                            print("failure in parsing test statement for test " + tc.name)
                            print("%s: %s" % (str(type(parseError)), str(parseError)))
                        if args.verbose >= 5:
                            traceback.print_exc()
                        if args.report:
                            report["parse_error"].append(tc.name)
                        count_parse_error += 1
                    except EvaluateError as evalError:
                        if args.verbose >= 2:
                            print("failure in evaluating test statement for test " + tc.name)
                            print("%s: %s" % (str(type(evalError)), str(evalError)))
                        if args.verbose >= 5:
                            traceback.print_exc()
                        if args.report:
                            report["evaluate_error"].append(tc.name)
                        count_evaluate_error += 1
                    except ExecutionError as execError:
                        if str(execError) == "Unimplemented assert_permutation":
                            count_skipped += 1
                        else:
                            if args.verbose >= 2:
                                print("failure in executing testcase for test " + tc.name)
                                print("%s: %s" % (str(type(execError)), str(execError)))
                            if args.verbose >= 5:
                                traceback.print_exc()
                            if args.report:
                                report["execute_error"].append(tc.name)
                            count_other_execution_error += 1
                    except Exception as exc2:
                        if args.verbose >= 0:
                            print("failure in test code for test " + tc.name)
                            print("%s: %s" % (str(type(exc2)), str(exc2)))
                        if args.verbose >= 5:
                            traceback.print_exc()
                        if args.report:
                            report["testcode_error"].append(tc.name)
                        other_failure += 1

        if args.verbose >= 1:
            print("%d testcases read" % count_all)
            print("%d testcases ignored" % count_ignore)
            print("%d testcases skipped" % count_none)
            print("%d testcases run" % count)
            print("")
            print("%d errors while parsing test statement" % count_parse_error)
            print("%d errors while evaluating test statement" % count_evaluate_error)
            print("%d other errors while executing testcase" % count_other_execution_error)
            print("%d errors from test code" % other_failure)
            print("%d success" % count_true)
            print("%d failed" % count_false)

        if args.report:
            report["summary"] = OrderedDict()
            report["summary"]["read"] = count_all
            report["summary"]["ignored"] = count_ignore
            report["summary"]["skipped"] = count_none
            report["summary"]["run"] = count
            report["summary"]["parse_error"] = count_parse_error
            report["summary"]["evaluate_error"] = count_evaluate_error
            report["summary"]["execute_error"] = count_other_execution_error
            report["summary"]["testcode_error"] = other_failure
            report["summary"]["success"] = count_true
            report["summary"]["failed"] = count_false
            with open(args.report, 'w') as outfile:
                outfile.write(json.dumps(report, indent=2))


if __name__ == '__main__':
    sys.exit(main())
