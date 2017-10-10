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
def test_rancher_compose_inservice_upgrade_rollback(client,
                                                    rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice1_1.yml"
    dc_file_upgrade = "dc_inservice1_2.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)

    check_config_for_service(client, service, {"test1": "value1"}, 1)

    # Upgrade stack using up --upgrade
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file_upgrade)

    check_config_for_service(client, service, {"test1": "value2"}, 1)

    # Check for default settings
    assert service.batchSize == 1
    assert service.intervalMillis == 2000
    assert service.startFirst is False

    service = rollback_upgrade_stack(client, service)
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_primary_rollback(
        client, rancher_cli_container):

    dc_file = "dc_inservice_sidekick.yml"
    dc_file_upgrade = "dc_inservice_sidekick_upg.yml"

    primary_label_before_upgrade = {"test1": "value1"}
    sk1_label_before_upgrade = {"testsk1": "value1"}
    sk2_label_before_upgrade = {"testsk2": "value1"}
    primary_label_after_upgrade = {"test1": "value2"}
    sk1_label_after_upgrade = {"testsk1": "value1"}
    sk2_label_after_upgrade = {"testsk2": "value1"}

    stack, service = upgrade_service_with_sidekick(
        client, dc_file, dc_file_upgrade,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade,
        primary_label_after_upgrade,
        sk1_label_after_upgrade,
        sk2_label_after_upgrade)

    service = rollback_upgrade_stack(client, service)
    check_config_for_service_with_sidekick(
        client, service, stack.name,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade)

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_only_sidekick_rollback(
        client, rancher_cli_container):

    dc_file = "dc_inservice_sidekick.yml"
    dc_file_upgrade = "dc_inservice_sidekick_upg1.yml"

    primary_label_before_upgrade = {"test1": "value1"}
    sk1_label_before_upgrade = {"testsk1": "value1"}
    sk2_label_before_upgrade = {"testsk2": "value1"}
    primary_label_after_upgrade = {"test1": "value1"}
    sk1_label_after_upgrade = {"testsk1": "value2"}
    sk2_label_after_upgrade = {"testsk2": "value1"}

    stack, service = upgrade_service_with_sidekick(
        client, dc_file, dc_file_upgrade,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade,
        primary_label_after_upgrade,
        sk1_label_after_upgrade,
        sk2_label_after_upgrade)

    service = rollback_upgrade_stack(client, service)
    check_config_for_service_with_sidekick(
        client, service, stack.name,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade)

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_both_sidekicks_rollback(
        client, rancher_cli_container):
    dc_file = "dc_inservice_sidekick.yml"
    dc_file_upgrade = "dc_inservice_sidekick_upg2.yml"

    primary_label_before_upgrade = {"test1": "value1"}
    sk1_label_before_upgrade = {"testsk1": "value1"}
    sk2_label_before_upgrade = {"testsk2": "value1"}
    primary_label_after_upgrade = {"test1": "value1"}
    sk1_label_after_upgrade = {"testsk1": "value2"}
    sk2_label_after_upgrade = {"testsk2": "value2"}

    stack, service = upgrade_service_with_sidekick(
        client, dc_file, dc_file_upgrade,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade,
        primary_label_after_upgrade,
        sk1_label_after_upgrade,
        sk2_label_after_upgrade)

    service = rollback_upgrade_stack(client, service)
    check_config_for_service_with_sidekick(
        client, service, stack.name,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade)

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_sk_all_rollback(
        client, rancher_cli_container):

    dc_file = "dc_inservice_sidekick.yml"
    dc_file_upgrade = "dc_inservice_sidekick_upg3.yml"

    primary_label_before_upgrade = {"test1": "value1"}
    sk1_label_before_upgrade = {"testsk1": "value1"}
    sk2_label_before_upgrade = {"testsk2": "value1"}
    primary_label_after_upgrade = {"test1": "value2"}
    sk1_label_after_upgrade = {"testsk1": "value2"}
    sk2_label_after_upgrade = {"testsk2": "value2"}

    stack, service = upgrade_service_with_sidekick(
        client, dc_file, dc_file_upgrade,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade,
        primary_label_after_upgrade,
        sk1_label_after_upgrade,
        sk2_label_after_upgrade)

    service = rollback_upgrade_stack(client, service)
    check_config_for_service_with_sidekick(
        client, service, stack.name,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade)

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
def test_rancher_compose_inservice_upgrade_remove_sk_rollback(
        client, rancher_cli_container):
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice_sidekick.yml"
    dc_file_upgrade = "dc_inservice_sidekick_removesidekick.yml"
    primary_label = {"test1": "value1"}
    sk1_label = {"testsk1": "value1"}
    sk2_label = {"testsk2": "value1"}

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label,
                                           sk1_label,
                                           sk2_label)

    # Upgrade stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 1
    assert check_for_sidekick_name_in_service(service, "sk1")

    # Rollback Service
    service = rollback_upgrade_stack(client, service)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label,
                                           sk1_label,
                                           sk2_label)
    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_inservice_upgrade_add_sk_rollback(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inservice_sidekick.yml"
    dc_file_upgrade = "dc_inservice_sidekick_addsidekick.yml"
    primary_label = {"test1": "value1"}
    sk1_label = {"testsk1": "value1"}
    sk2_label = {"testsk2": "value1"}
    sk3_label = {"testsk3": "value1"}

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label,
                                           sk1_label,
                                           sk2_label)
    # Upgrade stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file_upgrade)
    assert len(service.secondaryLaunchConfigs) == 3
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    assert check_for_sidekick_name_in_service(service, "sk3")
    check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label,
                                           sk1_label,
                                           sk2_label)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk3",
        sk3_label, 1, primary=False)

    # Rollback Service
    service = rollback_upgrade_stack(client, service)
    assert len(service.secondaryLaunchConfigs) == 2
    assert check_for_sidekick_name_in_service(service, "sk1")
    assert check_for_sidekick_name_in_service(service, "sk2")
    check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label,
                                           sk1_label,
                                           sk2_label)

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_upgrade_with_ports_confirm(
        client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    dc_file = "dc_inserviceport.yml"
    dc_file_upgrade = "dc_inserviceport_upg.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)

    check_config_for_service(client, service, {"test1": "value1"}, 1)
    validate_exposed_port(client, service, [40], "/name.html", 1)

    # Upgrade stack using up --upgrade
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file_upgrade)

    check_config_for_service(client, service, {"test1": "value2"}, 1)
    validate_exposed_port(client, service, [40], "/name.html", 1)

    # Check for default settings
    assert service.batchSize == 1
    assert service.intervalMillis == 2000
    assert service.startFirst is False

    service = rollback_upgrade_stack(client, service)
    check_config_for_service(client, service, {"test1": "value1"}, 1)
    validate_exposed_port(client, service, [40], "/name.html", 1)

    delete_all(client, [stack])


