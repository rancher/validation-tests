from common_fixtures import *  # NOQA
from test_services_sidekick \
    import create_env_with_sidekick, validate_sidekick, validate_dns

logger = logging.getLogger(__name__)


def create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port,
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

    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)

    consumed_service = client.wait_success(
        consumed_service, SERVICE_WAIT_TIMEOUT)

    assert service.state == "active"
    assert consumed_service.state == "active"
    return env, service, consumed_service


def test_dns_discovery_activate_svc_activate_consumed_svc_link(
        admin_client, client):

    port = "401"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_dns_discovery_service_scale_up(admin_client, client):

    port = "402"

    service_scale = 1
    consumed_service_scale = 2

    final_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_services_scale_down(admin_client, client):

    port = "403"

    service_scale = 3
    consumed_service_scale = 2

    final_service_scale = 1

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_consumed_services_scale_up(admin_client, client):

    port = "404"

    service_scale = 1

    consumed_service_scale = 2
    final_consumed_service_scale = 4

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(
        consumed_service, SERVICE_WAIT_TIMEOUT)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_consumed_services_scale_down(admin_client, client):

    port = "405"

    service_scale = 2
    consumed_service_scale = 3

    final_consumed_service_scale = 1

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    consumed_service = client.update(consumed_service,
                                     scale=final_consumed_service_scale,
                                     name=consumed_service.name)
    consumed_service = client.wait_success(
        consumed_service, SERVICE_WAIT_TIMEOUT)
    assert consumed_service.state == "active"
    assert consumed_service.scale == final_consumed_service_scale

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_consumed_services_stop_start_instance(
        admin_client, client):

    port = "406"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    container_name = get_container_name(env, consumed_service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), SERVICE_WAIT_TIMEOUT)
    service = wait_state(client, service, "active")

    wait_for_scale_to_adjust(admin_client, consumed_service)

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_consumed_services_restart_instance(
        admin_client, client):

    port = "407"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    container_name = get_container_name(env, consumed_service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Restart instance
    container = client.wait_success(container.restart(), SERVICE_WAIT_TIMEOUT)
    assert container.state == 'running'
    time.sleep(10)
    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_consumed_services_delete_instance(admin_client, client):

    port = "408"

    service_scale = 1
    consumed_service_scale = 3

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    container_name = get_container_name(env, consumed_service, 1)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(admin_client, consumed_service)

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_consumed_services_deactivate_activate(
        admin_client, client):

    port = "409"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    consumed_service = consumed_service.deactivate()
    consumed_service = client.wait_success(
        consumed_service, SERVICE_WAIT_TIMEOUT)
    assert consumed_service.state == "inactive"
    wait_until_instances_get_stopped(admin_client, consumed_service)

    consumed_service = consumed_service.activate()
    consumed_service = client.wait_success(
        consumed_service, SERVICE_WAIT_TIMEOUT)
    assert consumed_service.state == "active"
    time.sleep(10)
    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_service_deactivate_activate(admin_client, client):

    port = "410"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    service = service.deactivate()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(admin_client, service)

    service = service.activate()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"
    time.sleep(restart_sleep_interval)

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_deactivate_activate_environment(admin_client, client):

    port = "411"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port,
                            )

    env = env.deactivateservices()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "inactive"

    consumed_service = client.wait_success(
        consumed_service, SERVICE_WAIT_TIMEOUT)
    assert consumed_service.state == "inactive"

    wait_until_instances_get_stopped(admin_client, consumed_service)

    env = env.activateservices()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"

    consumed_service = client.wait_success(
        consumed_service, SERVICE_WAIT_TIMEOUT)
    assert consumed_service.state == "active"
    time.sleep(restart_sleep_interval)

    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discovery_services_stop_start_instance(admin_client, client):

    port = "416"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port,
                            )

    container_name = get_container_name(env, consumed_service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Stop service instance
    service_instance = client.wait_success(
        service_instance.stop(), SERVICE_WAIT_TIMEOUT)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(admin_client, service)
    time.sleep(restart_sleep_interval)

    validate_linked_service(admin_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_dns_discovery_services_restart_instance(admin_client, client):

    port = "417"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    container_name = get_container_name(env, service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart consumed instance
    service_instance = client.wait_success(
        service_instance.restart(), SERVICE_WAIT_TIMEOUT)
    assert service_instance.state == 'running'
    time.sleep(restart_sleep_interval)
    validate_linked_service(admin_client, service, [consumed_service], port,
                            )

    delete_all(client, [env])


def test_dns_discovery_services_delete_instance(admin_client, client):

    port = "418"

    service_scale = 2
    consumed_service_scale = 2

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port)

    validate_linked_service(admin_client, service, [consumed_service], port)

    container_name = get_container_name(env, service, 2)
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(service_instance))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(admin_client, service)
    validate_linked_service(admin_client, service, [consumed_service], port)

    delete_all(client, [env])


def test_dns_discoverys_with_hostnetwork_1(admin_client, client):

    # Verify if able to resolve to containers of service in host network
    # from containers that belong to another service in managed network.
    port = "419"

    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"
    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port,
        ssh_port, isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=True)
    validate_linked_service(admin_client, service, [consumed_service], port)
    delete_all(client, [env])


