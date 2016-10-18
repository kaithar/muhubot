#! /bin/bash

if [[ -e nodes/py3_$1.py || -e nodes/py3_$1 ]]; then
    echo "--- Detected nodes/py3_$1.py or nodes/py3_$1"
    source venv/bin/activate
    python3 node_process.py py3_$1
elif [[ -e nodes/py2_$1.py || -e nodes/py2_$1 ]]; then
    echo "--- Detected nodes/py2_$1.py or nodes/py2_$1"
    source venv2/bin/activate
    python2 node_process.py py2_$1
else
    echo "Can't find nodes/py2_$1.py, nodes/py3_$1.py or similarly named directories"
fi
