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
git clone git@github.com:rancherio/validation-tests.git
cd validation-tests
./scripts/test
```