def test_dns_discoverys_with_hostnetwork_2(admin_client, client):

    # Verify if able to resolve to container of service in host network
    # from containers that belong to another service in host network in the
    # same stack
    port = "420"

    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port,
        ssh_port, isnetworkModeHost_svc=True,
        isnetworkModeHost_consumed_svc=True)
    validate_linked_service(
        admin_client, service, [consumed_service], ssh_port,
        linkName=consumed_service.name + "." + env.name + ".rancher.internal")

    delete_all(client, [env])


def test_dns_discoverys_with_hostnetwork_3(admin_client, client):

    # Verify if able to resolve to containers of service in managed
    # network from containers that belong to another service in host network.

    port = "421"

    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"

    env, service, consumed_service = create_environment_with_services(
        admin_client, client, service_scale, consumed_service_scale, port,
        ssh_port, isnetworkModeHost_svc=True,
        isnetworkModeHost_consumed_svc=False)
    validate_linked_service(
        admin_client, service, [consumed_service], ssh_port,
        linkName=consumed_service.name + "." + env.name + ".rancher.internal")
    delete_all(client, [env])


def test_dns_discoverys_with_hostnetwork_externalService(admin_client, client):

    # Verify if able to resolve external services from containers
    # that belong to another service in host network.

    port = "422"
    env, service, ext_service, con_list = \
        create_env_with_ext_svc(client, 1, port)

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID_HOSTNET,
                         "networkMode": "host",
                         "labels": dns_labels}
    random_name = random_str()
    service_name = random_name.replace("-", "")
    host_service = client.create_service(name=service_name,
                                         stackId=env.id,
                                         launchConfig=launch_config_svc,
                                         scale=1)
    host_service = client.wait_success(host_service)
    host_service.activate()
    ext_service.activate()
    host_service = client.wait_success(host_service, SERVICE_WAIT_TIMEOUT)
    ext_service = client.wait_success(ext_service, SERVICE_WAIT_TIMEOUT)
    assert host_service.state == "active"
    assert ext_service.state == "active"

    validate_external_service(
        admin_client, host_service, [ext_service], 33, con_list,
        fqdn="." + env.name + ".rancher.internal")
    con_list.append(env)
    delete_all(client, con_list)


