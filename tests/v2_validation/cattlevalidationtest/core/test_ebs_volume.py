from common_fixtures import *  # NOQA

EBS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          'resources/ebs')

start_project_str = "Starting"

if_test_ebs = pytest.mark.skipif(
    RANCHER_EBS != "true",
    reason="rancher ebs test environment is not enabled")


@if_test_ebs
def test_ebs_volume_on_same_host(client):

    # Launching a service with scale 2 using the same volume
    # All the container should land on the same host

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":/test"],
                     "networkMode": "managed",
                     "imageUuid": "docker:ubuntu:14.04.3",
                     "stdinOpen": True
                     }
    scale = 2

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    container_list = get_service_container_list(client, service)
    assert container_list[0].hostId == container_list[1].hostId

    client.wait_success(client.delete(stack))
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_volume_read_write_data(client):

    # Launching two service with scale 1 using the same volume
    # Volume should be able to read and write from all the containers

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    path = "/test"
    port = "1000"
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service1, stack1 = create_env_and_svc(client, launch_config,
                                          scale)
    stack1 = stack1.activateservices()
    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    container_list = get_service_container_list(client, service1)
    filename = "test"
    content = random_str()
    write_data(container_list[0], int(port), path, filename, content)

    path = "/test"
    port = "1001"
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service2, stack2 = create_env_and_svc(client, launch_config,
                                          scale)
    stack2 = stack2.activateservices()
    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    container_list = get_service_container_list(client, service2)
    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack1))
    client.wait_success(client.delete(stack2))
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_volume_move_same_host(client):

    # Launch a service with scale 1 using the volume1.
    # Write data to the volume. Delete the service
    # and re-launch a new one on the same host
    # using the same volume. Data should be persisted.

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1000"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    filename = "test"
    content = random_str()
    container_list = get_service_container_list(client, service)
    write_data(container_list[0], int(port), path, filename, content)
    delete_all(client, [stack])

    wait_for_condition(client, volume, lambda x: x.state == "detached")

    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":/test"],
                     "networkMode": "managed",
                     "ports": [port + ":22/tcp"],
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_volume_move_diff_hosts(client):

    # Launch a service with scale 1 using the volume1.
    # Write data to the volume. Delete the service and
    # re-launch a new one on the a different host
    # using the same volume. Data should be persisted.
    # this test requires host a and host b are in the same AZ

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    path = "/test"
    port = "1001"
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})

    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    filename = "test"
    content = random_str()
    container_list = get_service_container_list(client, service)
    write_data(container_list[0], int(port), path, filename, content)
    delete_all(client, [stack])

    wait_for_condition(client, volume, lambda x: x.state == "detached")

    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[1].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content
    client.wait_success(client.delete(stack))
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_volume_restart_service_instance(client):

    # Launch a service with scale 1 using the volume1.
    # Write data to the volume. Restart the container instance.
    # Data should persisted after container restart

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1002"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    filename = "test"
    content = random_str()

    container_list = get_service_container_list(client, service)
    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    # Restart container instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == "running"

    container_list = get_service_container_list(client, service)
    container = container_list[0]

    file_content = \
        read_data(container, int(port), path, filename)
    assert file_content == content

    client.wait_success(client.delete(stack))
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_volume_activate_deactivate_service(client):

    # Launch a service with scale 1 using ebs volume
    # Write data to the volume. Stop the service
    # Data should be persisted after service is activated

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1003"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    filename = "test"
    content = random_str()
    container_list = get_service_container_list(client, service)
    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    stack = stack.deactivateservices()
    service = wait_state(client, service, "inactive")
    container_list = get_service_container_list(client, service)
    container = container_list[0]
    assert service.state == "inactive"
    container = client.wait_success(container, 120)
    assert container.state == "stopped"

    stack = stack.activateservices()

    service = wait_state(client, service, "active")
    assert service.state == "active"
    container_list = get_service_container_list(client, service)
    container = container_list[0]
    container = client.wait_success(container, 120)
    assert container.state == "running"

    container_list = get_service_container_list(client, service)
    container = container_list[0]

    file_content = \
        read_data(container, int(port), path, filename)
    assert file_content == content

    client.wait_success(client.delete(stack))
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_volume_delete_instance(client):

    # Launch a service with scale 1 using the volume
    # Write data to the volume. Delete the container instance
    # Data should be persisted after the container gets recreated

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1004"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    filename = "test"
    content = random_str()
    container_list = get_service_container_list(client, service)
    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    # Delete instance
    container = client.wait_success(client.delete(container), 120)
    # After delete the instance should be recreated
    assert container.state == 'removed'
    wait_for_scale_to_adjust(client, service)

    container_list = get_service_container_list(client, service)
    container = container_list[0]
    assert container.state == "running"

    file_content = \
        read_data(container, int(port), path, filename)
    assert file_content == content

    client.wait_success(client.delete(stack), 120)
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_service_with_two_new_volumes(client, rancher_cli_container):

    # Launch a service with scale 1 using two new volumes.
    # Write and read to both the volumes should be successful

    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path1 = "/testdata1"
    path2 = "/testdata2"
    port1 = 7005

    # Create a stack
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_two_volumes.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    # Get the volume Id
    volumedict = container.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId

    write_data(container, int(port1), path1, filename, content)

    file_content = \
        read_data(container, int(port1), path1, filename)

    assert file_content == content

    container = container_list[0]
    write_data(container, int(port1), path2, filename, content)

    file_content = \
        read_data(container, int(port1), path2, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))

    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_stack_scope_volume(client, rancher_cli_container):

    # Launch a service with scale 1 using ebs volume at stack scope

    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7006

    # Create a stack

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_stack_scope.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")
    print service

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1

    container = container_list[0]
    # Get the volume Id
    volumedict = container.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId

    write_data(container, int(port), path, filename, content)

    file_content = \
        read_data(container, int(port), path, filename)

    assert file_content == content
    client.wait_success(client.delete(stack), 120)

    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_container_scope_volume(client, rancher_cli_container):

    # Launch a service with scale 1 using ebs volume at container scope
    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7007

    # Create a stack

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_container_scope.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    # Get the volume Id
    volumedict = container.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId
    write_data(container, int(port), path, filename, content)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))

    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_container_scope_volume_delete_instance(client,
                                                    rancher_cli_container):

    # Launch a service with scale 1 using ebs volume at container scope
    # Delete an instance and ensure no data is lost
    # after the container is recreated

    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7008

    # Create a stack

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_container_scope_1.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    # Delete instance
    container = client.wait_success(client.delete(container), 120)
    # After delete, the instance should be recreated
    assert container.state == 'removed'
    wait_for_scale_to_adjust(client, service)

    container_list = get_service_container_list(client, service)
    container = container_list[0]
    assert container.state == "running"

    # Get the volume Id
    volumedict = container.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId

    file_content = \
        read_data(container, int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))
    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_container_scope_volume_restart_instance(client,
                                                     rancher_cli_container):

    # Launch a service with scale 1 using ebs volume at container scope
    # Delete an instance and ensure no data is lost
    # after the container is restarted

    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7009

    # Create a stack
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_container_scope_2.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    # Get the volume Id
    volumedict = container.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId
    write_data(container, int(port), path, filename, content)

    # Restart container instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == "running"

    container_list = get_service_container_list(client, service)
    container = container_list[0]
    file_content = \
        read_data(container, int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))

    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_container_scope_volume_upgrade(client,
                                            rancher_cli_container):

    # Launch a service with scale 1 using ebs volume at container scope
    # Delete an instance and ensure no data is lost
    # after the service is upgraded

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7010

    # Create a stack

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_container_scope_3.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    # Get the volume Id
    volumedict = container.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId
    write_data(container, int(port), path, filename, content)

    # Upgrade stack
    service = upgrade_stack(client, stack_name, service,
                            "dc_container_scope_upg.yml",
                            directory=EBS_SUBDIR)

    # Check for default settings
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 2
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 1000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Confirm upgrade
    service = confirm_upgrade_stack(
        client, stack_name, service, "dc_container_scope_upg.yml",
        directory=EBS_SUBDIR)

    check_config_for_service(client, service, {"test1": "value2"}, 1)
    containers = get_service_container_list(client, service)

    file_content = \
        read_data(containers[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))

    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_container_scope_volume_upgrade_rollback(client,
                                                     rancher_cli_container):

    # Launch a service with scale 1 using ebs volume at container scope
    # Delete an instance and ensure no data is lost
    # after the service is upgraded and rolled back

    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7011

    # Create stack

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_container_scope_4.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    # Get the volume Id
    volumedict = container.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId
    write_data(container, int(port), path, filename, content)

    # Upgrade stack
    service = upgrade_stack(client, stack_name, service,
                            "dc_container_scope_upg_rb.yml",
                            directory=EBS_SUBDIR)

    check_config_for_service(client, service, {"test1": "value1"}, 0)
    check_config_for_service(client, service, {"test1": "value2"}, 1)

    # Check for default settings
    assert service.upgrade["inServiceStrategy"]["batchSize"] == 2
    assert service.upgrade["inServiceStrategy"]["intervalMillis"] == 1000
    assert service.upgrade["inServiceStrategy"]["startFirst"] is False

    # Rollback the upgrade
    service = rollback_upgrade_stack(
        client, stack_name, service, "dc_container_scope_upg.yml",
        directory=EBS_SUBDIR)
    check_config_for_service(client, service, {"test1": "value1"}, 1)

    check_config_for_service(client, service, {"test1": "value1"}, 1)
    container_list = get_service_container_list(client, service)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))

    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_volume_primary(client, rancher_cli_container):

    # Launch a service with primary and sidekicks, using ebs volume
    # in only primary container. Data is primary should be available
    # to the sidekick container

    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port1 = 7012
    port2 = 7013

    # Create an environment using up

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_primary_sidekick_1.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    container1 = container_list[0]
    container2 = container_list[1]

    # Get the volume Id
    volumedict = container1.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId
    # Write data to the primary and read from the sidekick container
    write_data(container1, int(port1), path, filename, content)

    file_content = \
        read_data(container2, int(port2), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))

    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_volume_sidekick(client, rancher_cli_container):

    # Launch a service with primary and sidekicks, using ebs volume
    # in only sidekick container. Data is sidekick should be available
    # to the primary container

    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port1 = 7014
    port2 = 7015

    # Create a stack with volume in the sidekick

    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test1", EBS_SUBDIR, "dc_primary_sidekick_2.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    container1 = container_list[0]
    container2 = container_list[1]

    # Get the volume Id
    volumedict = container1.dataVolumeMounts
    print "The volume ID is:"
    for key, value in volumedict.items():
        print key, value
    volumeId = value
    print volumeId
    # Write data to the sidekick and read from the primary container
    write_data(container2, int(port2), path, filename, content)

    file_content = \
        read_data(container1, int(port1), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))
    # Remove the volume
    remove_command = "volume rm " + volumeId
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Verify volume is removed
    if volumeId in cli_remove_response:
        assert True


