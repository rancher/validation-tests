from common_fixtures import *  # NOQA
import os

if_upgrade_testing = pytest.mark.skipif(
    os.environ.get("UPGRADE_TESTING") != "true",
    reason='UPGRADE_TESTING is not true')

pre_upgrade_namespace = ""
post_upgrade_namespace = ""
pre_port_ext = ""
post_port_ext = ""


@pytest.fixture(scope='session')
def get_env():
    global pre_upgrade_namespace
    global post_upgrade_namespace
    global pre_port_ext
    global post_port_ext
    pre_upgrade_namespace = os.environ.get("PRE_UPGRADE_NAMESPACE")
    post_upgrade_namespace = os.environ.get("POST_UPGRADE_NAMESPACE")
    pre_port_ext = os.environ.get("PRE_PORT_EXT")
    post_port_ext = os.environ.get("POST_PORT_EXT")


@if_upgrade_testing
def test_pre_upgrade_validate_stack(kube_hosts, get_env):
    input_config = {
        "namespace": pre_upgrade_namespace,
        "port_ext": pre_port_ext
    }
    k8s_create_stack(input_config)
    k8s_validate_stack(input_config)


@if_upgrade_testing
def test_post_upgrade_validate_stack(kube_hosts, get_env):
    # Validate pre upgrade stack after the upgrade
    input_config = {
        "namespace": pre_upgrade_namespace,
        "port_ext": pre_port_ext
    }
    k8s_validate_stack(input_config)
    k8s_modify_stack(input_config)

    # Create and validate new stack on the upgraded setup
    input_config = {
        "namespace": post_upgrade_namespace,
        "port_ext": post_port_ext
    }
    k8s_create_stack(input_config)
    k8s_validate_stack(input_config)
