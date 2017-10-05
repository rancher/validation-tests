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
def test_rancher_compose_inservice_upgrade_confirm(client,
                                                   rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_1.yml"
    dc_file_upgrade = "dc_inservice1_2.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)

    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)
    # Check for default settings
    assert service.batchSize == 2
    assert service.intervalMillis == 1000
    assert service.startFirst is False

    check_config_for_service(client, service, {"test1": "value2"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_rollback(client,
                                                    rancher_cli_container):
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_1.yml"
    rc_file = "rc_inservice1_1.yml"
    dc_file_upgrade = "dc_inservice1_2.yml"
    upgrade_option = "--batch-size 3 --interval 500"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade,
                            upgrade_option=upgrade_option)
    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 3
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 500
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback upgrade

    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service(client, service, {"test1": "value1"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_delete(client,
                                                  rancher_cli_container):
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_1.yml"
    rc_file = "rc_inservice1_1.yml"
    dc_file_upgrade = "dc_inservice1_2.yml"
    upgrade_option = "--batch-size 1 --interval 750"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade,
                            upgrade_option=upgrade_option)

    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 1
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 750
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Delete stack
    launch_rancher_cli_from_file(
        client, INSERVICE_SUBDIR, stack_name,
        "rm --type service " + stack.name + "/" + service.name, service.id)
    wait_for_condition(
        client, service,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)
    service = client.reload(service)
    assert service.state == "removed"
    containers = get_service_container_managed_list(client, service)
    assert len(containers) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_primary(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_2.yml"
    upgrade_option = "--batch-size 10 --interval 2000"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade,
                            upgrade_option=upgrade_option)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 10
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 2000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_primary_rollback(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_2.yml"
    upgrade_option = "--batch-size 0 --interval 2000"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(
        client, stack_name, service, dc_file_upgrade,
        upgrade_option=upgrade_option)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 1
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 2000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_sidekick(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_3.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service, stack_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_sidekick_rollback(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_3.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service, stack_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        client,
        service, stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_container_state(client, primary_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_both_sidekicks(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_4.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service, stack_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")
    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_both_sidekicks_rollback(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_4.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")

    # Rollback upgrade

    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    check_container_state(client, primary_containers, "running")
    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_all(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_5.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0, primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0, primary=False)

    # Confirm upgrade

    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_all_rollback(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_5.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0, primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0, primary=False)

    # Rollback upgrade

    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_only_primary(
        client, rancher_cli_container, socat_containers):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice3_1.yml"
    rc_file = "rc_inservice3_1.yml"
    dc_file_upgrade = "dc_inservice3_2.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_only_primary_rollback(
        client, rancher_cli_container, socat_containers):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice3_1.yml"
    rc_file = "rc_inservice3_1.yml"
    dc_file_upgrade = "dc_inservice3_2.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick1(
        client, rancher_cli_container, socat_containers):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice3_1.yml"
    rc_file = "rc_inservice3_1.yml"
    dc_file_upgrade = "dc_inservice3_3.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service, stack_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "stopped")
    check_container_state(client, sk2_containers, "running")

    # Confirm upgrade

    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    validate_volume_mount(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick1_rollback(
        client, rancher_cli_container, socat_containers):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice3_1.yml"
    rc_file = "rc_inservice3_1.yml"
    dc_file_upgrade = "dc_inservice3_3.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service, stack_name+FIELD_SEPARATOR+"test1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "stopped")
    check_container_state(client, sk2_containers, "running")

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)

    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick2(
        client, rancher_cli_container, socat_containers):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice3_1.yml"
    rc_file = "rc_inservice3_1.yml"
    dc_file_upgrade = "dc_inservice3_4.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service, stack_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    check_container_state(client, primary_containers, "stopped")

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    validate_volume_mount(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_volume_mount_sidekick2_rollback(
        client, rancher_cli_container, socat_containers):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice3_1.yml"
    rc_file = "rc_inservice3_1.yml"
    dc_file_upgrade = "dc_inservice3_4.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)
    primary_containers = get_service_containers_with_name(
        client, service, stack_name+FIELD_SEPARATOR+"test1", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1, primary=False)
    check_container_state(client, primary_containers, "stopped")

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1, primary=False)

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0

    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1"])
    validate_volume_mount(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        [stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2"])
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_confirm_retainip(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_retainip_1.yml"
    rc_file = "rc_inservice1_retainip_1.yml"
    dc_file_upgrade = "dc_inservice1_retainip_2.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 6):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)
    # Check for default settings
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 2
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 1000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value2"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the new containers were retained after upgrade
    for i in range(1, 6):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            != containers[0].externalId

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_rollback_retainip(
        client, rancher_cli_container):

    # Create an stack using up
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_retainip_1.yml"
    rc_file = "rc_inservice1_retainip_1.yml"
    dc_file_upgrade = "dc_inservice1_retainip_2.yml"
    upgrade_option = "--batch-size 3 --interval 500"

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert service.retainIp

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 6):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 6):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade,
                            upgrade_option=upgrade_option)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 3
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 500
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value1"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the containers after rollback were retained after upgrade
    for i in range(1, 6):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            == containers[0].externalId

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_set_retainip_during_upgrade(
        client, rancher_cli_container):
    # Create an stack using up
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_1.yml"
    rc_file = "rc_inservice1_1.yml"
    dc_file_upgrade = "dc_inservice2_retainip_2.yml"
    rc_file_upgrade = "rc_inservice2_retainip_2.yml"

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert service.retainIp is None
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 3):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service,
                            dc_file_upgrade, rc_file_upgrade)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)
    # Check for default settings
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 2
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 1000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value2"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the new containers were retained after upgrade
    for i in range(1, 3):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            != containers[0].externalId

    delete_all(client, [stack])


@if_compose_data_files
# known issue 5476
def test_rancher_compose_inservice_upgrade_retainip_during_upgrade_rollback(
        client, rancher_cli_container):

    # Create an stack using up
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_1.yml"
    rc_file = "rc_inservice1_1.yml"
    dc_file_upgrade = "dc_inservice2_retainip_2.yml"
    rc_file_upgrade = "rc_inservice2_retainip_2.yml"

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert service.retainIp is None
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 3):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    containerips_before_upgrade = {}
    for i in range(1, 3):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        containerips_before_upgrade[container_name+"ip"] = \
            containers[0].primaryIpAddress
        containerips_before_upgrade[container_name+"id"] = \
            containers[0].externalId

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service,
                            dc_file_upgrade, rc_file_upgrade)
    assert service.retainIp
    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)

    # Rollback upgrade

    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    assert service.retainIp is None
    check_config_for_service(client, service, {"test1": "value1"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0

    # Confirm Ips of the containers after rollback were retained after upgrade
    for i in range(1, 3):
        container_name = get_container_name(stack, service, str(i))
        containers = client.list_container(name=container_name,
                                           removed_null=True)
        assert len(containers) == 1
        assert containerips_before_upgrade[container_name+"ip"] \
            == containers[0].primaryIpAddress
        assert containerips_before_upgrade[container_name+"id"] \
            == containers[0].externalId

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_remove_sk(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_rmsk.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 1
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert not check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 1
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert not check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
# Known issue #6380
def test_rancher_compose_inservice_upgrade_remove_sk_rollback(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_rmsk.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 1
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert not check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1,  primary=False)

    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_add_sk(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_addsk.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 3
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk3",
        {"testsk3": "value1"}, 1,  primary=False)

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 3
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk3",
        {"testsk3": "value1"}, 1,  primary=False)

    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_add_sk_rollback(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice2_1.yml"
    rc_file = "rc_inservice2_1.yml"
    dc_file_upgrade = "dc_inservice2_addsk.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    sk1_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1", 1)
    sk2_containers = get_service_containers_with_name(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2", 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 3
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 0)
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value2"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 0,  primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value2"}, 1,  primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk3",
        {"testsk3": "value1"}, 1,  primary=False)

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)

    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert not check_for_sidekick_name_in_service(service, "sk3")

    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        {"test1": "value1"}, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        {"testsk1": "value1"}, 1,  primary=False)

    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        {"testsk2": "value1"}, 1,  primary=False)

    check_container_state(client, sk1_containers, "running")
    check_container_state(client, sk2_containers, "running")
    container_list = get_service_container_managed_list(
        client, service, managed=0)
    assert len(container_list) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_upgrade_with_ports_confirm(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inserviceport.yml"
    rc_file = "rc_inserviceport.yml"
    dc_file_upgrade = "dc_inserviceport_upg.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service(client, service, {"test1": "value2"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_upgrade_with_ports_rollback(
        client, rancher_cli_container):
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inserviceport.yml"
    rc_file = "rc_inserviceport.yml"
    dc_file_upgrade = "dc_inserviceport_forrollback_upg.yml"
    upgrade_option = "--batch-size 3 --interval 500"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file, rc_file)
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service,
                            dc_file_upgrade, upgrade_option=upgrade_option)
    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)

    assert service.upgrade["inServiceStrategy"]["batchSize"] == 3
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 500
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service(client, service, {"test1": "value1"}, 1)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_upgrade_global_with_ports_confirm(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inserviceport_g.yml"
    dc_file_upgrade = "dc_inserviceport_g_upg.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)
    check_config_for_service(client, service, {"test1": "value1"}, 1,
                             is_global=True)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service, dc_file_upgrade)
    check_config_for_service(client, service, {"test1": "value1"}, 0,
                             is_global=True)
    check_config_for_service(client, service, {"test1": "value2"}, 1,
                             is_global=True)

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service(client, service, {"test1": "value2"}, 1,
                             is_global=True)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_upgrade_global_with_ports_rollback(
        client, rancher_cli_container):
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inserviceport_g.yml"
    dc_file_upgrade = "dc_inserviceport_g_upg.yml"
    upgrade_option = "--batch-size 3 --interval 500"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)
    check_config_for_service(client, service, {"test1": "value1"}, 1,
                             is_global=True)

    # Upgrade stack using up --upgrade
    service = upgrade_stack(client, stack_name, service,
                            dc_file_upgrade, upgrade_option=upgrade_option)
    check_config_for_service(client, service, {"test1": "value1"}, 0,
                             is_global=True)
    check_config_for_service(client, service, {"test1": "value2"}, 1,
                             is_global=True)

    # Rollback upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, dc_file_upgrade)
    check_config_for_service(client, service, {"test1": "value1"}, 1,
                             is_global=True)
    containers = get_service_container_managed_list(client, service, 0)
    assert len(containers) == 0
    delete_all(client, [stack])


