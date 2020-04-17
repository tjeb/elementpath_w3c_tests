import os
from lxml import etree
from util import WorkingDirectory

nsmap = {None: "http://www.w3.org/2010/09/qt-fots-catalog"}


class Schema(object):
    """Represents an XML schema as pointed to in test xml files (currently not used)"""

    def __init__(self, element):
        self.uri = element.attrib.get('uri')
        self.file = element.attrib.get('file')
        description_xml = element.find('description', namespaces=nsmap)
        if description_xml is not None:
            self.description = description_xml.text
        else:
            self.description = ""

        # TODO: add schema tools?


class Source(object):
    """Represents a source file as used in environment xml settings"""

    def __init__(self, element):
        self.role = element.attrib.get('role')
        self.uri = element.attrib.get('uri')
        self.file = element.attrib['file']
        description_xml = element.find('description', namespaces=nsmap)
        if description_xml is not None:
            self.description = description_xml.text
        else:
            self.description = ""

        try:
            self.xml = etree.parse(self.file)
        except etree.XMLSyntaxError:
            self.xml = None


class Environment(object):
    def __init__(self, element):
        self.namespaces = {}
        self.schema = None
        self.context_xml = None
        self.variables_sources = {}
        if 'name' in element.attrib:
            self.name = element.attrib['name']
        else:
            self.name = 'anonymous'

        for namespace_xml in element.findall('namespace', namespaces=nsmap):
            self.namespaces[namespace_xml.attrib['prefix']] = namespace_xml.attrib['uri']

        for schema_xml in element.findall('schema', namespaces=nsmap):
            if self.schema is not None:
                raise Exception("TODO: more than one schema?")
            self.schema = Schema(schema_xml)

        for source_xml in element.findall('source', namespaces=nsmap):
            # self.sources.append = Source(source_xml)
            source = Source(source_xml)
            if source.role == ".":
                self.context_xml = source
            else:
                self.variables_sources[source.role] = source


class ExecutionError(Exception):
    pass


class ParseError(ExecutionError):
    pass


class EvaluateError(ExecutionError):
    pass


def create_and_run_test(test_context, may_fail=False):
    """Helper function to parse and evaluate tests with elementpath"""
    # if may_fail is true, raise the exception instead of printing and aborting
    env_ref = test_context.testcase.environment_ref
    if env_ref:
        if env_ref in test_context.testset.environments:
            environment = test_context.testset.environments[env_ref]
        elif env_ref in test_context.environments:
            environment = test_context.environments[env_ref]
        else:
            raise Exception("Unknown environment %s in test case %s" % (env_ref, test_context.testcase.name))
    elif test_context.testcase.environment:
        environment = test_context.testcase.environment
    else:
        environment = None

    if environment is not None and environment.context_xml:
        xml_doc = environment.context_xml.xml
    else:
        xml_doc = etree.XML("<empty/>")

    try:
        parser = XPath2Parser()
        root_node = parser.parse(test_context.testcase.test)
        context = XPathContext(root=xml_doc)
        try:
            result = root_node.evaluate(context)
        except Exception as evalError:
            if test_context.verbose >= 2:
                print("Error evaluating %s: %s" % (test_context.testcase.test, str(evalError)))
            raise EvaluateError(evalError)
    except Exception as exc:
        if test_context.verbose >= 2:
            print("Error parsing %s: %s" % (test_context.testcase.test, str(exc)))
        raise ParseError(exc)
    if test_context.verbose >= 5:
        print("Result of evaluation: %s" % str(result))
    return result


class TestSet(object):
    """Represents a testset as read from the catalog file and the setset xml file itself"""

    def __init__(self, element):
        self.name = element.attrib['name']
        self.file = element.attrib['file']
        self.environments = {}
        self.testcases = []

        self.spec_dependencies = []
        self.feature_dependencies = []
        self.xml_version_dependency = None
        self.xsd_version_dependency = None

        full_path = os.path.abspath(self.file)
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        with WorkingDirectory(directory):
            xml_root = etree.parse(filename).getroot()

            self.description = xml_root.find('description', namespaces=nsmap).text

            for dependency_xml in xml_root.findall('dependency', namespaces=nsmap):
                dep_type = dependency_xml.attrib['type']
                value = dependency_xml.attrib['value']
                if dep_type == 'spec':
                    self.spec_dependencies.extend(value.split(' '))
                elif dep_type == 'feature':
                    self.feature_dependencies.append(value)
                elif dep_type == 'xml-version':
                    self.xml_version_dependency = value
                elif dep_type == 'xsd-version':
                    self.xsd_version_dependency = value
                elif dep_type == 'default-language' or dep_type == 'language':
                    pass
                elif dep_type == 'limits' or dep_type == 'calendar':
                    # TODO What do we need to do here?
                    pass
                else:
                    # print("unknown dependency type: %s = %s" % (dep_type, value))
                    # sys.exit(4)
                    # ignore other deps for now
                    pass

            for environment_xml in xml_root.findall('environment', namespaces=nsmap):
                environment = Environment(environment_xml)
                self.environments[environment.name] = environment

            for testcase_xml in xml_root.findall('test-case', namespaces=nsmap):
                self.testcases.append(TestCase(testcase_xml, self))


