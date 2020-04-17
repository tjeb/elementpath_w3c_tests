# Elementpath test harness for the w3c XML test suite

This is a test harness to execute the W3C XPath tests with elementpath.

Its main goal is to check that additions and fixes for elementpath don't 
violate the standard, and to show that they improve upon the implementation.

## Status

This is a work in progress; it currently ignores about half of the tests, and there are probably quite a few tests that could be run instead of ignored. There may also be some issues with how tests are checked and reported. If you have any improvements, please submit a pull request.

## Requirements

- The w3c test suite, available at https://github.com/w3c/qt3tests
- elementpath (preferably a git checkout as well), available at https://github.com/sissaschool/elementpath
- python3
- lxml


## Installation

Create a directory to put everything in

    > mkdir ~/ep_tests
    > cd ~/ep_tests

Fetch this repository, the w3c suite and elementpath

    > git clone https://github.com/w3c/qt3tests
    > git clone https://github.com/sissaschool/elementpath
    > git clone https://github.com/tjeb/elementpath_w3c_tests

Setup the environment

    > cd elementpath_w3c_tests
    > python3 -m venv venv
    > source venv/bin/activate
    > pip install -r requirements.txt
    > pip install -e ../elementpath

## Running the test harness

Assuming you have the test suite installed in the directories used in the previous section:

    > cd ~/ep_tests/elementpath_w3c_tests
    > source venv/bin/activate
    > ./execute_tests.py ../qt3tests/catalog.xml

The tests make take a while to run. The output should be something like:

    31424 testcases read
    16497 testcases ignored
    46 testcases skipped
    14019 testcases run

    902 errors while parsing test statement
    0 errors while evaluating test statement
    0 other errors while executing testcase
    0 errors from test code
    10704 success
    3275 failed

You can execute individual tests, or a specific testset, by providing a second positional argument

    > ./execute_tests.py ../qt3tests/catalog.xml fn-abs-2
    1 testcases read
    0 testcases ignored
    0 testcases skipped
    1 testcases run

    0 errors while parsing test statement
    0 errors while evaluating test statement
    0 other errors while executing testcase
    0 errors from test code
    1 success
    0 failed

You can get more verbose output with the -v option; see -h for the verbosity levels.

You can write the test results, including the test names that result in each status, by specifying a filename with the -r option; this will write a report in JSON format to that file.

## Comparing branches of elementpath with the test harness

In order to see a comparison of test results from different branches, you can use the compare_results.py script. Please note that this does git checkouts in the elementpath source branch, so make sure it is clean. Also be aware that this writes some files to /tmp (report_<branch>.json).

    > ./compare_results -g ../elementpath master decimal_type_coercion
    Summary of differences:
        status parse_error: -26
        status evaluate_error: no change
        status execute_error: no change
        status testcode_error: no change
        status success: +26
        status failed: no change

    prod-CastableExpr.CastableAs649 was parse_error, is now success
    prod-CastableExpr.CastableAs650 was parse_error, is now success
    prod-ContextItemExpr.externalcontextitem-3 was parse_error, is now success
    prod-ContextItemExpr.externalcontextitem-4 was parse_error, is now success
    prod-ContextItemExpr.externalcontextitem-5 was parse_error, is now success
    prod-ContextItemExpr.externalcontextitem-6 was parse_error, is now success
    prod-Predicate.filterexpressionhc1 was parse_error, is now success
    prod-Predicate.predicates-9 was parse_error, is now success
    prod-Predicate.predicates-10 was parse_error, is now success
    prod-Predicate.predicates-11 was parse_error, is now success
    prod-Predicate.predicates-12 was parse_error, is now success
    prod-Predicate.predicates-19 was parse_error, is now success
    prod-Predicate.predicates-20 was parse_error, is now success
    prod-Predicate.predicates-21 was parse_error, is now success
    prod-Predicate.predicates-22 was parse_error, is now success
    prod-Predicate.predicates-23 was parse_error, is now success
    prod-Predicate.predicates-27 was parse_error, is now success
    prod-Predicate.predicates-28 was parse_error, is now success
    prod-Predicate.predicatesns-9 was parse_error, is now success
    prod-Predicate.predicatesns-10 was parse_error, is now success
    prod-Predicate.predicatesns-11 was parse_error, is now success
    prod-Predicate.predicatesns-12 was parse_error, is now success
    prod-ValueComp.value-comp-eq-int-3 was parse_error, is now success
    prod-ValueComp.value-comp-eq-int-7 was parse_error, is now success
    prod-ValueComp.value-comp-eq-double-3 was parse_error, is now success
    prod-ValueComp.value-comp-eq-double-7 was parse_error, is now success

compare_results.py can also be used directly with report.json files:

    > ./compare_results -r /tmp/report_master.json /tmp/report_mychanges.json
