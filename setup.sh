#! /bin/bash

(
    set -x
    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r py3-requirements.txt
)

(
    set -x
    virtualenv -p python2.7 venv2
    source venv2/bin/activate
    pip install -r py2-requirements.txt
)
