from common_fixtures import *  # NOQA

if_stress_testing = pytest.mark.skipif(
    os.environ.get("STRESS_TESTING") != "true",
    reason='STRESS_TESTING is not true')


@if_stress_testing
def test_k8s_dashboard(kube_hosts):
    assert True
