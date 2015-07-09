from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)


def create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port):

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    service.activate()
    consumed_service.activate()

    service.addservicelink(serviceLink={"serviceId": consumed_service.id})
    service = client.wait_success(service, 120)

    consumed_service = client.wait_success(consumed_service, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    validate_add_service_link(super_client, service, consumed_service)

    return env, service, consumed_service


def test_link_activate_svc_activate_consumed_svc_link(super_client, client):

    port = "301"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_link_activate_consumed_svc_link_activate_svc(super_client, client):

    port = "302"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    consumed_service = activate_svc(client, consumed_service)
    link_svc(super_client, service, [consumed_service])
    service = activate_svc(client, service)

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_activate_svc_link_activate_consumed_svc(super_client, client):

    port = "303"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    service = activate_svc(client, service)
    link_svc(super_client, service, [consumed_service])
    consumed_service = activate_svc(client, consumed_service)

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_link_activate_consumed_svc_activate_svc(super_client, client):

    port = "304"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    link_svc(super_client, service, [consumed_service])
    consumed_service = activate_svc(client, consumed_service)
    service = activate_svc(client, service)

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_link_activate_svc_activate_consumed_svc(super_client, client):

    port = "305"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    link_svc(super_client, service, [consumed_service])
    service = activate_svc(client, service)
    consumed_service = activate_svc(client, consumed_service)

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_link_when_services_still_activating(super_client, client):

    port = "306"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    service.activate()
    consumed_service.activate()

    service.addservicelink(serviceLink={"serviceId": consumed_service.id})
    service = client.wait_success(service, 120)

    consumed_service = client.wait_success(consumed_service, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    validate_add_service_link(super_client, service, consumed_service)

    validate_linked_service(super_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_link_service_scale_up(super_client, client):

    port = "307"

    service_scale = 1
    consumed_service_scale = 2

    final_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_services_scale_down(super_client, client):

    port = "308"

    service_scale = 3
    consumed_service_scale = 2

    final_service_scale = 1

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_consumed_services_scale_up(super_client, client):

    port = "309"

    service_scale = 1

    consumed_service_scale = 2
    final_consumed_service_scale = 4

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_consumed_services_scale_down(super_client, client):

    port = "310"

    service_scale = 2
    consumed_service_scale = 3

    final_consumed_service_scale = 1

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_consumed_services_stop_start_instance(super_client, client):

    port = "311"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 120)
    service = client.wait_success(service)

    wait_for_scale_to_adjust(super_client, consumed_service)

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_consumed_services_restart_instance(super_client, client):

    port = "312"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    container_name = env.name + "_" + consumed_service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_consumed_services_delete_instance(super_client, client):

    port = "313"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    container_name = env.name + "_" + consumed_service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(super_client, consumed_service)

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_consumed_services_deactivate_activate(super_client, client):

    port = "314"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    consumed_service = consumed_service.deactivate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"
    wait_until_instances_get_stopped(super_client, consumed_service)

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_service_deactivate_activate(super_client, client):

    port = "315"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(super_client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_deactivate_activate_environment(super_client, client):

    port = "316"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "inactive"

    wait_until_instances_get_stopped(super_client, consumed_service)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    consumed_service = client.wait_success(consumed_service, 120)
    assert consumed_service.state == "active"

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_link_add_remove_servicelinks(super_client, client):
    port = "317"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

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

    # Add another service link
    service.addservicelink(serviceLink={"serviceId": consumed_service1.id})
    validate_add_service_link(super_client, service, consumed_service1)

    validate_linked_service(super_client, service,
                            [consumed_service, consumed_service1], port)

    # Remove existing service link to the service
    service.removeservicelink(serviceLink={"serviceId": consumed_service.id})
    validate_remove_service_link(super_client, service, consumed_service)

    validate_linked_service(super_client, service, [consumed_service1], port)
    delete_all(client, [env])


def test_link_services_delete_service_add_service(super_client, client):

    port = "318"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"
    validate_remove_service_link(super_client, service, consumed_service)

    port1 = "3180"

    # Add another service and link to consumed service
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

    service1.addservicelink(serviceLink={"serviceId": consumed_service.id})
    validate_add_service_link(super_client, service1, consumed_service)

    validate_linked_service(super_client, service1, [consumed_service], port1)

    delete_all(client, [env])


def test_link_services_delete_and_add_consumed_service(super_client, client):

    port = "319"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    # Delete consume service

    consumed_service = client.wait_success(client.delete(consumed_service))
    assert consumed_service.state == "removed"
    validate_remove_service_link(super_client, service, consumed_service)

    # Add another consume service and link the service to this newly created
    # service

    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    consumed_service1 = client.create_service(name=service_name,
                                              environmentId=env.id,
                                              launchConfig=launch_config,
                                              scale=1)
    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "inactive"

    consumed_service1 = consumed_service1.activate()
    consumed_service1 = client.wait_success(consumed_service1, 120)
    assert consumed_service1.state == "active"

    service.addservicelink(serviceLink={"serviceId": consumed_service1.id})
    validate_add_service_link(super_client, service, consumed_service1)

    validate_linked_service(super_client, service, [consumed_service1], port)

    delete_all(client, [env])


def test_link_services_stop_start_instance(super_client, client):

    port = "320"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Stop service instance
    service_instance = client.wait_success(service_instance.stop(), 120)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(super_client, service)

    validate_linked_service(super_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_link_services_restart_instance(super_client, client):

    port = "321"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart consumed instance
    service_instance = client.wait_success(service_instance.restart(), 120)
    assert service_instance.state == 'running'

    validate_linked_service(super_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_link_services_delete_instance(super_client, client):

    port = "322"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_linked_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(service_instance))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(super_client, service)
    validate_linked_service(super_client, service, [consumed_service], port)

    delete_all(client, [env])
