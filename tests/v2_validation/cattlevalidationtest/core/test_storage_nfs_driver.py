from common_fixtures import *  # NOQA
from cattle import ApiError

if_test_rancher_nfs = pytest.mark.skipif(
    not os.environ.get('TEST_NFS'),
    reason='Rancher NFS test not enabled')
volume_driver = "rancher-nfs"


@if_test_rancher_nfs
def test_nfs_services_with_shared_vol(client):
    assert check_for_nfs_driver(client)
    services_with_shared_vol(client, volume_driver=volume_driver)


@if_test_rancher_nfs
def test_nfs_services_with_shared_vol_scaleup(client):
    assert check_for_nfs_driver(client)
    services_with_shared_vol_scaleup(client, volume_driver=volume_driver)


@if_test_rancher_nfs
def test_nfs_multiple_services_with_same_shared_vol(client):
    assert check_for_nfs_driver(client)
    multiple_services_with_same_shared_vol(client, volume_driver=volume_driver)


@if_test_rancher_nfs
def test_nfs_delete_volume(client):
    assert check_for_nfs_driver(client)
    delete_volume_after_service_deletes(client, volume_driver=volume_driver)


@if_test_rancher_nfs
def test_nfs_services_with_custom_export(client):
    assert check_for_nfs_driver(client)
    services_with_custom_export(client, volume_driver)


def services_with_shared_vol(client, volume_driver):

    # Create Environment with service that has shared volume from
    # volume_driver

    volume_name = random_str()
    path = "/myvol"
    port = "1000"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "volumeDriver": volume_driver,
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    service, env = create_env_and_svc(client, launch_config, 2)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == service.scale
    assert get_container_host_ip(container_list[0]) != \
        get_container_host_ip(container_list[1])

    volumes = client.list_volume(removed_null=True,
                                 name=volume_name)
    print volumes
    assert len(volumes) == 1
    assert volumes[0].state == "active"

    filename = "test"
    content = random_str()
    write_data(container_list[0], int(port), path, filename, content)

    file_content = \
        read_data(container_list[1], int(port), path, filename)

    assert file_content == content
    delete_all(client, [env])
    delete_volume(client, volumes[0])


def services_with_shared_vol_scaleup(client, volume_driver):

    # Create Environment with service that has shared volume from
    # volume_driver

    volume_name = random_str()
    path = "/myvol"
    port = "1001"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "volumeDriver": volume_driver,
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    service, env = create_env_and_svc(client, launch_config, 2)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == service.scale

    volumes = client.list_volume(removed_null=True,
                                 name=volume_name)
    print volumes
    assert len(volumes) == 1
    assert volumes[0].state == "active"
    assert get_container_host_ip(container_list[0]) != \
        get_container_host_ip(container_list[1])

    filename = "test"
    content = random_str()
    write_data(container_list[0], int(port), path, filename, content)

    file_content = \
        read_data(container_list[1], int(port), path, filename)

    assert file_content == content

    # Scale service
    final_scale = 3
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_scale

    # After scale up , make sure all container share the same volume by making
    # sure all containers are able to access the contents of the file
    # the was created before scaling service
    container_list = get_service_container_list(client, service)
    assert len(container_list) == service.scale
    for container in container_list:
        file_content = \
            read_data(container_list[1], int(port), path, filename)
        assert file_content == content

    filename = "test1"
    content = random_str()
    write_data(container_list[2], int(port), path, filename, content)
    for container in container_list:
        file_content = \
            read_data(container_list[1], int(port), path, filename)
        assert file_content == content

    delete_all(client, [env])
    delete_volume(client, volumes[0])