@if_test_ebs
def test_ebs_volume_restart_driver_container(client):

    # Launch a service with scale 1 using the volume1.
    # Write data to the volume. Restart the ebs driver container
    # The data in the volume should not be lost

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "7016"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    filename = "test"
    content = random_str()
    container_list = get_service_container_list(client, service)
    write_data(container_list[0], int(port), path, filename, content)

    # Restart EBS driver container
    env = client.list_stack(name="ebs")
    if len(env) == 1:
        service = get_service_by_name(client, env[0],
                                      "ebs-driver")
    ebs_container_list = get_service_container_list(client, service)
    client.wait_success(ebs_container_list[0].restart(), 120)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content
    client.wait_success(client.delete(stack))
    delete_volume(client, volume)


@if_test_ebs
def test_ebs_volume_stop_driver_container(client):

    # Launch a service with scale 1 using the volume1.
    # Write data to the volume. Stop the driver container
    # The data in the volume should not be lost
    # after the container gets recreated

    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "7017"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name,
                                   "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "networkMode": "managed",
                     "imageUuid": SSH_IMAGE_UUID,
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    filename = "test"
    content = random_str()
    container_list = get_service_container_list(client, service)
    write_data(container_list[0], int(port), path, filename, content)

    # Stop EBS driver instance
    env = client.list_stack(name="ebs")
    if len(env) == 1:
        service = get_service_by_name(client, env[0],
                                      "ebs-driver")
    ebs_container_list = get_service_container_list(client, service)
    client.wait_success(ebs_container_list[0].stop(), 120)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))
    delete_volume(client, volume)


def check_for_ebs_driver(client):
    ebs_driver = False
    env = client.list_stack(name="ebs")
    if len(env) == 1:
        service = get_service_by_name(client, env[0],
                                      "ebs-driver")
        if service.state == "active":
            ebs_driver = True
    return ebs_driver
