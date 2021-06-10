#!/bin/bash

set -x
set -eu

DEBUG="${DEBUG:-false}"

TRIM_JOB_NAME=$(basename $JOB_NAME)

if [ "false" != "${DEBUG}" ]; then
    echo "Environment:"
    env | sort
fi

cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )/../" && pwd )"

count=0
while [[ 3 -gt $count ]]; do    
    docker build -q -f Dockerfile -t rancher-16-validation-${TRIM_JOB_NAME}${BUILD_NUMBER} .

    if [[ $? -eq 0 ]]; then break; fi
    count=$(($count + 1))
    echo "Repeating failed Docker build ${count} of 3..."
done
