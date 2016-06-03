from common_fixtures import *  # NOQA

RCCOMMANDS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'resources/rccmds')
logger = logging.getLogger(__name__)


if_compose_data_files = pytest.mark.skipif(
    not os.path.isdir(RCCOMMANDS_SUBDIR),
    reason='Rancher compose files directory location not set/does not Exist')


@if_compose_data_files
def test_rancher_compose_create_service(super_client, client,
                                        rancher_compose_container):
    # This method tests the rancher compose create and up commands

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "create", "Creating stack", "rc1.yml")
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "up -d", "Starting project", "rc1.yml")
    env, service = get_env_service_by_name(client, env_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 3
    assert service.name == "test1"

    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_start_stop(super_client, client,
                                    rancher_compose_container):

    # This method tests the rancher compose start and stop commands
    # Bug #4887 has been filed
    # Bug #4933 has been filed [Start command has no response,
    # Now "Started" response is being checked. Should be changed if required.
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "up -d", "Starting project", "rc1.yml")
    env, service = get_env_service_by_name(client, env_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "stop", "Stopped", rancher_compose="rc1.yml")

    # Note: We add a sleep as the stop command does not wait until complete
    time.sleep(10)
    service = client.wait_success(service)

    # Confirm service is inactive and the containers are stopped
    assert service.state == "inactive"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3

    # Check for containers being stopped
    for container in container_list:
        assert container.state == "stopped"

    launch_rancher_compose_from_file(
          client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
          "start -d", "Started", "rc1.yml")

    # Confirm service is active and the containers are running
    service = client.wait_success(service, 300)
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_start_down(super_client, client,
                                    rancher_compose_container):

    # This method tests the rancher compose start and down commands
    env_name = random_str().replace("-", "")
    # Bug #4933 has been filed [Start command has no response,
    # Now "Started" response is being checked. Should be changed if required.
    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "up -d", "Starting project", "rc1.yml")
    env, service = get_env_service_by_name(client, env_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "down", "Stopped", "rc1.yml")

    # Note: We add a sleep as the down command does not wait until it completes
    time.sleep(10)
    service = client.wait_success(service)

    # Confirm service is inactive and the containers are stopped
    assert service.state == "inactive"
    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    # Check for containers being stopped
    for container in container_list:
        assert container.state == "stopped"

    launch_rancher_compose_from_file(
          client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
          "start -d", "Started", "rc1.yml")

    # Confirm service is active and the containers are running
    service = client.wait_success(service, 300)
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_service_restart(super_client, client,
                                         rancher_compose_container):
    # This method tests the rancher compose restart command
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc2.yml", env_name,
        "up -d", "Creating stack", "rc2.yml")
    env, service1 = get_env_service_by_name(client, env_name, "test1")
    env, service2 = get_env_service_by_name(client, env_name, "test2")

    # Confirm service is active and the containers are running
    service1 = client.wait_success(service1, 300)
    service2 = client.wait_success(service2, 300)
    assert service1.state == "active"
    assert service2.state == "active"
    check_config_for_service(super_client, service1, {"test1": "value1"}, 1)
    check_config_for_service(super_client, service2, {"test2": "value2"}, 1)

    container_list1 = get_service_container_list(super_client, service1)
    assert len(container_list1) == 4
    for container in container_list1:
        assert container.state == "running"
        assert container.startCount == 1

    container_list2 = get_service_container_list(super_client, service2)
    assert len(container_list2) == 4
    for con in container_list2:
        assert con.state == "running"
        assert container.startCount == 1
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc2.yml", env_name,
        "restart", "Restarting", "rc2.yml")

    env, service1 = get_env_service_by_name(client, env_name, "test1")
    env, service2 = get_env_service_by_name(client, env_name, "test2")

    # Confirm service is active and the containers are running
    service1 = client.wait_success(service1, 300)
    service2 = client.wait_success(service2, 300)
    assert service1.state == "active"
    assert service2.state == "active"
    check_config_for_service(super_client, service1, {"test1": "value1"}, 1)
    check_config_for_service(super_client, service2, {"test2": "value2"}, 1)

    container_list1 = get_service_container_list(super_client, service1)
    assert len(container_list1) == 4
    for container in container_list1:
        assert container.state == "running"
        assert container.startCount == 2

    container_list2 = get_service_container_list(super_client, service2)
    assert len(container_list2) == 4
    for container in container_list2:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_service_restart_bat_inter(super_client,
                                                   client,
                                                   rancher_compose_container):
    # This method tests restart command with batchsize and inteval options
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc2.yml", env_name,
        "up -d", "Creating stack", "rc2.yml")
    env, service1 = get_env_service_by_name(client, env_name, "test1")
    env, service2 = get_env_service_by_name(client, env_name, "test2")

    # Confirm service is active and the containers are running
    service1 = client.wait_success(service1, 300)
    service2 = client.wait_success(service2, 300)
    assert service1.state == "active"
    assert service2.state == "active"
    check_config_for_service(super_client, service1, {"test1": "value1"}, 1)
    check_config_for_service(super_client, service2, {"test2": "value2"}, 1)

    container_list1 = get_service_container_list(super_client, service1)
    assert len(container_list1) == 4
    for container in container_list1:
        assert container.state == "running"
        assert container.startCount == 1

    container_list2 = get_service_container_list(super_client, service2)
    assert len(container_list2) == 4
    for con in container_list2:
        assert con.state == "running"
        assert container.startCount == 1

    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc2.yml", env_name,
        "restart --batch-size 2 --interval 100", "Restarting", "rc2.yml")

    env, service1 = get_env_service_by_name(client, env_name, "test1")
    env, service2 = get_env_service_by_name(client, env_name, "test2")
    # Confirm service is active and the containers are running
    service1 = client.wait_success(service1, 300)
    service2 = client.wait_success(service2, 300)
    assert service1.state == "active"
    assert service2.state == "active"
    check_config_for_service(super_client, service1, {"test1": "value1"}, 1)
    check_config_for_service(super_client, service2, {"test2": "value2"}, 1)

    container_list1 = get_service_container_list(super_client, service1)
    assert len(container_list1) == 4
    for container in container_list1:
        assert container.state == "running"
        assert container.startCount == 2

    container_list2 = get_service_container_list(super_client, service2)
    assert len(container_list2) == 4
    for container in container_list2:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_services_delete(super_client, client,
                                         rancher_compose_container):
    # This method tests the delete command
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "up -d", "Starting project", "rc1.yml")
    env, service = get_env_service_by_name(client, env_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "rm -f", "Deleting", "rc1.yml")

    # Confirm service is active and the containers are running
    service = client.wait_success(service, 300)
    assert service.state == "removed"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 0

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_services_scale(super_client, client,
                                        rancher_compose_container):
    # This method tests the scale command
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "up -d", "Starting project", "rc1.yml")
    env, service = get_env_service_by_name(client, env_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    # Issue a command to scale up the services
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "scale test1=4", "Setting scale", "rc1.yml")

    # Confirm service is active and the containers are running
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(super_client, service)
    # Check if the number of containers are incremented correctly
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"

    # Issue a command to scale down the services
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc1.yml", env_name,
        "scale test1=3", "Setting scale", "rc1.yml")

    # Confirm service is active and the containers are running
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(super_client, service)
    # Check if the number of containers are decremented correctly
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_services_security(super_client, client,
                                           rancher_compose_container,
                                           socat_containers):
    # This method tests the options in security tab in the UI
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc3.yml", env_name,
        "up -d", "Starting project", "rc3.yml")
    env, service = get_env_service_by_name(client, env_name, "test3")

    # Confirm service is active and the containers are running
    assert service.state == "active"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for con in container_list:
        assert con.state == "running"
        con.privileged == "true"
        containers = super_client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running " + con.name)
        assert inspect["State"]["Running"]
        assert inspect["HostConfig"]["Privileged"]
        assert inspect["HostConfig"]["Memory"] == 104857600
        assert inspect["HostConfig"]["CpuShares"] == 256
        assert inspect["HostConfig"]["CapAdd"] == ["AUDIT_CONTROL",
                                                   "AUDIT_WRITE"]
        assert inspect["HostConfig"]["CapDrop"] == ["BLOCK_SUSPEND",
                                                    "CHOWN"]
        assert inspect["Config"]["Hostname"] == "rancherhost"
        assert inspect["HostConfig"]["PidMode"] == "host"
    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_services_log_driver(super_client, client,
                                             rancher_compose_container,
                                             socat_containers):
    # This test case fails bcos of bug #4773

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc3.yml", env_name,
        "up -d", "Starting project", "rc3.yml")
    env, service = get_env_service_by_name(client, env_name, "test3")

    # Confirm service is active and the containers are running
    assert service.state == "active"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for con in container_list:
        assert con.state == "running"
        con.privileged == "true"
        containers = super_client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running" + con.name)
        assert inspect["State"]["Running"]
        assert inspect["HostConfig"]["LogConfig"]["Type"] == "syslog"

    delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_services_network(super_client, client,
                                          rancher_compose_container,
                                          socat_containers):
    # This method tests the options in Network tab in the UI
    hostname_override = "io.rancher.container.hostname_override"
    requested_ip = "io.rancher.container.requested_ip"
    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc4.yml", env_name,
        "up -d", "Starting project", "rc4.yml")
    env, service = get_env_service_by_name(client, env_name, "test4")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    check_config_for_service(super_client, service,
                             {"testrc": "RANCHER_COMPOSE"}, 1)
    check_config_for_service(super_client, service,
                             {"io.rancher.container.requested_ip":
                              "209.243.140.21"}, 1)
    check_config_for_service(super_client, service,
                             {"io.rancher.container.hostname_override":
                                 "container_name"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 2
    for con in container_list:
        assert con.state == "running"
        con.privileged == "true"
        containers = super_client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running " + con.name)
        assert inspect["State"]["Running"]
        assert inspect["Config"]["Domainname"] == "xyz.com"
        assert \
            inspect["Config"]["Labels"][hostname_override] \
            == "container_name"
        assert inspect["Config"]["Labels"][requested_ip] == "209.243.140.21"
        dns_list = inspect["HostConfig"]["Dns"]
        dnssearch_list = inspect["HostConfig"]["DnsSearch"]
        assert "209.243.150.21" in dns_list
        assert "www.google.com" in dnssearch_list
        delete_all(client, [env])


@if_compose_data_files
def test_rancher_compose_services_volume(super_client, client,
                                         rancher_compose_container,
                                         socat_containers):

    # This test case fails because of bug #4786.
    # Docker inspect appends the local path to the volume

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, RCCOMMANDS_SUBDIR, "dc5.yml", env_name,
        "up -d", "Starting project", "rc5.yml")
    env, service = get_env_service_by_name(client, env_name, "test4")

    # Confirm service is active and the containers are running
    assert service.state == "active"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 3
    for con in container_list:
        assert con.state == "running"
        containers = super_client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running " + con.name)
        assert inspect["State"]["Running"]
        assert inspect["HostConfig"]["Binds"] == ["testvolume:/home:rw"]

    delete_all(client, [env])
