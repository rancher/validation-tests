from common_fixtures import *  # NOQA

EBS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'resources/ebs')

start_project_str = "Starting"

if_test_ebs = pytest.mark.skipif(
    RANCHER_EBS != "true",
    reason="rancher ebs test environment is not enabled"
)

@if_test_ebs
def test_environment_ebs_volume_on_same_host(client, super_client):
    # Launching a service with scale 2 using the same volume
    # All the container should land on the same host
    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    volume = client.create_volume({
        "type": "volume",
        "driver": "rancher-ebs",
        "name": volume_name,
        "driverOpts": {"size": "1"}
    })
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
    while True:
        try:
            client.delete(volume)
            break
        except Exception:
            time.sleep(1)
            pass


@if_test_ebs
def test_environment_ebs_volume_read_write_data(client, super_client):
    # Launching two service with scale 1 using the same volume
    # Volume should be able to read and write from all the containers
    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({
        "type": "volume",
        "driver": "rancher-ebs",
        "name": volume_name,
        "driverOpts": {"size": "1"}
    })
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
    container_list = get_service_container_list(super_client, service1)
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
    container_list = get_service_container_list(super_client, service2)
    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack1))
    client.wait_success(client.delete(stack2))
    while True:
        try:
            client.delete(volume)
            break
        except Exception:
            time.sleep(1)
            pass


@if_test_ebs
def test_ebs_volume_move_same_host(client, super_client):
    # Launch a service with scale 1 using the volume1.
    # Write data to the volume.
    # Delete the service and re-launch a new one on the same host
    # using the same volume. Data should be persisted.
    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1000"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({
        "type": "volume",
        "driver": "rancher-ebs",
        "name": volume_name,
        "driverOpts": {"size": "1"}
    })
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
    container_list = get_service_container_list(super_client, service)
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

    container_list = get_service_container_list(super_client, service)
    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))
    while True:
        try:
            client.delete(volume)
            break
        except Exception:
            time.sleep(1)
            pass


@if_test_ebs
def test_ebs_volume_move_diff_hosts(client, super_client):
    # Launch a service with scale 1 using the volume1.
    # Write data to the volume.
    # Delete the service and re-launch a new one on the a different host
    # using the same volume. Data should be persisted.
    # this test requires host a and host b are in the same AZ
    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    path = "/test"
    port = "1001"
    volume = client.create_volume({
        "type": "volume",
        "driver": "rancher-ebs",
        "name": volume_name,
        "driverOpts": {"size": "1"}
    })

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
    container_list = get_service_container_list(super_client, service)
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

    container_list = get_service_container_list(super_client, service)
    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content
    client.wait_success(client.delete(stack))
    while True:
        try:
            client.delete(volume)
            break
        except Exception:
            time.sleep(1)
            pass


@if_test_ebs
def test_ebs_volume_restart_service_instance(client, super_client):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Restart the container instance. The container restarts.
    # Data should be persisted.
    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1002"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name, "driverOpts": {"size": "1"}})
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

    container_list = get_service_container_list(super_client, service)
    container = container_list[0]
    write_data(container, int(port), path, filename, content)
    container = client.wait_success(container.restart(), 120)
    assert container.state == "running"

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content


@if_test_ebs
def test_ebs_volume_activate_deactivate_service(client, super_client):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Stop the container instance. The container restarts.
    # Data should be persisted.
    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1003"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name, "driverOpts": {"size": "1"}})
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
    container_list = get_service_container_list(super_client, service)
    container = container_list[0]
    write_data(container, int(port), path, filename, content)
    stack = stack.deactivateservices()

    service = wait_state(client, service, "inactive")
    container_list = get_service_container_list(super_client, service)
    container = container_list[0]
    assert service.state == "inactive"
    container = client.wait_success(container, 120)
    assert container.state == "stopped"

    stack = stack.activateservices()
    service = wait_state(client, service, "active")
    assert service.state == "active"
    container_list = get_service_container_list(super_client, service)
    container = container_list[0]
    container = client.wait_success(container, 120)

    assert container.state == "running"

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    '''
    client.wait_success(client.delete(stack))
    while True:
        try:
            client.delete(volume)
            break
        except Exception:
            time.sleep(1)
            pass
    '''