class TestContext(object):
    """
    The context in which tests are run, includes the global environments, the testset, the testcase, and verbosity.
    """

    def __init__(self, environments, testset, testcase, verbose):
        # Data about tests and environment
        self.environments = environments
        self.testset = testset
        self.testcase = testcase

        # other data
        self.verbose = verbose


class TestCase(object):
    """Represents a test case as read from a testset file"""

    def __init__(self, element, testset):
        self.testset_file = testset.file
        self.name = testset.name + "." + element.attrib['name']
        self.description = element.find('description', namespaces=nsmap).text
        self.test = element.find('test', namespaces=nsmap).text
        self.result = Result(element.find('result', namespaces=nsmap).find("*"))
        self.environment_ref = None
        self.environment = None
        self.spec_dependencies = []
        self.feature_dependencies = []
        self.xml_version_dependency = None
        self.xsd_version_dependency = None

        for dependency_xml in element.findall('dependency', namespaces=nsmap):
            dep_type = dependency_xml.attrib['type']
            value = dependency_xml.attrib['value']
            if dep_type == 'spec':
                self.spec_dependencies.extend(value.split(' '))
            elif dep_type == 'feature':
                self.feature_dependencies.append(value)
            elif dep_type == 'xml-version':
                self.xml_version_dependency = value
            elif dep_type == 'xsd-version':
                self.xsd_version_dependency = value
            elif dep_type == 'default-language' or dep_type == 'language':
                pass
            elif dep_type == 'limits' or dep_type == 'calendar':
                # TODO What do we need to do here?
                pass
            else:
                # print("unknown dependency type: %s = %s" % (dep_type, value))
                # sys.exit(4)
                # ignore other deps for now
                pass

        environment_xml = element.find('environment', namespaces=nsmap)
        if environment_xml is not None:
            if 'ref' in environment_xml.attrib:
                self.environment_ref = environment_xml.attrib['ref']
            else:
                self.environment = Environment(environment_xml)

    def print(self):
        print("Test: " + self.name)
        print("Description: " + self.description)
        print("Testset file: %s" % self.testset_file)
        print("Xpath test: " + self.test)
        print("Environment ref: " + str(self.environment_ref))
        print("Environment: " + str(self.environment))

    def run(self, test_context):
        if test_context.verbose >= 5:
            print("")
            self.print()
        return self.result.validate(test_context)

