from common_fixtures import *  # NOQA

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"

logger = logging.getLogger(__name__)


def create_env_with_2_svc_dns(client, scale_svc, scale_consumed_svc, port):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    # Create Consumed Service
    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service = client.wait_success(consumed_service)
    assert consumed_service.state == "inactive"

    # Create Consumed Service
    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service1 = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "inactive"

    # Create DNS service

    dns = client.create_dnsService(name='WEB1',
                                   environmentId=env.id)
    dns = client.wait_success(dns)

    return env, service, consumed_service, consumed_service1, dns


def create_environment_with_dns_services(super_client, client,
                                         service_scale,
                                         consumed_service_scale,
                                         port):

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)
    service.activate()
    consumed_service.activate()
    consumed_service1.activate()
    dns.activate()

    service.addservicelink(serviceId=dns.id)
    dns.addservicelink(serviceId=consumed_service.id)
    dns.addservicelink(serviceId=consumed_service1.id)

    service = client.wait_success(service, 120)
    consumed_service = client.wait_success(consumed_service, 120)
    consumed_service1 = client.wait_success(consumed_service1, 120)
    dns = client.wait_success(dns, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    assert consumed_service1.state == "active"

    validate_add_service_link(super_client, service, dns)
    validate_add_service_link(super_client, dns, consumed_service)
    validate_add_service_link(super_client, dns, consumed_service1)

    return env, service, consumed_service, consumed_service1, dns


def test_dns_activate_svc_dns_consumed_svc_link(super_client, client):

    port = "31101"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_activate_consumed_svc_link_activate_svc(super_client, client):

    port = "31102"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    link_svc(super_client, service, [dns])
    link_svc(super_client, dns, [consumed_service, consumed_service1])
    service = activate_svc(client, service)
    consumed_service = activate_svc(client, consumed_service)
    consumed_service1 = activate_svc(client, consumed_service1)
    dns = activate_svc(client, dns)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_activate_svc_link_activate_consumed_svc(super_client, client):

    port = "31103"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    service = activate_svc(client, service)
    consumed_service = activate_svc(client, consumed_service)
    consumed_service1 = activate_svc(client, consumed_service1)
    link_svc(super_client, service, [dns])
    link_svc(super_client, dns, [consumed_service, consumed_service1])
    dns = activate_svc(client, dns)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_link_activate_consumed_svc_activate_svc(super_client, client):

    port = "31104"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    dns = activate_svc(client, dns)
    link_svc(super_client, service, [dns])
    link_svc(super_client, dns, [consumed_service, consumed_service1])
    service = activate_svc(client, service)
    consumed_service = activate_svc(client, consumed_service)
    consumed_service1 = activate_svc(client, consumed_service1)
    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_link_when_services_still_activating(super_client, client):

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

    service.addservicelink(serviceId=dns.id)
    dns.addservicelink(serviceId=consumed_service.id)
    dns.addservicelink(serviceId=consumed_service1.id)

    service = client.wait_success(service, 120)
    consumed_service = client.wait_success(consumed_service, 120)
    consumed_service1 = client.wait_success(consumed_service1, 120)
    dns = client.wait_success(dns, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    assert consumed_service1.state == "active"

    validate_add_service_link(super_client, service, dns)
    validate_add_service_link(super_client, dns, consumed_service)
    validate_add_service_link(super_client, dns, consumed_service1)

    validate_dns_service(super_client, service,
                         [consumed_service, consumed_service1], port, dns.name)

    delete_all(client, [env])


def test_dns_service_scale_up(super_client, client):

    port = "31107"

    service_scale = 1
    consumed_service_scale = 2

    final_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_services_scale_down(super_client, client):

    port = "31108"

    service_scale = 3
    consumed_service_scale = 2

    final_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_scale_up(super_client, client):

    port = "31109"

    service_scale = 1

    consumed_service_scale = 2
    final_consumed_service_scale = 4

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_scale_down(super_client, client):

    port = "3110"

    service_scale = 2
    consumed_service_scale = 3

    final_consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_stop_start_instance(super_client, client):

    port = "3111"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 120)
    service = client.wait_success(consumed_service)
    wait_for_scale_to_adjust(super_client, consumed_service)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_restart_instance(super_client, client):

    port = "3112"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_delete_instance(super_client, client):

    port = "3113"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + consumed_service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(super_client, consumed_service)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_consumed_services_deactivate_activate(super_client, client):

    port = "3114"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    consumed_service = consumed_service.deactivate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"
    time.sleep(60)

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_service_deactivate_activate(super_client, client):

    port = "3115"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    time.sleep(60)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_deactivate_activate_environment(super_client, client):

    port = "3116"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"

    time.sleep(60)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_add_remove_servicelinks(super_client, client):
    port = "3117"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Add another service to environment
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")
    consumed_service2 = client.create_service(name=consumed_service_name,
                                              environmentId=env.id,
                                              launchConfig=launch_config,
                                              scale=2)
    consumed_service2 = client.wait_success(consumed_service2)
    assert consumed_service2.state == "inactive"

    consumed_service2 = consumed_service2.activate()
    consumed_service2 = client.wait_success(consumed_service2, 120)
    assert consumed_service2.state == "active"

    # Add another service link
    dns.addservicelink(serviceId=consumed_service2.id)
    validate_add_service_link(super_client, dns, consumed_service2)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1,
                                consumed_service2], port, dns.name)

    # Remove existing service link to the service
    dns.removeservicelink(serviceId=consumed_service.id)
    validate_remove_service_link(super_client, dns, consumed_service)

    validate_dns_service(
        super_client, service, [consumed_service1, consumed_service2],
        port, dns.name)
    delete_all(client, [env])


