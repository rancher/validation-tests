# Validation tests for Rancher
------------------------------
### Pre-reqs

A running Rancher Environment.


To run from scratch:

1. Tox


### Running

Running v2-beta validation tests:
**************************************

1 - Environment global variables required for v2 version of tests (upgrade support) to work depends on the type of tests, for cattle:

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

2 - Edit the tox.ini file in v2_validation directory `tests/v2_validation/tox.ini` to run the specific tests if needed, change by adding to the command:

```
[testenv]
deps=-rrequirements.txt
commands=py.test --durations=20 --junitxml=validationTestsJunit.xml cattlevalidationtest/core/test_k8s.py::test_k8s_env_rollingupdates {posargs}
passenv=*
```

The previous example will run the `test_k8s_env_rollingupdates` test case in `test_k8s.py` validation

3 - Run the tests
```
./scripts/test_v2-beta
```

## Contact
For bugs, questions, comments, corrections, suggestions, etc., open an issue in
 [rancher/rancher](//github.com/rancher/rancher/issues) with a title starting with `[Validation-Tests] `.
Or just [click here](//github.com/rancher/rancher/issues/new?title=%5BValidation-Tests%5D%20) to create a new issue.

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
