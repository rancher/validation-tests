from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)


def test_dns_activate_svc_dns_consumed_svc_link(client):

    port = "31100"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_cross_link(client):

    port = "31101"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale,
            port, True)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env, get_env(client, consumed_service),
                        get_env(client, consumed_service1), dns])


def test_dns_service_scale_up(client):

    port = "31107"

    service_scale = 1
    consumed_service_scale = 2

    final_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_services_scale_down(client):

    port = "31108"

    service_scale = 3
    consumed_service_scale = 2

    final_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_scale_up(client):

    port = "31109"

    service_scale = 1

    consumed_service_scale = 2
    final_consumed_service_scale = 4

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_scale_down(client):

    port = "3110"

    service_scale = 2
    consumed_service_scale = 3

    final_consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_stop_start_instance(client,
                                                   socat_containers):

    port = "3111"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = get_container_name(env, consumed_service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    stop_container_from_host(client, container)
    consumed_service = wait_state(client, consumed_service, "active")
    wait_for_scale_to_adjust(client, consumed_service)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_restart_instance(client):

    port = "3112"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    container_name = get_container_name(env, consumed_service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_delete_instance(client):

    port = "3113"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = get_container_name(env, consumed_service, 1)

    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(client, consumed_service)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_deactivate_activate(client):

    port = "3114"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = consumed_service.deactivate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"
    wait_until_instances_get_stopped(client, consumed_service)

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_service_deactivate_activate(client):

    port = "3115"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"
    time.sleep(restart_sleep_interval)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_deactivate_activate_environment(client):

    port = "3116"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"

    wait_until_instances_get_stopped(client, service)
    wait_until_instances_get_stopped(client, consumed_service)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    time.sleep(restart_sleep_interval)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_add_remove_servicelinks(client):
    port = "3117"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Add another service to environment
    launch_config = {"image": WEB_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")
    consumed_service2 = client.create_service(name=consumed_service_name,
                                              stackId=env.id,
                                              launchConfig=launch_config,
                                              scale=2)
    consumed_service2 = client.wait_success(consumed_service2, 120)
    assert consumed_service2.state == "active"

    # Add another service link
    dns = client.update(dns,
                        serviceLinks=[
                            {"type": "link", "name": consumed_service.name},
                            {"type": "link", "name": consumed_service1.name},
                            {"type": "link", "name": consumed_service2.name}])
    dns = client.wait_success(dns, timeout=60)
    validate_dns_service(
        client, service, [consumed_service, consumed_service1,
                          consumed_service2], port, dns.name)

    # Remove existing service link to the service
    dns = client.update(dns,
                        serviceLinks=[
                            {"type": "link", "name": consumed_service1.name},
                            {"type": "link", "name": consumed_service2.name}])

    dns = client.wait_success(dns, timeout=60)
    validate_dns_service(
        client, service, [consumed_service1, consumed_service2],
        port, dns.name)
    delete_all(client, [env])


def test_dns_services_delete_and_add_consumed_service(client):

    port = "3119"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Delete consume service

    consumed_service = client.wait_success(client.delete(consumed_service))
    assert consumed_service.state == "removed"

    validate_dns_service(client, service, [consumed_service1], port,
                         dns.name)

    # Add another consume service and link the service to this newly created
    # service

    launch_config = {"image": WEB_IMAGE_UUID}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    consumed_service2 = client.create_service(name=service_name,
                                              stackId=env.id,
                                              launchConfig=launch_config,
                                              scale=1)
    consumed_service2 = client.wait_success(consumed_service2)
    assert consumed_service2.state == "active"

    dns = client.update(dns,
                        serviceLinks=[
                            {"type": "link", "name": consumed_service1.name},
                            {"type": "link", "name": consumed_service2.name}])
    dns = client.wait_success(dns, timeout=60)
    validate_dns_service(
        client, service, [consumed_service1, consumed_service2], port,
        dns.name)

    delete_all(client, [env])


def test_dns_services_stop_start_instance(client,
                                          socat_containers):

    port = "3120"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = get_container_name(env, service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Stop service instance
    stop_container_from_host(client, service_instance)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(client, service)
    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_services_restart_instance(client):

    port = "3121"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = get_container_name(env, service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart service instance
    service_instance = client.wait_success(service_instance.restart(), 120)
    assert service_instance.state == 'running'
    time.sleep(restart_sleep_interval)
    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_service_restore_instance(client):

    port = "3122"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = get_container_name(env, service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # delete service instance
    service_instance = client.wait_success(client.delete(service_instance))
    assert service_instance.state == 'removed'

    wait_for_scale_to_adjust(client, service)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_dns_deactivate_activate(client):

    port = "3114"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    dns = dns.deactivate()
    dns = client.wait_success(dns, 120)
    assert dns.state == "inactive"

    dns = dns.activate()
    dns = client.wait_success(dns, 120)
    assert dns.state == "active"

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_svc_managed_cosumed_service_hostnetwork(client):

    port = "3118"

    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=False, isnetworkModeHost_consumed_svc=True)

    validate_dns_service(
        client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_svc_hostnetwork_cosumed_service_hostnetwork(client):

    port = "3119"

    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=True, isnetworkModeHost_consumed_svc=True)

    dns_name = dns.name + "." + env.name + "." + RANCHER_FQDN
    validate_dns_service(
        client, service, [consumed_service, consumed_service1], "33",
        dns_name)
    delete_all(client, [env])


def test_dns_svc_hostnetwork_cosumed_service_managednetwork(
        client):

    port = "3119"

    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=True, isnetworkModeHost_consumed_svc=False)

    dns_name = dns.name + "." + env.name + "." + RANCHER_FQDN
    validate_dns_service(
        client, service, [consumed_service, consumed_service1], "33",
        dns_name)

    delete_all(client, [env])
