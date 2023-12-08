from distutils.core import setup

setup(
    name = 'ThreadTimeline',
    description = 'Implementation of SeQUeNCe parallel library using Python/C API Interpreters module for sub-interpreters instead of MPI',
    packages = ['thread_timeline'],
    version = '1',
    script_name = './setup.py',
    data_files = ['./setup.py']
)