V2 version Validation test scripts for Cattle

PLEASE READ BELOW FOR RUNNING V2 TESTS:
**************************************

Environment global variables required for v2 version of tests (upgrade support) to work:

TEST_ROOT_DIR = <path to v2> Example: /Users/aruneli/rancher/validation-tests/tests/validation_v2
RANCHER_SERVER_VERSION=<current version> Example: 0.37.0
CATTLE_TEST_URL= <url> Example: http://104.197.121.156:8080
RANCHER_SERVER=<Ip Address of host where Rancher Server is running>

ssh-copy-id should be available in client running tests