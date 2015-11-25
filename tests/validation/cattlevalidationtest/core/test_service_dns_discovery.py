from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)


def create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port,
        ssh_port="22", isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=False):

    if not isnetworkModeHost_svc and not isnetworkModeHost_consumed_svc:
        env, service, consumed_service = create_env_with_2_svc(
            client, service_scale, consumed_service_scale, port)
    else:
        env, service, consumed_service = create_env_with_2_svc_hostnetwork(
            client, service_scale, consumed_service_scale, port, ssh_port,
            isnetworkModeHost_svc, isnetworkModeHost_consumed_svc)
    service.activate()
    consumed_service.activate()

    service = client.wait_success(service, 120)

    consumed_service = client.wait_success(consumed_service, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    return env, service, consumed_service


def test_dns_discovery_activate_svc_activate_consumed_svc_link(
        super_client, client):

    port = "401"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_dns_discovery_service_scale_up(super_client, client):

    port = "402"

    service_scale = 1
    consumed_service_scale = 2

    final_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_services_scale_down(super_client, client):

    port = "403"

    service_scale = 3
    consumed_service_scale = 2

    final_service_scale = 1

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_consumed_services_scale_up(super_client, client):

    port = "404"

    service_scale = 1

    consumed_service_scale = 2
    final_consumed_service_scale = 4

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discovery_consumed_services_scale_down(super_client, client):

    port = "405"

    service_scale = 2
    consumed_service_scale = 3

    final_consumed_service_scale = 1

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discovery_consumed_services_stop_start_instance(
        super_client, client):

    port = "406"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discovery_consumed_services_restart_instance(
        super_client, client):

    port = "407"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discovery_consumed_services_delete_instance(super_client, client):

    port = "408"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discovery_consumed_services_deactivate_activate(
        super_client, client):

    port = "409"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discovery_service_deactivate_activate(super_client, client):

    port = "410"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discovery_deactivate_activate_environment(super_client, client):

    port = "411"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port,
                            )

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


def test_dns_discovery_services_stop_start_instance(super_client, client):

    port = "416"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port,
                            )

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


def test_dns_discovery_services_restart_instance(super_client, client):

    port = "417"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(super_client, service, [consumed_service], port)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart consumed instance
    service_instance = client.wait_success(service_instance.restart(), 120)
    assert service_instance.state == 'running'

    validate_linked_service(super_client, service, [consumed_service], port,
                            )

    delete_all(client, [env])


def test_dns_discovery_services_delete_instance(super_client, client):

    port = "418"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
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


def test_dns_discoverys_with_hostnetwork_1(super_client, client):

    port = "419"

    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"
    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port,
        ssh_port, isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=True)
    validate_linked_service(super_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discoverys_with_hostnetwork_2(super_client, client):

    port = "420"

    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port,
        ssh_port, isnetworkModeHost_svc=True,
        isnetworkModeHost_consumed_svc=True)
    validate_linked_service(
        super_client, service, [consumed_service], ssh_port)

    delete_all(client, [env])


def test_dns_discoverys_with_hostnetwork_3(super_client, client):

    port = "421"

    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"

    env, service, consumed_service = create_environment_with_services(
        super_client, client, service_scale, consumed_service_scale, port,
        ssh_port, isnetworkModeHost_svc=True,
        isnetworkModeHost_consumed_svc=False)
    validate_linked_service(
        super_client, service, [consumed_service], ssh_port)
    delete_all(client, [env])
