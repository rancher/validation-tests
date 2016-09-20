from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)


def create_environment_with_dns_services(admin_client, client,
                                         service_scale,
                                         consumed_service_scale,
                                         port, cross_linking=False,
                                         isnetworkModeHost_svc=False,
                                         isnetworkModeHost_consumed_svc=False):
    if not isnetworkModeHost_svc and not isnetworkModeHost_consumed_svc:
        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns(
                client, service_scale, consumed_service_scale, port,
                cross_linking)
    else:
        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns_hostnetwork(
                client, service_scale, consumed_service_scale, port,
                cross_linking, isnetworkModeHost_svc,
                isnetworkModeHost_consumed_svc)
    service.activate()
    consumed_service.activate()
    consumed_service1.activate()
    dns.activate()

    service.addservicelink(serviceLink={"serviceId": dns.id})
    dns.addservicelink(serviceLink={"serviceId": consumed_service.id})
    dns.addservicelink(serviceLink={"serviceId": consumed_service1.id})

    service = client.wait_success(service, 120)
    consumed_service = client.wait_success(consumed_service, 120)
    consumed_service1 = client.wait_success(consumed_service1, 120)
    dns = client.wait_success(dns, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    assert consumed_service1.state == "active"

    validate_add_service_link(admin_client, service, dns)
    validate_add_service_link(admin_client, dns, consumed_service)
    validate_add_service_link(admin_client, dns, consumed_service1)

    return env, service, consumed_service, consumed_service1, dns


def test_dns_activate_svc_dns_consumed_svc_link(admin_client, client):

    port = "31100"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_cross_link(admin_client, client):

    port = "31101"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale,
            port, True)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env, get_env(admin_client, consumed_service),
                        get_env(admin_client, consumed_service1), dns])


def test_dns_activate_consumed_svc_link_activate_svc(admin_client, client):

    port = "31102"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    link_svc(admin_client, service, [dns])
    link_svc(admin_client, dns, [consumed_service, consumed_service1])
    service = activate_svc(client, service)
    consumed_service = activate_svc(client, consumed_service)
    consumed_service1 = activate_svc(client, consumed_service1)
    dns = activate_svc(client, dns)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_activate_svc_link_activate_consumed_svc(admin_client, client):

    port = "31103"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    service = activate_svc(client, service)
    consumed_service = activate_svc(client, consumed_service)
    consumed_service1 = activate_svc(client, consumed_service1)
    link_svc(admin_client, service, [dns])
    link_svc(admin_client, dns, [consumed_service, consumed_service1])
    dns = activate_svc(client, dns)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_link_activate_consumed_svc_activate_svc(admin_client, client):

    port = "31104"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    dns = activate_svc(client, dns)
    link_svc(admin_client, service, [dns])
    link_svc(admin_client, dns, [consumed_service, consumed_service1])
    service = activate_svc(client, service)
    consumed_service = activate_svc(client, consumed_service)
    consumed_service1 = activate_svc(client, consumed_service1)
    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_link_when_services_still_activating(admin_client, client):

    port = "31106"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    service.activate()
    consumed_service.activate()
    consumed_service1.activate()
    dns.activate()

    service.addservicelink(serviceLink={"serviceId": dns.id})
    dns.addservicelink(serviceLink={"serviceId": consumed_service.id})
    dns.addservicelink(serviceLink={"serviceId": consumed_service1.id})

    service = client.wait_success(service, 120)
    consumed_service = client.wait_success(consumed_service, 120)
    consumed_service1 = client.wait_success(consumed_service1, 120)
    dns = client.wait_success(dns, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    assert consumed_service1.state == "active"

    validate_add_service_link(admin_client, service, dns)
    validate_add_service_link(admin_client, dns, consumed_service)
    validate_add_service_link(admin_client, dns, consumed_service1)

    validate_dns_service(admin_client, service,
                         [consumed_service, consumed_service1], port, dns.name)

    delete_all(client, [env])


def test_dns_service_scale_up(admin_client, client):

    port = "31107"

    service_scale = 1
    consumed_service_scale = 2

    final_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_services_scale_down(admin_client, client):

    port = "31108"

    service_scale = 3
    consumed_service_scale = 2

    final_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_scale_up(admin_client, client):

    port = "31109"

    service_scale = 1

    consumed_service_scale = 2
    final_consumed_service_scale = 4

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_scale_down(admin_client, client):

    port = "3110"

    service_scale = 2
    consumed_service_scale = 3

    final_consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_stop_start_instance(admin_client, client):

    port = "3111"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 120)
    consumed_service = wait_state(client, consumed_service, "active")
    wait_for_scale_to_adjust(admin_client, consumed_service)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_restart_instance(admin_client, client):

    port = "3112"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_delete_instance(admin_client, client):

    port = "3113"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + consumed_service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(admin_client, consumed_service)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_deactivate_activate(admin_client, client):

    port = "3114"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = consumed_service.deactivate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"
    wait_until_instances_get_stopped(admin_client, consumed_service)

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_service_deactivate_activate(admin_client, client):

    port = "3115"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(admin_client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_deactivate_activate_environment(admin_client, client):

    port = "3116"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"

    wait_until_instances_get_stopped(admin_client, service)
    wait_until_instances_get_stopped(admin_client, consumed_service)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_add_remove_servicelinks(admin_client, client):
    port = "3117"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Add another service to environment
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")
    consumed_service2 = client.create_service(name=consumed_service_name,
                                              stackId=env.id,
                                              launchConfig=launch_config,
                                              scale=2)
    consumed_service2 = client.wait_success(consumed_service2)
    assert consumed_service2.state == "inactive"

    consumed_service2 = consumed_service2.activate()
    consumed_service2 = client.wait_success(consumed_service2, 120)
    assert consumed_service2.state == "active"

    # Add another service link
    dns.addservicelink(serviceLink={"serviceId": consumed_service2.id})
    validate_add_service_link(admin_client, dns, consumed_service2)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1,
                                consumed_service2], port, dns.name)

    # Remove existing service link to the service
    dns.removeservicelink(serviceLink={"serviceId": consumed_service.id})
    validate_remove_service_link(admin_client, dns, consumed_service)

    validate_dns_service(
        admin_client, service, [consumed_service1, consumed_service2],
        port, dns.name)
    delete_all(client, [env])


