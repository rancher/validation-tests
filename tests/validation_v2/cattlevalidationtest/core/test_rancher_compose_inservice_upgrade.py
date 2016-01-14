from common_fixtures import *  # NOQA
from test_services_volumemount import validate_volume_mount

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST
LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
INSERVICE_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                'resources/inservicedc')

logger = logging.getLogger(__name__)


if_compose_data_files = pytest.mark.skipif(
    not os.path.isdir(INSERVICE_SUBDIR),
    reason='Docker compose files directory location not set/ does not Exist')


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_confirm(super_client, client,
                                                   rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service(super_client, service, {"test1": "value1"}, 0)
    check_config_for_service(super_client, service, {"test1": "value2"}, 1)
    # Check for default settings
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 2
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 1000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value2"}, 1)
    containers = get_service_container_list(super_client, service, 0)
    assert len(containers) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_rollback(super_client, client,
                                                    rancher_compose_container):
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d ",
        "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --upgrade -d --batch-size 3 --interval 500", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service(super_client, service, {"test1": "value1"}, 0)
    check_config_for_service(super_client, service, {"test1": "value2"}, 1)

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 3
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 500
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)
    containers = get_service_container_list(super_client, service, 0)
    assert len(containers) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_delete(super_client, client,
                                                  rancher_compose_container):
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --upgrade -d --batch-size 1 --interval 750", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service(super_client, service, {"test1": "value1"}, 0)
    check_config_for_service(super_client, service, {"test1": "value2"}, 1)
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 1
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 750
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Delete environment

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "rm -f", "Deleted")
    wait_for_condition(
        client, service,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)
    service = client.reload(service)
    assert service.state == "removed"
    containers = get_service_container_list(super_client, service)
    assert len(containers) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_primary(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_2.yml", env_name,
        "up --upgrade -d --batch-size 10 --interval 2000", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 10
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 2000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_2.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_primary_rollback(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_2.yml", env_name,
        "up --upgrade -d --batch-size 0 --interval 2000", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 1
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 2000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_2.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_sidekick(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_3.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_sidekick_rollback(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_3.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_both_sidekicks(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")
    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_both_sidekicks_rollback(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")
    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_all(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0, primary=False)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 0, primary=False)

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)

    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_all_rollback(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0, primary=False)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 0, primary=False)

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)

    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_only_primary(
        super_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_2.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_2.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    validate_volume_mount(super_client, service, env_name+"_test1",
                          [env_name+"_test1_sk1"])
    validate_volume_mount(super_client, service, env_name+"_test1_sk1",
                          [env_name+"_test1_sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_only_primary_rollback(
        super_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_2.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_2.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    validate_volume_mount(super_client, service, env_name+"_test1",
                          [env_name+"_test1_sk1"])
    validate_volume_mount(super_client, service, env_name+"_test1_sk1",
                          [env_name+"_test1_sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick1(
        super_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "stopped")
    check_container_state(client, sk2_containers, "running")

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_3.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    validate_volume_mount(super_client, service, env_name+"_test1",
                          [env_name+"_test1_sk1"])
    validate_volume_mount(super_client, service, env_name+"_test1_sk1",
                          [env_name+"_test1_sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick1_rollback(
        super_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)
    sk2_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1_sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "stopped")
    check_container_state(client, sk2_containers, "running")

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_3.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)

    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    validate_volume_mount(super_client, service, env_name+"_test1",
                          [env_name+"_test1_sk1"])
    validate_volume_mount(super_client, service, env_name+"_test1_sk1",
                          [env_name+"_test1_sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick2(
        super_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "stopped")

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)

    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0
    validate_volume_mount(super_client, service, env_name+"_test1",
                          [env_name+"_test1_sk1"])
    validate_volume_mount(super_client, service, env_name+"_test1_sk1",
                          [env_name+"_test1_sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick2_rollback(
        super_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        super_client, service, env_name+"_test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "stopped")

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        super_client, service, env_name+"_test1_sk2",
        {"testsk2": "value1"}, 1, primary=False)

    container_list = get_service_container_list(super_client, service,
                                                managed=0)
    assert len(container_list) == 0

    validate_volume_mount(super_client, service, env_name+"_test1",
                          [env_name+"_test1_sk1"])
    validate_volume_mount(super_client, service, env_name+"_test1_sk1",
                          [env_name+"_test1_sk2"])
    delete_all(client, [env])


def check_config_for_service(super_client, service, labels, managed):
    containers = get_service_container_list(super_client, service, managed)
    assert len(containers) == service.scale
    for con in containers:
        for key in labels.keys():
            assert con.labels[key] == labels[key]
        if managed == 1:
            con.state = "running"
        else:
            con.state = "stopped"
    if managed:
        for key in labels.keys():
            service_labels = service.launchConfig["labels"]
            assert service_labels[key] == labels[key]


def check_config_for_service_sidekick(super_client, service, service_name,
                                      labels, managed, primary=True):
    containers = get_service_containers_with_name(
        super_client, service, service_name, managed)
    assert len(containers) == service.scale
    for con in containers:
        for key in labels.keys():
            assert con.labels[key] == labels[key]
        if managed == 1:
            con.state = "running"
        else:
            con.state = "stopped"
    print service
    if managed:
        for key in labels.keys():
            if primary:
                service_labels = service.launchConfig["labels"]
            else:
                sk_name = service_name.split("_")[-1]
                print sk_name
                sl_configs = service.secondaryLaunchConfigs
                for sl_config in sl_configs:
                    if sl_config["name"] == sk_name:
                        service_labels = sl_config["labels"]
            assert service_labels[key] == labels[key]


def check_container_state(client, containers, state):
    for con in containers:
        con = client.reload(con)
        assert con.state == state
