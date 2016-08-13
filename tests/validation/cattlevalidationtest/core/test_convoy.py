from common_fixtures import *  # NOQA
from cattle import ApiError

if_test_convoy_nfs = pytest.mark.skipif(
    not os.environ.get('TEST_CONVOY_NFS'),
    reason='Convoy NFS test not enabled')

if_test_convoy_gluster = pytest.mark.skipif(
    not os.environ.get('TEST_CONVOY_GLUSTER'),
    reason='Convoy Gluster test not enabled')


@if_test_convoy_nfs
def test_nfs_services_with_shared_vol(
        super_client, client, convoy_nfs):
    services_with_shared_vol(
        super_client, client, volume_driver="convoy-nfs")


@if_test_convoy_nfs
def test_nfs_services_with_shared_vol_scaleup(
        super_client, client, convoy_nfs):
    services_with_shared_vol_scaleup(
        super_client, client, volume_driver="convoy-nfs")


@if_test_convoy_nfs
def test_nfs_multiple_services_with_same_shared_vol(
        super_client, client, convoy_nfs):
    multiple_services_with_same_shared_vol(
        super_client, client, volume_driver="convoy-nfs")


@if_test_convoy_nfs
def test_nfs_delete_volume(
        super_client, client, convoy_nfs):
    delete_volume(
        super_client, client, volume_driver="convoy-nfs")


@if_test_convoy_gluster
def test_glusterfs_services_with_shared_vol(
        super_client, client, glusterfs_glusterconvoy):
    services_with_shared_vol(
        super_client, client, volume_driver="convoy-gluster")


@if_test_convoy_gluster
def test_glusterfs_services_with_shared_vol_scaleup(
        super_client, client, glusterfs_glusterconvoy):
    services_with_shared_vol_scaleup(
        super_client, client, volume_driver="convoy-gluster")


@if_test_convoy_gluster
def test_glusterfs_multiple_services_with_same_shared_vol(
        super_client, client, glusterfs_glusterconvoy):
    multiple_services_with_same_shared_vol(
        super_client, client, volume_driver="convoy-gluster")


@if_test_convoy_gluster
def test_glusterfs_delete_volume(
        super_client, client, glusterfs_glusterconvoy):
    delete_volume(
        super_client, client, volume_driver="convoy-gluster")


def services_with_shared_vol(
        super_client, client, volume_driver):

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

    container_list = get_service_container_list(super_client, service)
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
    delete_all(client, [env])


def services_with_shared_vol_scaleup(
        super_client, client, volume_driver):

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

    container_list = get_service_container_list(super_client, service)
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

    # Scale service
    final_scale = 3
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_scale

    # After scale up , make sure all container share the same volume by making
    # sure all containers are able to access the contents of the file
    # the was created before scale
    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == service.scale
    for container in container_list:
        file_content = \
            read_data(container_list[1], int(port), path, filename)
        assert file_content == content
    delete_all(client, [env])


def multiple_services_with_same_shared_vol(
        super_client, client, volume_driver):

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

    container_list = get_service_container_list(super_client, service)
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

    container_list = get_service_container_list(super_client, service1)
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


def delete_volume(
        super_client, client, volume_driver):
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

    container_list = get_service_container_list(super_client, service)
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

    container_list = get_service_container_list(super_client, service1)
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
    delete_all(client, [service])
    container_list = get_service_container_list(super_client, service)
    for container in container_list:
        wait_for_condition(
            client, container,
            lambda x: x.state == 'purged',
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

    # After deleting one of the services that uses the volumes , volume state
    # should still be active and we should not be allowed to delete the volume

    delete_all(client, [service1])
    container_list = get_service_container_list(super_client, service1)
    for container in container_list:
        wait_for_condition(
            client, container,
            lambda x: x.state == 'purged',
            lambda x: 'State is: ' + x.state)

    time.sleep(10)
    volume = client.reload(volume)
    assert volume.state == "inactive"
    volume = client.wait_success(client.delete(volume))
    assert volume.state == "removed"
    volume = client.wait_success(volume.purge())
    assert volume.state == "purged"

    delete_all(client, [env, env1])


def write_data(con, port, dir, file, content):
    hostIpAddress = con.dockerHostIp

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print hostIpAddress
    print str(port)
    ssh.connect(hostIpAddress, username="root",
                password="root", port=port)
    cmd1 = "cd " + dir
    cmd2 = "echo '" + content + "' > " + file
    cmd = cmd1 + ";" + cmd2
    logger.info(cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    ssh.close()
    return stdin, stdout, stderr


def read_data(con, port, dir, file):
    hostIpAddress = con.dockerHostIp

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print hostIpAddress
    print str(port)

    ssh.connect(hostIpAddress, username="root",
                password="root", port=port)
    print ssh
    cmd1 = "cd " + dir
    cmd2 = "cat " + file
    cmd = cmd1 + ";" + cmd2

    logger.info(cmd)

    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    assert len(response) == 1
    resp = response[0].strip("\n")
    ssh.close()
    return resp