@if_compose_data_files
def test_rancher_compose_upgrade_global_with_ports_rollback(
        client, rancher_cli_container):
    stack_name = random_str().replace("-", "")
    dc_file = "dc_inserviceport_g.yml"
    dc_file_upgrade = "dc_inserviceport_g_upg.yml"

    # Create an stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)

    check_config_for_service(client, service, {"test1": "value1"}, 1)
    validate_exposed_port(client, service, [42], "/name.html", 1)

    # Upgrade stack
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file_upgrade)

    check_config_for_service(client, service, {"test1": "value2"}, 1)
    validate_exposed_port(client, service, [42], "/name.html", 1)

    # Rollback stack
    service = rollback_upgrade_stack(client, service)
    check_config_for_service(client, service, {"test1": "value1"}, 1)
    validate_exposed_port(client, service, [42], "/name.html", 1)

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


def rollback_upgrade_stack(client, service, revisionId=None):
    if revisionId is None:
        revisionId = service.previousRevisionId
    service = service.rollback(revisionId=revisionId)
    service = wait_for_condition(client, service,
                                 lambda x: x.state == 'active',
                                 lambda x: 'State is: ' + x.state,
                                 timeout=120)
    assert service.state == "active"
    return service


def upgrade_service_with_sidekick(
        client, dc_file, dc_file_upgrade,
        primary_label_before_upgrade,
        sk1_label_before_upgrade,
        sk2_label_before_upgrade,
        primary_label_after_upgrade,
        sk1_label_after_upgrade,
        sk2_label_after_upgrade):

    stack_name = random_str().replace("-", "")
    # Create stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file)

    check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label_before_upgrade,
                                           sk1_label_before_upgrade,
                                           sk2_label_before_upgrade)
    # Upgrade stack using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", INSERVICE_SUBDIR, dc_file_upgrade)

    check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label_after_upgrade,
                                           sk1_label_after_upgrade,
                                           sk2_label_after_upgrade)
    return stack, service


def check_config_for_service_with_sidekick(client, service, stack_name,
                                           primary_label,
                                           sk1_label,
                                           sk2_label):
    check_config_for_service_sidekick(
        client, service, stack_name+FIELD_SEPARATOR+"test1",
        primary_label, 1)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk1",
        sk1_label, 1, primary=False)
    check_config_for_service_sidekick(
        client, service,
        stack_name+FIELD_SEPARATOR+"test1"+FIELD_SEPARATOR+"sk2",
        sk2_label, 1, primary=False)
