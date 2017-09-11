from common_fixtures import *  # NOQA
import os

upgrade_loops = int(os.environ.get("UPGRADE_LOOPS", "10"))
validation_enabled = str(os.environ.get("VALIDATION_ENABLED",
                                        'false').lower())
forced_stack = str(os.environ.get("FORCED_STACK", "kubernetes"))

if_stress_testing = pytest.mark.skipif(
    os.environ.get("STRESS_TESTING") != "true",
    reason='STRESS_TESTING is not true')

if_validation_enabled = pytest.mark.skipif(
    os.environ.get("VALIDATION_ENABLED") != "true",
    reason='VALIDATION_ENABLED is not true')


@if_stress_testing
@if_validation_enabled
def test_k8s_dashboard(kube_hosts):
    assert k8s_check_dashboard()


@if_stress_testing
@if_validation_enabled
def test_deploy_k8s_yaml(kube_hosts):
    input_config = {
        "namespace": "stresstest-ns-1",
        "port_ext": "1"
    }
    k8s_create_stack(input_config)
    time.sleep(120)
    k8s_validate_stack(input_config)


@if_stress_testing
@if_validation_enabled
def test_validate_helm(kube_hosts):
    assert k8s_validate_helm()


@if_stress_testing
def test_upgrade_validate_k8s(kube_hosts, rancher_cli_container):
    input_config = {
        "namespace": "stresstest-ns-0",
        "port_ext": "0"
    }

    for i in range(upgrade_loops):
        logger.info("Starting Loop: " + str(i+1))
        k8s_force_upgrade_stack(forced_stack)
        k8s_waitfor_infra_stacks()
        time.sleep(600)

        if validation_enabled is 'true':
            k8s_check_cluster_health(input_config)

            input_config = {
                "namespace": "stresstest-ns-"+str(i+1),
                "port_ext": str(i+1)
            }
        else:
            assert k8s_validate_kubectl()

        logger.info("End of Loop: " + str(i+1))
