from common_fixtures import *  # NOQA

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


def check_for_ebs_driver(client):
    ebs_driver = False
    env = client.list_stack(name="ebs")
    if len(env) == 1:
        service = get_service_by_name(client, env[0],
                                      "ebs-driver")
        if service.state == "active":
            ebs_driver = True
    return ebs_driver