def test_dns_discoverys_with_hostnetwork_externalService_cname(
        admin_client, client):

    # Verify if able to resolve external services from containers
    # that belong to another service in host network.

    port = "423"
    env, service, ext_service, con_list = \
        create_env_with_ext_svc(client, 1, port, True)

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID_HOSTNET,
                         "networkMode": "host",
                         "labels": dns_labels}
    random_name = random_str()
    service_name = random_name.replace("-", "")
    host_service = client.create_service(name=service_name,
                                         stackId=env.id,
                                         launchConfig=launch_config_svc,
                                         scale=1)
    host_service = client.wait_success(host_service)
    host_service.activate()
    ext_service.activate()
    host_service = client.wait_success(host_service, SERVICE_WAIT_TIMEOUT)
    ext_service = client.wait_success(ext_service, SERVICE_WAIT_TIMEOUT)
    assert host_service.state == "active"
    assert ext_service.state == "active"

    validate_external_service_for_hostname(admin_client, host_service,
                                           [ext_service], 33)
    delete_all(client, [env])


def test_dns_discoverys_coss_stack_service(
        admin_client, client):

    env = create_env(client)
    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}
    service_name = "test1"
    service = client.create_service(name=service_name,
                                    stackId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=2)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    service.activate()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"

    port = "424"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID, }
    launch_config_svc["ports"] = [port+":"+"22/tcp"]
    env1 = create_env(client)
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env1.id,
                                     launchConfig=launch_config_svc,
                                     scale=2)
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    service1.activate()
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    assert service1.state == "active"

    validate_linked_service(admin_client, service1, [service],
                            port,
                            linkName=service.name+"."+env.name)

    linkName = service.name+"."+env.name+"."+RANCHER_FQDN
    validate_linked_service(admin_client, service1, [service],
                            port,
                            linkName=linkName)

    delete_all(client, [env, env1])


def test_dns_discoverys_coss_stack_service_uppercase(
        admin_client, client):

    env = create_env(client)
    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}
    service_name = "TEST"
    service = client.create_service(name=service_name,
                                    stackId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=2)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    service.activate()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"

    port = "425"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID, }
    launch_config_svc["ports"] = [port+":"+"22/tcp"]
    env1 = create_env(client)
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env1.id,
                                     launchConfig=launch_config_svc,
                                     scale=2)
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    service1.activate()
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    assert service1.state == "active"

    validate_linked_service(admin_client, service1, [service],
                            port,
                            linkName=service.name+"."+env.name)

    linkName = service.name+"."+env.name+"."+RANCHER_FQDN
    validate_linked_service(admin_client, service1, [service],
                            port,
                            linkName=linkName)

    delete_all(client, [env, env1])


def test_dns_discoverys_for_containers_by_name_and_fqdn(
        admin_client, client):

    env = create_env(client)
    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}
    service_name = "TEST"
    service = client.create_service(name=service_name,
                                    stackId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=2)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    service.activate()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"

    port = "426"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID, }
    launch_config_svc["ports"] = [port+":"+"22/tcp"]
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=2)
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    service1.activate()
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    assert service1.state == "active"

    containers = get_service_container_list(admin_client, service)
    assert len(containers) == service.scale

    for container in containers:
        validate_for_container_dns_resolution(
            admin_client, service1, port, container, container.name)

        validate_for_container_dns_resolution(
            admin_client, service1, port, container,
            container.name+"."+RANCHER_FQDN)

    delete_all(client, [env])


def test_dns_discoverys_for_containers_by_name_and_fqdn_cross_stack(
        admin_client, client):

    env = create_env(client)
    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}
    service_name = "TEST"
    service = client.create_service(name=service_name,
                                    stackId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=2)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    service.activate()
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    assert service.state == "active"

    # Deploy client service
    port = "427"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID, }
    launch_config_svc["ports"] = [port+":"+"22/tcp"]
    env1 = create_env(client)
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env1.id,
                                     launchConfig=launch_config_svc,
                                     scale=2)
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    service1.activate()
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    assert service1.state == "active"

    containers = get_service_container_list(admin_client, service)
    assert len(containers) == service.scale

    for container in containers:
        validate_for_container_dns_resolution(
            admin_client, service1, port, container, container.name)

        validate_for_container_dns_resolution(
            admin_client, service1, port, container,
            container.name+"."+RANCHER_FQDN)

    delete_all(client, [env, env1])


