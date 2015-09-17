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

Environment global variables required for v2 version of tests (upgrade support) to work:

TEST_ROOT_DIR=<path to v2> Example: /Users/aruneli/rancher/validation-tests/v2
RANCHER_SERVER_VERSION=<current version> Example: 0.37.0
CATTLE_TEST_URL= <url> Example: http://104.197.121.156:8080
RANCHER_SERVER=<Ip Address of host where Rancher Server is running>

ssh-copy-id should be available in client running tests



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