def test_dns_services_delete_service_add_service(admin_client, client):

    port = "3118"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"
    validate_remove_service_link(admin_client, service, dns)

    port1 = "31180"

    # Add another service and link to dns service
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [port1+":22/tcp"]}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config,
                                     scale=1)
    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    service1 = service1.activate()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    service1.addservicelink(serviceLink={"serviceId": dns.id})
    validate_add_service_link(admin_client, service1, dns)

    validate_dns_service(
        admin_client, service1, [consumed_service, consumed_service1], port1,
        dns.name)

    delete_all(client, [env])


def test_dns_services_delete_and_add_consumed_service(admin_client, client):

    port = "3119"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Delete consume service

    consumed_service = client.wait_success(client.delete(consumed_service))
    assert consumed_service.state == "removed"
    validate_remove_service_link(admin_client, dns, consumed_service)

    validate_dns_service(admin_client, service, [consumed_service1], port,
                         dns.name)

    # Add another consume service and link the service to this newly created
    # service

    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    consumed_service2 = client.create_service(name=service_name,
                                              stackId=env.id,
                                              launchConfig=launch_config,
                                              scale=1)
    consumed_service2 = client.wait_success(consumed_service2)
    assert consumed_service2.state == "inactive"

    consumed_service2 = consumed_service2.activate()
    consumed_service2 = client.wait_success(consumed_service2, 120)
    assert consumed_service2.state == "active"

    service_link = {"serviceId": consumed_service2.id}
    dns.addservicelink(serviceLink=service_link)

    validate_add_service_link(admin_client, dns, consumed_service2)

    validate_dns_service(
        admin_client, service, [consumed_service1, consumed_service2], port,
        dns.name)

    delete_all(client, [env])


def test_dns_services_stop_start_instance(admin_client, client):

    port = "3120"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Stop service instance
    service_instance = client.wait_success(service_instance.stop(), 120)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(admin_client, service)
    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_services_restart_instance(admin_client, client):

    port = "3121"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart service instance
    service_instance = client.wait_success(service_instance.restart(), 120)
    assert service_instance.state == 'running'

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_service_restore_instance(admin_client, client):

    port = "3122"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # delete service instance
    service_instance = client.wait_success(client.delete(service_instance))
    assert service_instance.state == 'removed'

    wait_for_scale_to_adjust(admin_client, service)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_dns_deactivate_activate(admin_client, client):

    port = "3114"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    dns = dns.deactivate()
    dns = client.wait_success(dns, 120)
    assert dns.state == "inactive"

    dns = dns.activate()
    dns = client.wait_success(dns, 120)
    assert dns.state == "active"

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_add_remove_servicelinks_using_set(admin_client, client):
    port = "3117"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Add another service to environment
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")
    consumed_service1 = client.create_service(name=consumed_service_name,
                                              stackId=env.id,
                                              launchConfig=launch_config,
                                              scale=2)
    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "inactive"

    consumed_service1 = consumed_service1.activate()
    consumed_service1 = client.wait_success(consumed_service1, 120)
    assert consumed_service1.state == "active"

    # Add another service link using setservicelinks

    service_link1 = {"serviceId": consumed_service.id}
    service_link2 = {"serviceId": consumed_service1.id}

    dns.setservicelinks(serviceLinks=[service_link1, service_link2])

    validate_add_service_link(admin_client, dns, consumed_service1)

    validate_dns_service(admin_client, service,
                         [consumed_service, consumed_service1], port, dns.name)

    # Remove existing service link to the service using setservicelinks
    dns.setservicelinks(serviceLinks=[service_link2])
    validate_remove_service_link(admin_client, dns, consumed_service)

    validate_dns_service(admin_client, service, [consumed_service1], port,
                         dns.name)
    delete_all(client, [env])


def test_dns_svc_cosumed_service_hostnetwork(admin_client, client):

    port = "3118"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_svc_managed_cosumed_service_hostnetwork(admin_client, client):

    port = "3118"

    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=False, isnetworkModeHost_consumed_svc=True)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_svc_hostnetwork_cosumed_service_hostnetwork(admin_client, client):

    port = "3119"

    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=True, isnetworkModeHost_consumed_svc=True)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], "33",
        dns.name)

    delete_all(client, [env])


def test_dns_svc_hostnetwork_cosumed_service_managednetwork(
        admin_client, client):

    port = "3119"

    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            admin_client, client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=True, isnetworkModeHost_consumed_svc=False)

    validate_dns_service(
        admin_client, service, [consumed_service, consumed_service1], "33",
        dns.name)

    delete_all(client, [env])