def test_dns_services_delete_service_add_service(super_client, client):

    port = "3118"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"
    validate_remove_service_link(super_client, service, dns)

    port1 = "31180"

    # Add another service and link to dns service
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [port1+":22/tcp"]}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     environmentId=env.id,
                                     launchConfig=launch_config,
                                     scale=1)
    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    service1 = service1.activate()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    service1.addservicelink(serviceId=dns.id)
    validate_add_service_link(super_client, service1, dns)

    validate_dns_service(
        super_client, service1, [consumed_service, consumed_service1], port1,
        dns.name)

    delete_all(client, [env])


def test_dns_services_delete_and_add_consumed_service(super_client, client):

    port = "3119"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Delete consume service

    consumed_service = client.wait_success(client.delete(consumed_service))
    assert consumed_service.state == "removed"
    validate_remove_service_link(super_client, dns, consumed_service)

    validate_dns_service(super_client, service, [consumed_service1], port,
                         dns.name)

    # Add another consume service and link the service to this newly created
    # service

    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    consumed_service2 = client.create_service(name=service_name,
                                              environmentId=env.id,
                                              launchConfig=launch_config,
                                              scale=1)
    consumed_service2 = client.wait_success(consumed_service2)
    assert consumed_service2.state == "inactive"

    consumed_service2 = consumed_service2.activate()
    consumed_service2 = client.wait_success(consumed_service2, 120)
    assert consumed_service2.state == "active"

    dns.addservicelink(serviceId=consumed_service2.id)
    validate_add_service_link(super_client, dns, consumed_service2)

    validate_dns_service(
        super_client, service, [consumed_service1, consumed_service2], port,
        dns.name)

    delete_all(client, [env])


def test_dns_services_stop_start_instance(super_client, client):

    port = "3120"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Stop service instance
    service_instance = client.wait_success(service_instance.stop(), 120)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(super_client, service)
    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_services_restart_instance(super_client, client):

    port = "3121"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart service instance
    service_instance = client.wait_success(service_instance.restart(), 120)
    assert service_instance.state == 'running'

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_service_restore_instance(super_client, client):

    port = "3122"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # delete service instance
    service_instance = client.wait_success(client.delete(service_instance))
    assert service_instance.state == 'removed'

    wait_for_scale_to_adjust(super_client, service)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env])


def test_dns_dns_deactivate_activate(super_client, client):

    port = "3114"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    dns = dns.deactivate()
    dns = client.wait_success(dns, 120)
    assert dns.state == "inactive"
    time.sleep(60)

    dns = dns.activate()
    dns = client.wait_success(dns, 120)
    assert dns.state == "active"

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)
    delete_all(client, [env])