def multiple_services_with_same_shared_vol(client, volume_driver):

    # Create Environment with service that has shared volume from
    # volume_driver

    volume_name = random_str()
    path = "/myvol"
    port = "1002"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "volumeDriver": volume_driver,
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    service, env = create_env_and_svc(client, launch_config, 2)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == service.scale

    volumes = client.list_volume(removed_null=True,
                                 name=volume_name)
    print volumes
    assert len(volumes) == 1
    assert volumes[0].state == "active"

    filename = "test"
    content = random_str()
    write_data(container_list[0], int(port), path, filename, content)

    file_content = \
        read_data(container_list[1], int(port), path, filename)

    assert file_content == content

    # create another service using the same volume
    port = "1003"
    path = "/myvoltest"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "volumeDriver": volume_driver,
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    service1, env1 = create_env_and_svc(client, launch_config, 2)

    service1 = service1.activate()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    container_list = get_service_container_list(client, service1)
    assert len(container_list) == service1.scale

    # Make sure all container of this service share the same volume as the
    # first service created with this volume name by making sure all
    # containers of this service are able to access the contents of the file
    # that was created from container in first service

    for container in container_list:
        file_content = \
            read_data(container, int(port), path, filename)
        assert file_content == content
    delete_all(client, [env, env1])
    delete_volume(client, volumes[0])


