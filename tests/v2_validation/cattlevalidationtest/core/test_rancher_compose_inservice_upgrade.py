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
def test_rancher_compose_inservice_upgrade_confirm(admin_client, client,
                                                   rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 0)
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)
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
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)
    containers = get_service_container_list(admin_client, service, 0)
    assert len(containers) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_rollback(admin_client, client,
                                                    rancher_compose_container):
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d ",
        "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --upgrade -d --batch-size 3 --interval 500", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 0)
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 3
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 500
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)
    containers = get_service_container_list(admin_client, service, 0)
    assert len(containers) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_delete(admin_client, client,
                                                  rancher_compose_container):
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_2.yml", env_name,
        "up --upgrade -d --batch-size 1 --interval 750", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 0)
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)
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
    containers = get_service_container_list(admin_client, service)
    assert len(containers) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_primary(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_2.yml", env_name,
        "up --upgrade -d --batch-size 10 --interval 2000", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
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
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_primary_rollback(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_2.yml", env_name,
        "up --upgrade -d --batch-size 0 --interval 2000", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
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
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_sidekick(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
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
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_sidekick_rollback(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client,
        service, env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
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
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_both_sidekicks(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")
    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_both_sidekicks_rollback(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_4.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")
    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_all(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0, primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0, primary=False)

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_all_rollback(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0, primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0, primary=False)

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_5.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_only_primary(
        admin_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_2.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
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
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_only_primary_rollback(
        admin_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_2.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
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
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick1(
        admin_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
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
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    validate_volume_mount(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick1_rollback(
        admin_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_3.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
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
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)

    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick2(
        admin_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "stopped")

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    validate_volume_mount(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick2_rollback(
        admin_client, client, rancher_compose_container, socat_containers):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice3_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "stopped")

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice3_4.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0

    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_confirm_retainip(
        admin_client, client, rancher_compose_container):

    # Create an environment using up
    env_name = random_str().replace("-", "")
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice1_retainip_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 6):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_2.yml", env_name,
        "up --upgrade -d", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value1"}, 0)
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)
    # Check for default settings
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 2
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 1000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_2.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)
    containers = get_service_container_list(admin_client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the new containers were retained after upgrade
    for i in range(1, 6):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            != containers[0].externalId

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_rollback_retainip(
        admin_client, client, rancher_compose_container):

    # Create an environment using up
    env_name = random_str().replace("-", "")
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice1_retainip_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    assert service.retainIp

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 6):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 6):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_2.yml", env_name,
        "up --upgrade -d --batch-size 3 --interval 500", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value1"}, 0)
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 3
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 500
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_2.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)
    containers = get_service_container_list(admin_client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the containers after rollback were retained after upgrade
    for i in range(1, 6):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            == containers[0].externalId

    delete_all(client, [env])


@if_compose_data_files
# known issue 5476
def test_rancher_compose_inservice_upgrade_set_retainip_during_upgrade(
        admin_client, client, rancher_compose_container):
    # Create an environment using up
    env_name = random_str().replace("-", "")
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    print service
    assert service.state == "active"
    assert service.retainIp is None
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 3):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_retainip_2.yml", env_name,
        "up --upgrade -d", "Upgrading", "rc_inservice2_retainip_2.yml")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value1"}, 0)
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)
    # Check for default settings
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 2
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 1000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_2.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)
    containers = get_service_container_list(admin_client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the new containers were retained after upgrade
    for i in range(1, 3):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            != containers[0].externalId

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_retainip_during_upgrade_rollback(
        admin_client, client, rancher_compose_container):

    # Create an environment using up
    env_name = random_str().replace("-", "")
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_1.yml", env_name,
        "up -d", "Creating stack", "rc_inservice1_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    assert service.retainIp is None
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 3):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 3):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    env, service = get_env_service_by_name(client, env_name, "test1")
    assert service.state == "active"
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_2.yml", env_name,
        "up --upgrade -d --batch-size 3 --interval 500", "Upgrading",
        "dc_inservice1_retainip_2.yml")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert service.retainIp
    check_config_for_service(admin_client, service, {"test1": "value1"}, 0)
    check_config_for_service(admin_client, service, {"test1": "value2"}, 1)

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 3
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 500
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice1_retainip_2.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    assert service.retainIp is None
    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)
    containers = get_service_container_list(admin_client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the containers after rollback were retained after upgrade
    for i in range(1, 3):
        container_name = get_container_name(env, service, str(i))
        containers = admin_client.list_container(name=container_name,
                                                 removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            == containers[0].externalId

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_remove_sk(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_rmsk.yml", env_name,
        "up --upgrade -d ", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert len(service.secondaryLaunchConfigs) == 1
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert not check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_rmsk.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"

    assert len(service.secondaryLaunchConfigs) == 1
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert not check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_remove_sk_rollback(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_rmsk.yml", env_name,
        "up --upgrade -d ", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert len(service.secondaryLaunchConfigs) == 1
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert not check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_rmsk.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"

    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1,  primary=False)

    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_add_sk(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_addsk.yml", env_name,
        "up --upgrade -d ", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert len(service.secondaryLaunchConfigs) == 3
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk3",
        {"testsk3": "value1"}, 1,  primary=False)

    # Confirm upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_addsk.yml", env_name,
        "up --confirm-upgrade -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    assert len(service.secondaryLaunchConfigs) == 3
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk3",
        {"testsk3": "value1"}, 1,  primary=False)

    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_add_sk_rollback(
        admin_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_1.yml", env_name,
        "up -d",
        "Creating stack", "rc_inservice2_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    assert service.state == "active"
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade environment using up --upgrade
    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_addsk.yml", env_name,
        "up --upgrade -d ", "Upgrading")
    service = client.reload(service)
    assert service.state == "upgraded"
    assert len(service.secondaryLaunchConfigs) == 3
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk3",
        {"testsk3": "value1"}, 1,  primary=False)

    # Rollback upgrade

    launch_rancher_compose_from_file(
        client, INSERVICE_SUBDIR, "dc_inservice2_rmsk.yml", env_name,
        "up --rollback -d", "Started")
    service = client.reload(service)
    assert service.state == "active"
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert not check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        admin_client, service, env_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1,  primary=False)

    check_config_for_service_sidekick(
        admin_client, service,
        env_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1,  primary=False)

    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_list(admin_client, service,
                                                managed=0)
    assert len(container_list) == 0
    delete_all(client, [env])


def check_config_for_service_sidekick(admin_client, service, service_name,
                                      labels, managed, primary=True):
    containers = get_service_containers_with_name(
        admin_client, service, service_name, managed)
    assert len(containers) == service.scale
    for con in containers:
        for key in labels.keys():
            assert con.labels[key] == labels[key]
        if managed == 1:
            assert con.state == "running"
        else:
            assert con.state == "stopped"
    print service
    if managed:
        for key in labels.keys():
            if primary:
                service_labels = service.launchConfig["labels"]
            else:
                sk_name = service_name.split("-")[-1]
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


def check_for_sidekick_name_in_service(service, sidekick_name):
    found = False
    for lcs in service.secondaryLaunchConfigs:
        if sidekick_name == lcs.name:
            found = True
            break
    return found
