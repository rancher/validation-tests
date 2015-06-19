from common_fixtures import *  # NOQA

LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/test:latest"


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def create_env_with_svc_and_lb(client, scale_svc, scale_lb, port):

    launch_config_svc = {"imageUuid": LB_IMAGE_UUID}

    launch_config_lb = {"ports": [port+":80"]}

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

    # Create LB Service
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=scale_lb)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    return env, service, lb_service


def link_svc(super_client, service, linkservices):

    for linkservice in linkservices:
        service = service.addservicelink(serviceId=linkservice.id)
        validate_add_service_link(super_client, service, linkservice)
    return service


def activate_svc(client, service):

    service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"
    return service


def create_environment_with_lb_services(super_client, client,
                                        service_scale, lb_scale, port):

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service = activate_svc(client, service)
    lb_service = activate_svc(client, lb_service)
    link_svc(super_client, lb_service, [service])

    return env, service, lb_service


def test_lbservice_activate_lb_activate_svc_link(super_client, client):

    port = "8900"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lbservice_activate_lb_link_activate_svc(super_client, client):

    port = "8901"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    lb_service = activate_svc(client, lb_service)
    link_svc(super_client, lb_service, [service])
    service = activate_svc(client, service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lbservice_activate_svc_link_activate_lb(super_client, client):

    port = "8902"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service = activate_svc(client, service)
    link_svc(super_client, lb_service, [service])
    lb_service = activate_svc(client, lb_service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lbservice_link_activate_lb_activate_svc(super_client, client):

    port = "8903"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    link_svc(super_client, lb_service, [service])
    lb_service = activate_svc(client, lb_service)
    service = activate_svc(client, service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lbservice_link_activate_svc_activate_lb(super_client, client):

    port = "8904"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    link_svc(super_client, lb_service, [service])
    service = activate_svc(client, service)
    lb_service = activate_svc(client, lb_service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lbservice_link_when_services_still_activating(super_client, client):

    port = "8905"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service.activate()
    lb_service.activate()
    lb_service.addservicelink(serviceId=service.id)

    service = client.wait_success(service, 120)
    lb_service = client.wait_success(lb_service, 120)

    assert service.state == "active"
    assert lb_service.state == "active"
    validate_add_service_link(super_client, lb_service, service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_activate_env(super_client, client):

    port = "8925"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    lb_service.addservicelink(serviceId=service.id)

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_add_service_link(super_client, lb_service, service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_scale_up_service(super_client, client):

    port = "9001"

    service_scale = 2
    lb_scale = 1
    final_service_scale = 3

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_scale_down_service(super_client, client):

    port = "9002"

    service_scale = 3
    lb_scale = 1

    final_service_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_scale_up_lb_service(super_client, client):

    port = "9003"

    service_scale = 2
    lb_scale = 1

    final_lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_scale_down_lb_service(super_client, client):

    port = "9004"

    service_scale = 2
    lb_scale = 2

    final_lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_stop_start_instance(super_client, client):

    port = "9005"

    service_scale = 3
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    # Stop instance
    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]
    container = client.wait_success(container.stop(), 120)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(super_client, service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_delete_purge_instance(super_client, client):

    port = "9006"

    service_scale = 3
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    # Delete instance
    container_name = env.name + "_" + service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(super_client, service)
    validate_lb_service(super_client, client, env, [service], lb_service, port)

    delete_all(client, [env])


def test_lb_services_deactivate_activate_lbservice(super_client, client):

    port = "9008"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    lb_service = lb_service.deactivate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "inactive"
    time.sleep(60)

    lb_service = lb_service.activate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_deactivate_activate_service(super_client, client):

    port = "9009"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    time.sleep(60)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_deactivate_activate_environment(super_client, client):

    port = "9010"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "inactive"

    time.sleep(60)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_service(super_client, client, env, [service], lb_service, port)
    delete_all(client, [env])


def test_lb_services_add_remove_servicelinks_service(super_client, client):
    port = "9011"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    # Add another service to environment
    launch_config = {"imageUuid": LB_IMAGE_UUID}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     environmentId=env.id,
                                     launchConfig=launch_config,
                                     scale=2)
    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    service1 = service1.activate()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    # Add another service link to the LB service
    lb_service.addservicelink(serviceId=service1.id)
    validate_add_service_link(super_client, lb_service, service1)

    validate_lb_service(super_client, client, env, [service, service1],
                        lb_service, port)

    # Remove existing service link to the LB service
    lb_service.removeservicelink(serviceId=service.id)
    validate_remove_service_link(super_client, lb_service, service)

    validate_lb_service(super_client, client, env, [service1], lb_service,
                        port)
    delete_all(client, [env])


def test_lb_services_add_remove_servicelinks_lb(super_client, client):
    port = "9011"
    port2 = "9111"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    # Add another LB service to environment
    launch_config_lb = {"ports": [port2+":80"]}
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb2_service = client.create_loadBalancerService(
        name=service_name, environmentId=env.id, launchConfig=launch_config_lb,
        scale=1)

    lb2_service = client.wait_success(lb2_service)
    assert lb2_service.state == "inactive"

    lb2_service = lb2_service.activate()
    service1 = client.wait_success(lb2_service, 120)
    assert service1.state == "active"

    # Link this LB to the existing service

    lb2_service.addservicelink(serviceId=service.id)
    validate_add_service_link(super_client, lb2_service, service)

    validate_lb_service(super_client, client, env, [service],
                        lb2_service, port2)

    # Remove existing lB link to service
    lb_service.removeservicelink(serviceId=service.id)
    validate_remove_service_link(super_client, lb_service, service)

    validate_lb_service(super_client, client, env, [service],
                        lb2_service, port2)
    delete_all(client, [env])


def test_lb_services_delete_service_add_service(super_client, client):

    port = "9012"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"
    validate_remove_service_link(super_client, lb_service, service)

    # Add another service to environment and link to LB
    launch_config = {"imageUuid": LB_IMAGE_UUID}

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

    # Add another service link to the LB service
    lb_service.addservicelink(serviceId=service1.id)
    validate_add_service_link(super_client, lb_service, service1)

    validate_lb_service(super_client, client, env, [service1],
                        lb_service, port)

    delete_all(client, [env])


def test_lb_services_delete_lb_service(super_client, client):

    port = "9013"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    # Delete LB Service

    lb_service = client.wait_success(client.delete(lb_service))
    assert lb_service.state == "removed"
    validate_remove_service_link(super_client, lb_service, service)

    # Make sure you are able to add another LB service using the same port

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    delete_all(client, [env])


def test_lb_services_stop_start_lb_instance_(super_client, client):

    port = "9014"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    lb_instances = get_service_container_list(super_client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # Stop lb instance
    lb_instance = client.wait_success(lb_instance.stop(), 120)
    service = client.wait_success(lb_service)

    wait_for_scale_to_adjust(super_client, lb_service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    delete_all(client, [env])


def test_lb_services_lb_instance_restart(super_client, client):

    port = "9015"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    lb_instances = get_service_container_list(super_client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # Restart lb instance
    lb_instance = client.wait_success(lb_instance.restart(), 120)
    assert lb_instance.state == 'running'

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    delete_all(client, [env])


def test_lb_services_lb_instance_delete(super_client, client):

    port = "9016"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    lb_instances = get_service_container_list(super_client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # delete lb instance
    lb_instance = client.wait_success(client.delete(lb_instance))
    assert lb_instance.state == 'removed'

    wait_for_scale_to_adjust(super_client, lb_service)

    validate_lb_service(super_client, client, env, [service], lb_service, port)

    delete_all(client, [env])


def check_round_robin_access(container_names, host, port):
    con_hostname = container_names[:]
    con_hostname_ordered = []

    url = "http://" + host.ipAddresses()[0].address +\
          ":" + port + "/name.html"

    logger.info(url)

    for n in range(0, len(con_hostname)):
        r = requests.get(url)
        response = r.text.strip("\n")
        logger.info(response)
        r.close()
        assert response in con_hostname
        con_hostname.remove(response)
        con_hostname_ordered.append(response)

    logger.info(con_hostname_ordered)

    i = 0
    for n in range(0, 10):
        r = requests.get(url)
        response = r.text.strip("\n")
        r.close()
        logger.info(response)
        assert response == con_hostname_ordered[i]
        i = i + 1
        if i == len(con_hostname_ordered):
            i = 0


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


def validate_lb_service(super_client, client, env, services, lb_service, port,
                        exclude_instance=None):

    lbs = client.list_loadBalancer(serviceId=lb_service.id)
    assert len(lbs) == 1

    lb = lbs[0]

    # Wait for host maps to get created and reach "active" state
    host_maps = wait_until_host_map_created(client, lb, lb_service.scale)
    assert len(host_maps) == lb_service.scale

    logger.info("host_maps - " + str(host_maps))

    target_count = 0
    for service in services:
        target_count = target_count + service.scale

    # Wait for target maps to get created and reach "active" state

    target_maps = wait_until_target_map_created(client, lb, target_count)
    logger.info(target_maps)

    lb_hosts = []

    for host_map in host_maps:
        host = client.by_id('host', host_map.hostId)
        lb_hosts.append(host)
        logger.info("host: " + host.name)

    container_names = get_container_names_list(super_client, env, services)
    logger.info(container_names)

    if exclude_instance is None:
        assert len(container_names) == target_count
    else:
        list_length = target_count - 1
        assert len(container_names) == list_length
        assert exclude_instance.externalId[:12] not in container_names

    for host in lb_hosts:
        wait_until_lb_is_active(host, port)
        check_round_robin_access(container_names, host, port)


def wait_until_target_map_created(client, lb, count, timeout=30):
    start = time.time()
    target_maps = client.list_loadBalancerTarget(loadBalancerId=lb.id,
                                                 removed_null=True,
                                                 state="active")
    while len(target_maps) != count:
        time.sleep(.5)
        target_maps = client. \
            list_loadBalancerTarget(loadBalancerId=lb.id, removed_null=True,
                                    state="active")
        if time.time() - start > timeout:
            raise Exception('Timed out waiting for map creation')
    return target_maps


def wait_until_host_map_created(client, lb, count, timeout=30):
    start = time.time()
    host_maps = client.list_loadBalancerHostMap(loadBalancerId=lb.id,
                                                removed_null=True,
                                                state="active")
    while len(host_maps) != count:
        time.sleep(.5)
        host_maps = client. \
            list_loadBalancerHostMap(loadBalancerId=lb.id, removed_null=True,
                                     state="active")
        if time.time() - start > timeout:
            raise Exception('Timed out waiting for map creation')
    return host_maps


def wait_until_target_maps_removed(super_client, lb, consumed_service):
    instance_maps = super_client.list_serviceExposeMap(
        serviceId=consumed_service.id)
    for instance_map in instance_maps:
        target_maps = super_client.list_loadBalancerTarget(
            loadBalancerId=lb.id, instanceId=instance_map.instanceId)
        assert len(target_maps) == 1
        target_map = target_maps[0]
        wait_for_condition(
            super_client, target_map,
            lambda x: x.state == "removed",
            lambda x: 'State is: ' + x.state)


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

    lbs = super_client.list_loadBalancer(serviceId=service.id)
    assert len(lbs) == 1
    lb = lbs[0]
    wait_until_target_maps_removed(super_client, lb, consumedService)


def get_service_container_list(super_client, service):

    container = []
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        container.append(c)

    assert len(container) == service.scale
    return container


def wait_until_lb_is_active(host, port, timeout=30):
    start = time.time()
    while check_for_no_access(host, port):
        time.sleep(.5)
        print "No access yet"
        if time.time() - start > timeout:
            raise Exception('Timed out waiting for LB to become active')
    return


def check_for_no_access(host, port):
    try:
        url = "http://" + host.ipAddresses()[0].address + ":" +\
              port + "/name.html"
        requests.get(url)
        return False
    except requests.ConnectionError:
        logger.info("Connection Error - " + url)
        return True