def test_dns_discovery_for_sidekick_containers_by_name_and_fqdn_cross_stack(
        admin_client, client):

    port = "428"
    service_scale = 2

    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick(client, service_scale, port)
    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, port)

    secondary_cons = get_service_containers_with_name(
        admin_client, service, consumed_service_name)
    assert len(secondary_cons) == service.scale

    # Deploy client service in another environment
    port = "429"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID, }
    launch_config_svc["ports"] = [port+":"+"22/tcp"]
    env1 = create_env(client)
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env1.id,
                                     launchConfig=launch_config_svc,
                                     scale=2)
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    service1.activate()
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    assert service1.state == "active"

    for container in secondary_cons:
        validate_for_container_dns_resolution(
            admin_client, service1, port, container, container.name)

        validate_for_container_dns_resolution(
            admin_client, service1, port, container,
            container.name+"."+RANCHER_FQDN)

    delete_all(client, [env, env1])


def test_dns_discovery_for_service_with_sidekick(admin_client, client):
    port = "430"
    service_scale = 2

    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick(client, service_scale, port)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"
    dnsname = service.secondaryLaunchConfigs[0].name

    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, port, dnsname)

    secondary_cons = get_service_containers_with_name(
        admin_client, service, consumed_service_name)

    # Deploy client service in same environment
    port = "431"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID, }
    launch_config_svc["ports"] = [port+":"+"22/tcp"]
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=2)
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    service1.activate()
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    assert service1.state == "active"
    client_containers = get_service_container_list(admin_client, service1)

    dnsname = service.secondaryLaunchConfigs[0].name + "." + service.name
    validate_dns(
        admin_client, client_containers, secondary_cons, port, dnsname)
    delete_all(client, [env])


def test_dns_discovery_for_service_with_sidekick_cross_stack(
        admin_client, client):
    port = "432"
    service_scale = 2

    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick(client, service_scale, port)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"
    dnsname = service.secondaryLaunchConfigs[0].name

    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, port, dnsname)

    secondary_cons = get_service_containers_with_name(
        admin_client, service, consumed_service_name)

    # Deploy client service in a different environment
    port = "433"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID, }
    launch_config_svc["ports"] = [port+":"+"22/tcp"]
    service_name = random_str()
    env1 = create_env(client)
    service1 = client.create_service(name=service_name,
                                     stackId=env1.id,
                                     launchConfig=launch_config_svc,
                                     scale=2)
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    service1.activate()
    service1 = client.wait_success(service1, SERVICE_WAIT_TIMEOUT)
    assert service1.state == "active"
    client_containers = get_service_container_list(admin_client, service1)

    dnsname = \
        service.secondaryLaunchConfigs[0].name + "." + service.name + \
        "." + env.name + "." + RANCHER_FQDN

    validate_dns(
        admin_client, client_containers, secondary_cons, port, dnsname)
    delete_all(client, [env, env1])


def validate_for_container_dns_resolution(
        admin_client, service, sshport, container, dns_name):

    time.sleep(sleep_interval)
    client_containers = get_service_container_list(admin_client, service)
    assert len(client_containers) == service.scale
    for con in client_containers:
        host = admin_client.by_id('host', con.hosts[0].id)

        # Validate port mapping
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host.ipAddresses()[0].address, username="root",
                    password="root", port=int(sshport))

        # Validate container name resolution
        cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + \
              dns_name + ":80/name.html;cat result.txt"
        logger.info(cmd)
        print cmd
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        assert len(response) == 1
        resp = response[0].strip("\n")
        logger.info(resp)
        print resp
        assert resp in (container.externalId[:12])

        # Validate DNS resolution using dig
        cmd = "dig " + dns_name + " +short"
        logger.info(cmd)
        print cmd
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        logger.info("Actual dig Response" + str(response))
        assert len(response) == 1
        resp = response[0].strip("\n")
        logger.info(resp)
        print resp
        assert resp == container.primaryIpAddress
    return
