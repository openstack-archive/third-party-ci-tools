#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
VENV=${DIR}/.venv

INSTALL_REQS=False
if [ ! -d ${VENV} ]; then
    virtualenv ${VENV}
    INSTALL_REQS=True
fi

source ${VENV}/bin/activate

if [ ${INSTALL_REQS} == True ]; then
    pip install -r ${DIR}/requirements.txt
fi