def test_dns_add_remove_servicelinks_using_set(super_client, client):
    port = "3117"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            super_client, client, service_scale, consumed_service_scale, port)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    # Add another service to environment
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")
    consumed_service1 = client.create_service(name=consumed_service_name,
                                              environmentId=env.id,
                                              launchConfig=launch_config,
                                              scale=2)
    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "inactive"

    consumed_service1 = consumed_service1.activate()
    consumed_service1 = client.wait_success(consumed_service1, 120)
    assert consumed_service1.state == "active"

    # Add another service link using setservicelinks
    dns.setservicelinks(serviceIds=[consumed_service.id, consumed_service1.id])
    validate_add_service_link(super_client, dns, consumed_service1)

    validate_dns_service(super_client, service,
                         [consumed_service, consumed_service1], port, dns.name)

    # Remove existing service link to the service using setservicelinks
    dns.setservicelinks(serviceIds=[consumed_service1.id])
    validate_remove_service_link(super_client, dns, consumed_service)

    validate_dns_service(super_client, service, [consumed_service1], port,
                         dns.name)
    delete_all(client, [env])


def check_service_map(super_client, service, instance, state):
    instance_service_map = super_client.\
        list_serviceExposeMap(serviceId=service.id, instanceId=instance.id,
                              state=state)
    assert len(instance_service_map) == 1


def get_container_names_list(super_client, env, services):
    container_names = []
    for service in services:
        containers = get_service_container_list(super_client, service)
        for c in containers:
            if c.state == "running":
                container_names.append(c.externalId[:12])
    return container_names


def validate_add_service_link(super_client, service, consumedService):
    service_maps = super_client. \
        list_serviceConsumeMap(serviceId=service.id,
                               consumedServiceId=consumedService.id)
    assert len(service_maps) == 1
    service_map = service_maps[0]
    wait_for_condition(
        super_client, service_map,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state)


def validate_remove_service_link(super_client, service, consumedService):
    service_maps = super_client. \
        list_serviceConsumeMap(serviceId=service.id,
                               consumedServiceId=consumedService.id)
    assert len(service_maps) == 1
    service_map = service_maps[0]
    wait_for_condition(
        super_client, service_map,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)


def get_service_container_list(super_client, service):

    container = []
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        containers = super_client.list_container(
            externalId=c.externalId,
            include="hosts")
        assert len(containers) == 1
        container.append(containers[0])

    return container


def validate_dns_service(super_client, service, consumed_services,
                         exposed_port, dnsname, exclude_instance=None,
                         exclude_instance_purged=False):
    time.sleep(5)

    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == service.scale

    for con in service_containers:
        host = super_client.by_id('host', con.hosts[0].id)

        containers = []
        expected_dns_list = []
        expected_link_response = []
        dns_response = []

        for consumed_service in consumed_services:
            cons = get_service_container_list(super_client, consumed_service)
            if exclude_instance_purged:
                assert len(cons) == consumed_service.scale - 1
            else:
                assert len(cons) == consumed_service.scale
            containers = containers + cons
        for con in containers:
            if (exclude_instance is not None) \
                    and (con.id == exclude_instance.id):
                logger.info("Excluded from DNS and wget list:" + con.name)
            else:
                expected_dns_list.append(con.primaryIpAddress)
                expected_link_response.append(con.externalId[:12])

        logger.info("Expected dig response List" + str(expected_dns_list))
        logger.info("Expected wget response List" +
                    str(expected_link_response))

        # Validate port mapping
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host.ipAddresses()[0].address, username="root",
                    password="root", port=int(exposed_port))

        # Validate link containers
        cmd = "wget -O result.txt http://" + dnsname + \
              ":80/name.html;cat result.txt"
        logger.info(cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        assert len(response) == 1
        resp = response[0].strip("\n")
        logger.info("Actual wget Response" + str(resp))
        assert resp in (expected_link_response)

        # Validate DNS resolution using dig
        cmd = "dig " + dnsname + " +short"
        logger.info(cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        logger.info("Actual dig Response" + str(response))
        assert len(response) == len(expected_dns_list)

        for resp in response:
            dns_response.append(resp.strip("\n"))

        for address in expected_dns_list:
            assert address in dns_response