def check_config_for_service_sidekick(client, service, service_name,
                                      labels, managed, primary=True):
    containers = get_service_containers_with_name(
        client, service, service_name, managed)
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


def upgrade_stack(client, stack_name, service, docker_compose,
                  rancher_compose=None, upgrade_option=None):
    upgrade_cmd = "up -d "
    if upgrade_option is not None:
        upgrade_cmd += upgrade_option
    launch_rancher_cli_from_file(
        client, INSERVICE_SUBDIR, stack_name,
        upgrade_cmd, "st",
        docker_compose)
    service = wait_for_condition(client, service,
                                 lambda x: x.state == 'active',
                                 lambda x: 'State is: ' + x.state)
    assert service.state == "active"
    return service


def confirm_upgrade_stack(client, stack_name, service, docker_compose):
    launch_rancher_cli_from_file(
        client, INSERVICE_SUBDIR, stack_name,
        "up --confirm-upgrade -d", "Started",
        docker_compose)
    service = wait_for_condition(client, service,
                                 lambda x: x.state == 'active',
                                 lambda x: 'State is: ' + x.state)
    assert service.state == "active"
    return service


def rollback_upgrade_stack(client, stack_name, service, docker_compose):
    launch_rancher_cli_from_file(
        client, INSERVICE_SUBDIR, stack_name,
        "up --rollback -d", "Started",
        docker_compose)
    service = client.reload(service)
    assert service.state == "active"
    return service
