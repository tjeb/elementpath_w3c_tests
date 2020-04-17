import os


def print_snippet(snippet):
    print(etree.tostring(snippet, pretty_print=True).decode("utf-8"))


class WorkingDirectory(object):
    def __init__(self, new_directory):
        self.new_directory = new_directory
        self.original_directory = os.getcwd()

    def __enter__(self):
        os.chdir(self.new_directory)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_directory)