from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)


def create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port,
        ssh_port="22", isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=False, linkName=None):

    if not isnetworkModeHost_svc and not isnetworkModeHost_consumed_svc:
        env, service, consumed_service = create_env_with_2_svc(
            client, service_scale, consumed_service_scale, port)
    else:
        env, service, consumed_service = create_env_with_2_svc_hostnetwork(
            client, service_scale, consumed_service_scale, port, ssh_port,
            isnetworkModeHost_svc, isnetworkModeHost_consumed_svc)

    service = client.wait_success(service, 120)
    consumed_service = client.wait_success(consumed_service, 120)
    assert service.state == "active"
    assert consumed_service.state == "active"

    if linkName is None:
        linkName = "mylink"

    service = client.update(
        service,
        serviceLinks=[
            {"type": "link", "name": consumed_service.name, "alias": linkName}
        ])
    return env, service, consumed_service


def test_link_activate_svc_activate_consumed_svc_link(client):

    port = "301"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_link_when_services_still_activating(client):

    port = "306"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    linkName = "mylink"
    service = client.update(
        service,
        serviceLinks=[
            {"type": "link", "name": consumed_service.name, "alias": linkName}
        ])
    service = client.wait_success(service, 120)
    consumed_service = client.wait_success(consumed_service, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"

    validate_linked_service(client, service, [consumed_service], port,
                            linkName=linkName)

    delete_all(client, [env])


def test_link_service_scale_up(client):

    port = "307"

    service_scale = 1
    consumed_service_scale = 2

    final_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_services_scale_down(client):

    port = "308"

    service_scale = 3
    consumed_service_scale = 2

    final_service_scale = 1

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_consumed_services_scale_up(client):

    port = "309"

    service_scale = 1

    consumed_service_scale = 2
    final_consumed_service_scale = 4

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_consumed_services_scale_down(client):

    port = "310"

    service_scale = 2
    consumed_service_scale = 3

    final_consumed_service_scale = 1

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_consumed_services_stop_start_instance(client,
                                                    socat_containers):

    port = "311"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    container_name = get_container_name(env, consumed_service, "2")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    stop_container_from_host(client, container)
    service = wait_state(client, service, "active")

    wait_for_scale_to_adjust(client, consumed_service)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_consumed_services_restart_instance(client):

    port = "312"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    container_name = get_container_name(env, consumed_service, "2")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'
    time.sleep(restart_sleep_interval)
    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_consumed_services_delete_instance(client):

    port = "313"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    container_name = get_container_name(env, consumed_service, "1")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(client, consumed_service)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_consumed_services_deactivate_activate(client):

    port = "314"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    consumed_service = consumed_service.deactivate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"
    wait_until_instances_get_stopped(client, consumed_service)

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_service_deactivate_activate(client):

    port = "315"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"
    time.sleep(restart_sleep_interval)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_deactivate_activate_environment(client):

    port = "316"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    env = env.stopall()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"

    wait_until_instances_get_stopped(client, consumed_service)

    env = env.startall()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    time.sleep(restart_sleep_interval)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_add_remove_servicelinks(client):
    port = "317"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    # Add another service to environment
    launch_config = {"image": WEB_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")
    consumed_service1 = client.create_service(name=consumed_service_name,
                                              stackId=env.id,
                                              launchConfig=launch_config,
                                              scale=2)
    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "active"

    # Add another service link
    service = client.update(
        service,
        serviceLinks=[
            {"type": "link", "name": consumed_service.name, "alias": "mylink"},
            {"type": "link", "name":  consumed_service1.name,
             "alias": "mylink2"}])

    validate_linked_service(client, service,
                            [consumed_service], port,
                            linkName="mylink")
    validate_linked_service(client, service,
                            [consumed_service1], port,
                            linkName="mylink2")

    # Remove existing service link to the service
    service = client.update(
        service,
        serviceLinks=[
            {"type": "link", "name": consumed_service1.name,
             "alias": "mylink2"}])

    validate_linked_service(client, service, [consumed_service1], port,
                            linkName="mylink2")
    delete_all(client, [env])


def test_link_services_delete_service_add_service(client):

    port = "318"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"

    port1 = "3180"

    # Add another service and link to consumed service
    launch_config = {"image": SSH_IMAGE_UUID,
                     "ports": [port1+":22/tcp"]}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config,
                                     scale=1)
    service1 = client.wait_success(service1)
    assert service1.state == "active"

    service1 = client.update(
        service1,
        serviceLinks=[
            {"type": "link", "name": consumed_service.name,
             "alias": "mylink"}])

    validate_linked_service(client, service1, [consumed_service], port1,
                            linkName="mylink")

    delete_all(client, [env])


def test_link_services_delete_and_add_consumed_service(client):

    port = "319"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    # Delete consume service

    consumed_service = client.wait_success(client.delete(consumed_service))
    assert consumed_service.state == "removed"

    # Add another consume service and link the service to this newly created
    # service

    launch_config = {"image": WEB_IMAGE_UUID}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    consumed_service1 = client.create_service(name=service_name,
                                              stackId=env.id,
                                              launchConfig=launch_config,
                                              scale=1)
    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "active"

    service = client.update(
        service,
        serviceLinks=[{"type": "link", "name": consumed_service1.name,
                       "alias": "mylink1"}])
    validate_linked_service(client, service, [consumed_service1], port,
                            linkName="mylink1")

    delete_all(client, [env])


def test_link_services_stop_start_instance(client,
                                           socat_containers):

    port = "320"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    container_name = get_container_name(env, service, "2")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Stop service instance
    stop_container_from_host(client, service_instance)
    service = wait_state(client, service, "active")
    wait_for_scale_to_adjust(client, service)
    time.sleep(restart_sleep_interval)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    delete_all(client, [env])


def test_link_services_restart_instance(client):

    port = "321"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    container_name = get_container_name(env, service, "2")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart consumed instance
    service_instance = client.wait_success(service_instance.restart(), 120)
    assert service_instance.state == 'running'
    time.sleep(restart_sleep_interval)
    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    delete_all(client, [env])


def test_link_services_delete_instance(client):

    port = "322"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port)

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    container_name = get_container_name(env, service, "2")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(service_instance))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(client, service)
    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")

    delete_all(client, [env])


def test_links_with_hostnetwork_1(client):

    port = "323"

    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"
    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port,
        ssh_port, isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=True)
    validate_linked_service(client, service, [consumed_service], port,
                            linkName="mylink")
    delete_all(client, [env])


def test_link_name_uppercase(client):
    port = "326"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        client, service_scale, consumed_service_scale, port,
        linkName="MYUPPERCASELINK")

    validate_linked_service(client, service, [consumed_service], port,
                            linkName="MYUPPERCASELINK")
    delete_all(client, [env])