@if_test_ebs
def test_ebs_volume_delete_instance(client, super_client, admin_client):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Delete the container instance. The container gets recreated
    # Data should be persisted.
    assert check_for_ebs_driver(client)
    volume_name = "ebs_" + random_str()
    path = "/test"
    port = "1004"
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name, "driverOpts": {"size": "1"}})
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
    container_list = get_service_container_list(super_client, service)
    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    # Delete instance
    container = client.wait_success(client.delete(container), 120)
    # After delete the instance should be recreated
    assert container.state == 'removed'
    wait_for_scale_to_adjust(admin_client, service)

    container_list = get_service_container_list(super_client, service)
    container = container_list[0]
    container = client.wait_success(container, 120)
    assert container.state == "running"

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))
    while True:
        try:
            client.delete(volume)
            break
        except Exception:
            time.sleep(1)
            pass


@if_test_ebs
def test_ebs_service_with_two_new_volumes(client, super_client, rancher_compose_container):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Delete the service and re-launch a new one on the same host
    # using the same volume. Data should be persisted.
    assert check_for_ebs_driver(client)

    env_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path1 = "/testdata1"
    path2 = "/testdata2"
    port1 = 7005

    # Create an environment using up

    launch_rancher_compose_from_file(
        client, EBS_SUBDIR, "dc_service_two_volumes.yml", env_name,
        "up -d", start_project_str)
    stack, service = get_env_service_by_name(client, env_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    write_data(container, int(port1), path1, filename, content)

    file_content = \
        read_data(container_list[0], int(port1), path1, filename)

    assert file_content == content

    container = container_list[0]
    write_data(container, int(port1), path2, filename, content)

    file_content = \
        read_data(container_list[0], int(port1), path2, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))


@if_test_ebs
def test_ebs_stack_scope_volume(client, super_client, rancher_compose_container):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Delete the service and re-launch a new one on the same host
    # using the same volume. Data should be persisted.
    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata1"
    port = 7006

    # Create an environment using up

    launch_rancher_compose_from_file(
        client, EBS_SUBDIR, "dc_stack_scope.yml", stack_name,
        "up -d", start_project_str)
    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))


@if_test_ebs
def test_ebs_container_scope_volume(client, super_client, rancher_compose_container):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Delete the service and re-launch a new one on the same host
    # using the same volume. Data should be persisted.
    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7007

    # Create an environment using up

    launch_rancher_compose_from_file(
        client, EBS_SUBDIR, "dc_container_scope.yml", stack_name,
        "up -d", start_project_str)
    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))


@if_test_ebs
def test_ebs_container_scope_volume_delete_instance(client, super_client, rancher_compose_container):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Delete the service and re-launch a new one on the same host
    # using the same volume. Data should be persisted.
    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7007

    # Create an environment using up

    launch_rancher_compose_from_file(
        client, EBS_SUBDIR, "dc_container_scope.yml", stack_name,
        "up -d", start_project_str)
    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))


@if_test_ebs
def test_ebs_container_scope_volume_restart_instance(client, super_client, rancher_compose_container):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Delete the service and re-launch a new one on the same host
    # using the same volume. Data should be persisted.
    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7007

    # Create an environment using up

    launch_rancher_compose_from_file(
        client, EBS_SUBDIR, "dc_container_scope.yml", stack_name,
        "up -d", start_project_str)
    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))


@if_test_ebs
def test_ebs_container_scope_volume_upgrade(client, super_client, rancher_compose_container):
    # Launch a service with scale 1 using the volume1. Write data to the volume.
    # Delete the service and re-launch a new one on the same host
    # using the same volume. Data should be persisted.
    assert check_for_ebs_driver(client)

    stack_name = random_str().replace("-", "")

    filename = "test"
    content = random_str()
    path = "/testdata"
    port = 7007

    # Create an environment using up

    launch_rancher_compose_from_file(
        client, EBS_SUBDIR, "dc_container_scope.yml", stack_name,
        "up -d", start_project_str)
    stack, service = get_env_service_by_name(client, stack_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "test1"

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    container = container_list[0]
    write_data(container, int(port), path, filename, content)

    file_content = \
        read_data(container_list[0], int(port), path, filename)

    assert file_content == content

    client.wait_success(client.delete(stack))


def check_for_ebs_driver(client):
    ebs_driver = False
    env = client.list_stack(name="ebs")
    if len(env) == 1:
        service = get_service_by_name(client, env[0],
                                      "ebs-driver")
        if service.state == "active":
            ebs_driver = True
    return ebs_driver
