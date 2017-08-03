from common_fixtures import *  # NOQA


def test_multiple_az_scheduling(admin_client, client):
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    labels = hosts[0].labels
    labels['az'] = 'east'
    client.update(hosts[0], labels=labels)

    labels2 = hosts[1].labels
    labels2['az'] = 'west'
    client.update(hosts[1], labels=labels2)

    labels = {"io.rancher.scheduler.scale_per_group": "key=az"}
    launch_config = {"imageUuid": "docker:ubuntu",
                     "stdinOpen": True,
                     "labels": labels,
                     }
    scale = 6

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(admin_client, service)
    east_count = 0
    west_count = 0
    for container in container_list:
        if container.hostId == hosts[0].id:
            east_count += 1
        elif container.hostId == hosts[1].id:
            west_count += 1
    assert east_count == 3
    assert west_count == 3
    delete_all(client, [stack])


def test_multiple_az_scheduling_diff_weight(admin_client, client):
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    labels = hosts[0].labels
    labels['az'] = 'east'
    client.update(hosts[0], labels=labels)

    labels2 = hosts[1].labels
    labels2['az'] = 'west'
    client.update(hosts[1], labels=labels2)

    labels = {"io.rancher.scheduler.scale_per_group": "key=az;east=1,west=2"}
    launch_config = {"imageUuid": "docker:ubuntu",
                     "stdinOpen": True,
                     "labels": labels,
                     }
    scale = 6

    service, stack = create_env_and_svc(client, launch_config,
                                      scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(admin_client, service)
    east_count = 0
    west_count = 0
    for container in container_list:
        if container.hostId == hosts[0].id:
            east_count += 1
        elif container.hostId == hosts[1].id:
            west_count += 1
    assert east_count == 2
    assert west_count == 4
    delete_all(client, [stack])


def test_multiple_az_scheduling_one_host(admin_client, client):
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    labels = hosts[0].labels
    labels['az'] = 'east'
    client.update(hosts[0], labels=labels)

    labels2 = hosts[1].labels
    labels2['az'] = 'west'
    client.update(hosts[1], labels=labels2)

    labels = {"io.rancher.scheduler.scale_per_group": "key=az;east=1"}
    launch_config = {"imageUuid": "docker:ubuntu",
                     "stdinOpen": True,
                     "labels": labels,
                     }
    scale = 6

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(admin_client, service)
    east_count = 0
    for container in container_list:
        if container.hostId == hosts[0].id:
            east_count += 1
    assert east_count == 6
    delete_all(client, [stack])


def test_multiple_az_scheduling_adding_host(admin_client, client):
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    labels = hosts[0].labels
    labels['az'] = 'east'
    client.update(hosts[0], labels=labels)

    labels2 = hosts[1].labels
    labels2['az'] = 'west'
    client.update(hosts[1], labels=labels2)

    labels = {"io.rancher.scheduler.scale_per_group": "key=az"}
    launch_config = {"imageUuid": "docker:ubuntu",
                     "stdinOpen": True,
                     "labels": labels,
                     }
    scale = 2

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(admin_client, service)
    east_count = 0
    west_count = 0
    for container in container_list:
        if container.hostId == hosts[0].id:
            east_count += 1
        elif container.hostId == hosts[1].id:
            west_count += 1
    assert east_count == 1
    assert west_count == 1

    labels3 = hosts[2].labels
    labels3['az'] = 'south'
    client.update(hosts[2], labels=labels3)
    time.sleep(1)
    service = client.update(service, scale=scale+1)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    container_list = get_service_container_list(admin_client, service)
    east_count = 0
    west_count = 0
    south_count = 0
    for container in container_list:
        if container.hostId == hosts[0].id:
            east_count += 1
        elif container.hostId == hosts[1].id:
            west_count += 1
        elif container.hostId == hosts[2].id:
            south_count += 1
    assert east_count == 1
    assert west_count == 1
    assert south_count == 1
    labels3 = hosts[2].labels
    try:
        del labels3['az']
    except KeyError:
        pass
    client.update(hosts[2], labels=labels3)
    delete_all(client, [stack])