def delete_volume_after_service_deletes(client, volume_driver):
    # Create Environment with service that has shared volume from
    # volume_driver

    volume_name = random_str()
    path = "/myvol"
    port = "1004"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "volumeDriver": volume_driver,
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    service, env = create_env_and_svc(client, launch_config, 2)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == service.scale

    volumes = client.list_volume(removed_null=True,
                                 name=volume_name)
    assert len(volumes) == 1
    volume = volumes[0]

    assert volume.state == "active"

    filename = "test"
    content = random_str()
    write_data(container_list[0], int(port), path, filename, content)

    file_content = \
        read_data(container_list[1], int(port), path, filename)

    assert file_content == content

    # create another service using the same volume
    port = "1005"
    path = "/myvoltest"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "volumeDriver": volume_driver,
                     "dataVolumes": [volume_name + ":" + path],
                     "ports": [port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    service1, env1 = create_env_and_svc(client, launch_config, 2)

    service1 = service1.activate()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    container_list = get_service_container_list(client, service1)
    assert len(container_list) == service1.scale

    # Make sure all container share the same volume as the first service
    # created with this volume name by making sure all containers of this
    # service are able to access the contents of the file
    # the was created before scale

    for container in container_list:
        file_content = \
            read_data(container, int(port), path, filename)
        assert file_content == content

    # After deleting one of the services that uses the volumes , volume state
    # should still be active and we should not be allowed to delete the volume
    container_list = get_service_container_list(client, service)
    delete_all(client, [service])
    for container in container_list:
        wait_for_condition(
            client, container,
            lambda x: x.state == 'removed',
            lambda x: 'State is: ' + x.state)
        volume = client.reload(volume)

    volume = client.reload(volume)
    assert volume.state == "active"

    with pytest.raises(ApiError) as e:
        volume = client.wait_success(client.delete(volume))
    assert e.value.error.status == 405
    assert e.value.error.code == 'Method not allowed'

    volume = client.reload(volume)
    assert volume.state == "active"

    # After deleting all the services that uses the volumes , volume state
    # should be detached and we should be allowed to delete the volume

    container_list = get_service_container_list(client, service1)
    delete_all(client, [service1])
    for container in container_list:
        wait_for_condition(
            client, container,
            lambda x: x.state == 'removed',
            lambda x: 'State is: ' + x.state)
    delete_volume(client, volume)


def new_volume_custom_opts(driver, name, host, export, subfolder=False):
    volume = {
        "driver": driver,
        "name": name,
        "driverOpts": {
            "host": host
        }
    }
    # exportBase means "create subdirs"
    if subfolder:
        volume["driverOpts"]["exportBase"] = export
    # export means "dont create subdirs"
    else:
        volume["driverOpts"]["export"] = export
    return volume


def services_with_custom_export(client, volume_driver):
    nfs_service = get_nfs_driver_service(client)

    # root volume/service setup
    root_volume = new_volume_custom_opts(
        driver=volume_driver,
        name=random_str(),
        host=nfs_service.launchConfig.environment.NFS_SERVER,
        export=nfs_service.launchConfig.environment.MOUNT_DIR,
        subfolder=False)
    client.create_volume(root_volume)

    root_path = "/myvol"
    root_port = "1006"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "dataVolumes": [root_volume['name'] + ":" + root_path],
                     "ports": [root_port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    root_service, root_env = create_env_and_svc(client, launch_config, 2)
    root_service = root_service.activate()
    root_service = client.wait_success(root_service, 120)
    assert root_service.state == "active"

    root_container_list = get_service_container_list(client, root_service)
    assert len(root_container_list) == root_service.scale

    assert_volume_is_active(client, root_volume['name'])
    assert_volume_shared_rw(client, root_container_list, root_port, root_path,
                            "shared-rw-root")

    # subfolder volume/service setup
    subfolder_volume = new_volume_custom_opts(
        driver=volume_driver,
        name=random_str(),
        host=nfs_service.launchConfig.environment.NFS_SERVER,
        export=nfs_service.launchConfig.environment.MOUNT_DIR,
        subfolder=True)
    client.create_volume(subfolder_volume)

    subfolder_path = "/myvol2"
    subfolder_port = "1007"
    subfolder_data_volume = subfolder_volume['name'] + ":" + subfolder_path
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "dataVolumes": [subfolder_data_volume],
                     "ports": [subfolder_port + ":22/tcp"],
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label_ne":
                          "io.rancher.stack_service.name" +
                          "=${stack_name}/${service_name}"}
                     }

    subfolder_service, subfolder_env = \
        create_env_and_svc(client, launch_config, 2)
    subfolder_service = subfolder_service.activate()
    subfolder_service = client.wait_success(subfolder_service, 120)
    assert subfolder_service.state == "active"

    subfolder_container_list = \
        get_service_container_list(client, subfolder_service)
    assert len(subfolder_container_list) == subfolder_service.scale

    assert_volume_is_active(client, subfolder_volume['name'])
    subfolder_content = \
        assert_volume_shared_rw(client, subfolder_container_list,
                                subfolder_port, subfolder_path,
                                "shared-rw-subfolder")

    # moment of truth - attempt to read subfolder volume data from root
    # container, proving the exports are mounted in the desired fashion
    file_content = read_data(root_container_list[1], int(root_port),
                             root_path + "/" + subfolder_volume['name'],
                             "shared-rw-subfolder")
    assert file_content == subfolder_content

    # cleanup
    delete_all(client, [root_service, subfolder_service])
    delete_volume(client, get_volume_by_name(client, root_volume['name']))
    delete_volume(client, get_volume_by_name(client, subfolder_volume['name']))


def assert_volume_is_active(client, name):
    volume = get_volume_by_name(client, name)
    assert volume.state == "active"


def get_volume_by_name(client, name):
    volumes = client.list_volume(
        removed_null=True,
        name=name)
    assert len(volumes) == 1
    return volumes[0]


def assert_volume_shared_rw(client, container_list, port, path, filename):
    content = random_str()
    write_data(container_list[0], int(port), path, filename, content)

    file_content = \
        read_data(container_list[1], int(port), path, filename)

    assert file_content == content
    return content


def delete_volume(client, volume):
    volume = wait_for_condition(
        client, volume,
        lambda x: x.state == 'detached',
        lambda x: 'State is: ' + x.state,
        timeout=600)
    assert volume.state == "detached"
    volume = client.wait_success(client.delete(volume))
    assert volume.state == "removed"
    volume = client.wait_success(volume.purge())
    assert volume.state == "purged"


def check_for_nfs_driver(client):
    nfs_driver = False
    service = get_nfs_driver_service(client)
    if service is not None and service.state == "active":
        nfs_driver = True
    return nfs_driver


def get_nfs_driver_service(client):
    env = client.list_stack(name="nfs")
    if len(env) == 1:
        return get_service_by_name(client, env[0], "nfs-driver")
    return None