class Result(object):
    """This is the class that handles running individual test result checks (i.e. compares the evaluation output against the requirements), such as 'assert-eq' etc."""

    def __init__(self, element):
        # Get the internal element, and remove comment
        self.type = etree.QName(element.tag).localname
        self.value = element.text
        self.children = []
        for child in element.findall("*"):
            self.children.append(Result(child))
        # if self.value is None:
        #    raise Exception("not implemented: result type %s" % self.type)
        vmethod = self.type.replace("-", "_")
        if vmethod == 'assert':
            self._validate = self.xassert
        elif vmethod == 'not':
            self._validate = self.xnot
        elif hasattr(self, vmethod):
            self._validate = getattr(self, vmethod)

    def validate(self, test_context):
        if test_context.verbose >= 5:
            print("Calling validate on Result for type %s" % self.type)
            print("Expecting value: %s" % self.value)
        return self._validate(test_context)

    def _validate(self, test_context):
        raise Exception("Not Implemented: Result for %s" % self.type)

    def all_of(self, test_context):
        if len(self.children) == 0:
            raise Exception("all-of called with no children")
        for child in self.children:
            if not child.validate(test_context):
                return False
        return True

    def any_of(self, test_context):
        if len(self.children) == 0:
            raise Exception("any-of called with no children")
        for child in self.children:
            try:
                if child.validate(test_context):
                    return True
            except Exception:
                # This will print an error but continue regardless
                # TODO: how to improve that?
                # See K-StringFunc-2 for an example where this is an issue
                pass
        return False

    def assert_eq(self, test_context):
        output = create_and_run_test(test_context)

        parser = XPath2Parser()
        root_node = parser.parse(self.value)
        context = XPathContext(root=etree.XML("<empty/>"))
        result = root_node.evaluate(context)

        if type(output) == list and len(output) == 1:
            output = output[0]
        # print("result: '%s' (%s)" % (str(result), str(type(result))))
        return result == output

    def assert_type(self, test_context):
        # print("Context:")
        # test_context.testcase.print()
        output = create_and_run_test(test_context)
        if self.value == 'xs:anyURI':
            result = isinstance(output, str)
        elif self.value == 'xs:boolean':
            result = isinstance(output, bool)
        elif self.value == 'xs:date':
            result = isinstance(output, elementpath.datatypes.Date10)
        elif self.value == 'xs:double':
            result = isinstance(output, float)
        elif self.value == 'xs:dateTime':
            result = isinstance(output, elementpath.datatypes.DateTime10)
        elif self.value == 'xs:dayTimeDuration':
            result = isinstance(output, elementpath.datatypes.Timezone)
        elif self.value == 'xs:decimal':
            result = isinstance(output, decimal.Decimal)
        elif self.value == 'xs:float':
            result = isinstance(output, float)
        elif self.value == 'xs:integer':
            result = isinstance(output, int)
        elif self.value == 'xs:NCName':
            result = isinstance(output, str)
        elif self.value == 'xs:nonNegativeInteger':
            result = isinstance(output, int)
        elif self.value == 'xs:positiveInteger':
            result = isinstance(output, int)
        elif self.value == 'xs:string':
            result = isinstance(output, str)
        elif self.value == 'xs:time':
            result = isinstance(output, elementpath.datatypes.Time)
        elif self.value == 'xs:token':
            result = isinstance(output, str)
        elif self.value == 'xs:unsignedShort':
            result = isinstance(output, int)
        elif self.value.startswith('document-node') or self.value.startswith('element'):
            result = isinstance(output, list)
        else:
            print("unknown type in assert_type: %s (result type is %s), testcase %s" % (self.value, str(type(output)), test_context.testcase.name))
            # print("list: " + str(output))
            sys.exit(1)
        return result

    def assert_string_value(self, test_context):
        output = create_and_run_test(test_context)
        result = output == self.value
        return result

    def error(self, test_context):
        try:
            output = create_and_run_test(test_context, may_fail=True)
            return False
        except Exception:
            return True

    def assert_true(self, test_context):
        output = create_and_run_test(test_context)
        result = output == True
        return result

    def assert_false(self, test_context):
        try:
            output = create_and_run_test(test_context, may_fail=True)
            result = output == False
            return result
        except Exception as exc:
            # print("Failure!")
            # test_context.testcase.print()
            raise exc

    def assert_count(self, test_context):
        output = create_and_run_test(test_context)
        if type(output) == str:
            return int(self.value) == 1
        else:
            return int(self.value) == len(output)

    def xassert(self, test_context):
        # Assert contains an xpath expression whose value must be true
        # The expression may use the variable $result, which is the output of
        # the original test
        output = create_and_run_test(test_context)
        variables = {'result': output}

        parser = XPath2Parser(variables=variables)
        root_node = parser.parse(self.value)
        context = XPathContext(root=etree.XML("<empty/>"))
        result = root_node.evaluate(context)
        return result == True

    def assert_deep_eq(self, test_context):
        output = create_and_run_test(test_context)
        expression = "fn:deep-equal($result, (%s))" % self.value
        variables = {'result': output}

        parser = XPath2Parser(variables=variables)
        root_node = parser.parse(expression)
        context = XPathContext(root=etree.XML("<empty/>"))
        result = root_node.evaluate(context)
        return result == True

    def assert_empty(self, test_context):
        output = create_and_run_test(test_context)
        if output is not None and output != []:
            return False
        else:
            return True

    def assert_permutation(self, test_context):
        # Hmz, TODO: try parsing the output through elementpath
        # If that succeeds sometimes, just raise executionerror
        # Skip!
        return None

        output = create_and_run_test(test_context)
        print("assert permutation")
        print("expect: " + self.value)
        print("get: " + str(output))
        v = self.value
        v = v.replace("true()", "True")
        v = v.replace("false()", "False")
        expect = eval("[ %s ]" % v)

        expect = [str(e) for e in expect]
        output = [str(e) for e in output]

        expect.sort()
        output.sort()
        print("PARSED EXPECT: " + str(expect))
        print("get: " + str(output))
        return expect == output

    def assert_serialization_error(self, test_context):
        # TODO: this currently succeeds on any error
        try:
            output = create_and_run_test(test_context)
            return False
        except Exception as exc:
            return True

    def assert_xml(self, test_context):
        output = create_and_run_test(test_context)
        if output is None:
            return False
        if type(output) == list:
            parts = []
            for el in output:
                if str(type(el)) == "<class 'elementpath.xpath_nodes.Text'>":
                    parts.append(str(el))
                else:
                    parts.append(etree.tostring(el).decode('utf-8').strip())
            xml_str = "".join(parts)
        else:
            xml_str = etree.tostring(output, pretty_print=True).decode('utf-8').strip()
        if test_context.verbose >= 5:
            print("Final XML string to compare: '%s'" % xml_str)
        return xml_str == self.value

    def serialization_matches(self, test_context):
        output = create_and_run_test(test_context)
        regex = re.compile(self.value)
        match = regex.match(output)
        return match

    def xnot(self, test_context):
        if len(self.children) != 1:
            raise Exception("<not> called with zero or more than 1 children")
        child = self.children[0]
        return not child.validate(test_context)
