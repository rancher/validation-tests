# Validation tests for Rancher
------------------------------
### Pre-reqs

A running Rancher Environment.


To run from scratch:

1. [cloudnautique/10acre-ranch](https://github.com/cloudnautique/10acre-ranch)
2. Tox


### Running

If you have a running Rancher environment set `CATTLE_TEST_URL` environment variable.
If that variable is not set, the tests will attempt to provision one.

To run:

```
git clone git@github.com:rancher/validation-tests.git
cd validation-tests
./scripts/test
```
## Contact
For bugs, questions, comments, corrections, suggestions, etc., open an issue in
 [rancher/rancher](//github.com/rancher/rancher/issues) with a title starting with `[Validation-Tests] `.

Or just [click here](//github.com/rancher/rancher/issues/new?title=%5BValidation-Tests%5D%20) to create a new issue.

PLEASE READ BELOW FOR RUNNING V2 TESTS:
**************************************

1- Environment global variables required for v2 version of tests (upgrade support) to work depends on the type of tests, for cattle:

```
export CATTLE_TEST_URL=http://x.x.x.x:8080
export CATTLE_RESTART_SLEEP_INTERVAL=10
export ACCESS_KEY=xxxxx
export SECRET_KEY=xxxxx
export PROJECT_ID=1a5
```

For k8s:

```
export CATTLE_TEST_URL=http://x.x.x.x:8080
export TEST_CATALOG=false
export RANCHER_ORCHESTRATION=k8s
export KUBECTL_VERSION=v1.6.0
export DIGITALOCEAN_KEY=xxxxxxxxxxxxxx
export K8S_DEPLOY=False
export K8S_STATIC_ENV=k8s
export K8S_DEPLOY_DEFAULT=False
export LIBRARY_CATALOG_URL=https://github.com/rancher/rancher-catalog
export LIBRARY_CATALOG_BRANCH=master
export OVERRIDE_CATALOG=False
export ACCESS_KEY=xxxxx
export SECRET_KEY=xxxxx
export PROJECT_ID=1a5
```

2- Edit the tox.ini file in v2_validation directory `tests/v2_validation/tox.ini` to run the specific tests you need and make sure to add `passenv=*`, it should look something like that:

```
[tox]
envlist=py27, flake8

[testenv]
deps=-rrequirements.txt
commands=py.test --durations=20 --junitxml=validationTestsJunit.xml cattlevalidationtest/core/test_k8s.py::test_k8s_env_rollingupdates {posargs}
passenv=*

[testenv:flake8]
deps=-rrequirements.txt
commands=flake8 cattlevalidationtest

[testenv:githubauthenv]
deps=-rrequirements.txt
commands=py.test --duration=20 --junitxml=validationTestsJunit.xml cattlevalidationtest/core/test_github.py {posargs}
```

The previous example will run the `test_k8s_env_rollingupdates` test case in `test_k8s.py` validation

3- Change the line in scripts/test to `pushd ./tests/v2_validation` instead of `pushd ./tests/validation`

4- Run the tests
```
./scripts/test
```

# License
Copyright (c) 2014-2015 [Rancher Labs, Inc.](http://rancher.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
