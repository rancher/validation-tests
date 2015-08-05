from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def create_environment_with_lb_services(super_client, client,
                                        service_scale, lb_scale, port):

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service.activate()
    lb_service.activate()

    service_link = {"serviceId": service.id}
    lb_service.addservicelink(serviceLink=service_link)

    service = client.wait_success(service, 120)
    lb_service = client.wait_success(lb_service, 120)

    assert service.state == "active"
    assert lb_service.state == "active"

    return env, service, lb_service


def test_lbservice_activate_lb_activate_svc_link(
        super_client, client, socat_containers):

    port = "8900"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_activate_lb_link_activate_svc(
        super_client, client, socat_containers):

    port = "8901"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    lb_service = activate_svc(client, lb_service)
    link_svc_with_port(super_client, lb_service, [service], "80")
    service = activate_svc(client, service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_activate_svc_link_activate_lb(
        super_client, client, socat_containers):

    port = "8902"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service = activate_svc(client, service)
    link_svc_with_port(super_client, lb_service, [service], "80")
    lb_service = activate_svc(client, lb_service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_link_activate_lb_activate_svc(
        super_client, client, socat_containers):

    port = "8903"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    link_svc_with_port(super_client, lb_service, [service], "80")
    lb_service = activate_svc(client, lb_service)
    service = activate_svc(client, service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_link_activate_svc_activate_lb(
        super_client, client, socat_containers):

    port = "8904"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    link_svc_with_port(super_client, lb_service, [service], "80")
    service = activate_svc(client, service)
    lb_service = activate_svc(client, lb_service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_link_when_services_still_activating(
        super_client, client, socat_containers):

    port = "8905"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service.activate()
    lb_service.activate()
    service_link = {"serviceId": service.id}
    lb_service.addservicelink(serviceLink=service_link)

    service = client.wait_success(service, 120)
    lb_service = client.wait_success(lb_service, 120)

    assert service.state == "active"
    assert lb_service.state == "active"
    validate_add_service_link(super_client, lb_service, service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_activate_env(
        super_client, client, socat_containers):

    port = "8925"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service_link = {"serviceId": service.id}
    lb_service.addservicelink(serviceLink=service_link)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    service = client.wait_success(service, 120)
    assert service.state == "active"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_add_service_link(super_client, lb_service, service)

    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_up_service(
        super_client, client, socat_containers):

    port = "9001"

    service_scale = 2
    lb_scale = 1
    final_service_scale = 3

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_down_service(
        super_client, client, socat_containers):

    port = "9002"

    service_scale = 3
    lb_scale = 1

    final_service_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_up_lb_service(
        super_client, client, socat_containers):

    port = "9003"

    service_scale = 2
    lb_scale = 1

    final_lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_down_lb_service(
        super_client, client, socat_containers):

    port = "9004"

    service_scale = 2
    lb_scale = 2

    final_lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_stop_start_instance(
        super_client, client, socat_containers):

    port = "9005"

    service_scale = 3
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    # Stop instance
    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]
    container = client.wait_success(container.stop(), 120)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(super_client, service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_delete_purge_instance(
        super_client, client, socat_containers):

    port = "9006"

    service_scale = 3
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    # Delete instance
    container_name = env.name + "_" + service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(super_client, service)
    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_deactivate_activate_lbservice(
        super_client, client, socat_containers):

    port = "9008"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    lb_service = lb_service.deactivate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "inactive"
    wait_until_instances_get_stopped(super_client, lb_service)

    lb_service = lb_service.activate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_deactivate_activate_service(
        super_client, client, socat_containers):

    port = "9009"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(super_client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_deactivate_activate_environment(
        super_client, client, socat_containers):

    port = "9010"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "inactive"

    wait_until_instances_get_stopped(super_client, lb_service)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_add_remove_servicelinks_service(
        super_client, client, socat_containers):
    port = "9011"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    # Add another service to environment
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

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
    service_link = {"serviceId": service1.id}
    lb_service.addservicelink(serviceLink=service_link)

    validate_add_service_link(super_client, lb_service, service1)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service, service1], lb_service)
    validate_lb_service(super_client, client, lb_service, port,
                        [service, service1])

    # Remove existing service link to the LB service

    service_link = {"serviceId": service.id}
    lb_service.removeservicelink(serviceLink=service_link)

    validate_remove_service_link(super_client, lb_service, service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service1], lb_service)

    validate_lb_service(
        super_client, client,  lb_service, port, [service1])
    delete_all(client, [env])


def test_lb_services_add_remove_servicelinks_lb(
        super_client, client, socat_containers):
    port = "9011"
    port2 = "9111"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

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

    lb2_service.addservicelink(
        serviceLink={"serviceId": service.id})
    validate_add_service_link(super_client, lb2_service, service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb2_service)
    validate_lb_service(super_client, client,
                        lb2_service, port2, [service])

    # Remove existing lB link to service
    lb_service.removeservicelink(
        serviceLink={"serviceId": service.id})
    validate_remove_service_link(super_client, lb_service, service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb2_service)
    validate_lb_service(super_client, client,
                        lb2_service, port2, [service])
    delete_all(client, [env])


def test_lb_services_delete_service_add_service(
        super_client, client, socat_containers):

    port = "9012"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"
    validate_remove_service_link(super_client, lb_service, service)

    # Add another service to environment and link to LB
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

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
    service_link = {"serviceId": service1.id}
    lb_service.addservicelink(serviceLink=service_link)

    validate_add_service_link(super_client, lb_service, service1)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service1], lb_service)
    validate_lb_service(
        super_client, client,  lb_service, port, [service1])

    delete_all(client, [env])


def test_lb_services_delete_lb_service(
        super_client, client, socat_containers):

    port = "9013"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    # Delete LB Service

    lb_service = client.wait_success(client.delete(lb_service))
    assert lb_service.state == "removed"
    validate_remove_service_link(super_client, lb_service, service)

    # Make sure you are able to add another LB service using the same port

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_stop_start_lb_instance_(
        super_client, client, socat_containers):

    port = "9014"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    lb_instances = get_service_container_list(super_client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # Stop lb instance
    lb_instance = client.wait_success(lb_instance.stop(), 120)
    lb_service = client.wait_success(lb_service)

    wait_for_scale_to_adjust(super_client, lb_service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_lb_instance_restart(
        super_client, client, socat_containers):

    port = "9015"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)
    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    lb_instances = get_service_container_list(super_client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # Restart lb instance
    lb_instance = client.wait_success(lb_instance.restart(), 120)
    assert lb_instance.state == 'running'

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_lb_instance_delete(
        super_client, client, socat_containers):

    port = "9016"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_lb_services(
        super_client, client, service_scale, lb_scale, port)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    lb_instances = get_service_container_list(super_client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # delete lb instance
    lb_instance = client.wait_success(client.delete(lb_instance))
    assert lb_instance.state == 'removed'

    wait_for_scale_to_adjust(super_client, lb_service)

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    validate_lb_service(super_client, client, lb_service, port, [service])

    delete_all(client, [env])
