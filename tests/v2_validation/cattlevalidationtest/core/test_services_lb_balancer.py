from common_fixtures import *  # NOQA
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def create_environment_with_balancer_services(client,
                                              service_scale, lb_scale, port,
                                              internal=False,
                                              lbcookie_policy=None,
                                              config=None):

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, internal,
        lbcookie_policy, config)

    service.activate()
    lb_service.activate()

    service = client.wait_success(service, 180)
    lb_service = client.wait_success(lb_service, 180)

    assert service.state == "active"
    assert lb_service.state == "active"
    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    return env, service, lb_service


def create_lb_services_with_sa_con_targets(client,
                                           lb_scale, port,
                                           con_health_check=False,
                                           con_port=None):
    env, cons, lb_service = create_env_with_containers_and_lb(
        client, lb_scale, port, con_health_check_enabled=con_health_check,
        con_port=con_port)
    lb_service.activate()
    lb_service = client.wait_success(lb_service, 180)
    assert lb_service.state == "active"
    validate_lb_with_sa_con_targets(client,
                                    cons, lb_service, port)
    return env, cons, lb_service


def validate_lb_with_sa_con_targets(client,
                                    cons, lb_service, port):
    wait_for_lb_service_to_become_active(client,
                                         cons, lb_service)
    con_names = []
    for con in cons:
        con_names.append(con.externalId[:12])
    validate_lb_service_con_names(client, lb_service, port,
                                  con_names)


def test_lbservice_and_targetservice_activate(
        client, socat_containers):

    port = "18900"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_activate_target_svc_activate(
        client, socat_containers):

    port = "18901"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    lb_service = activate_svc(client, lb_service)
    service = activate_svc(client, service)

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_target_svc_activate_lbservice_activate(
        client, socat_containers):

    port = "18902"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service = activate_svc(client, service)
    lb_service = activate_svc(client, lb_service)

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_activate_targetservice_activate_set_targets(
        client, socat_containers):

    port = "18903"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, includePortRule=False)

    # Activate LB
    lb_service = activate_svc(client, lb_service)
    # Activate Service
    service = activate_svc(client, service)
    # Set LB targets
    port_rules = []
    protocol = "http"
    target_port = "80"
    service_id = service.id
    port_rule = {"sourcePort": port, "protocol": protocol,
                 "serviceId": service_id, "targetPort": target_port}
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    lb_service = client.wait_success(lb_service, 120)

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def set_targets_targetservice_activate_lbservice_target(
        client, socat_containers):

    port = "18904"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, includePortRule=False)

    # Set LB targets
    port_rules = []
    protocol = "http"
    target_port = "80"
    service_id = service.id
    port_rule = {"sourcePort": port, "protocol": protocol,
                 "serviceId": service_id, "targetPort": target_port}
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    lb_service = client.wait_success(lb_service, 120)

    # Activate service and LB service
    service = activate_svc(client, service)
    lb_service = activate_svc(client, lb_service)

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def set_targets_when_target_service_is_still_activating(
        client, socat_containers):

    port = "18905"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, includePortRule=False)

    service.activate()

    # Set LB targets
    port_rules = []
    protocol = "http"
    target_port = "80"
    service_id = service.id
    port_rule = {"sourcePort": port, "protocol": protocol,
                 "serviceId": service_id, "targetPort": target_port}
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    lb_service = client.wait_success(lb_service, 120)

    lb_service.activate()
    service = client.wait_success(service, 120)
    lb_service = client.wait_success(lb_service, 120)

    assert service.state == "active"
    assert lb_service.state == "active"
    validate_add_service_link(client, lb_service, service)

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_activate_env(
        client, socat_containers):

    port = "18925"

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

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_add_service_link(client, lb_service, service)

    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_up_service(
        client, socat_containers):

    port = "19001"

    service_scale = 2
    lb_scale = 1
    final_service_scale = 3

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_down_service(
        client, socat_containers):

    port = "19002"

    service_scale = 3
    lb_scale = 1

    final_service_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_up_lb_service(
        client, socat_containers):

    port = "19003"

    service_scale = 2
    lb_scale = 1

    final_lb_scale = 2

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_scale_down_lb_service(
        client, socat_containers):

    port = "19004"

    service_scale = 2
    lb_scale = 2

    final_lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_stop_start_instance(
        client, socat_containers):

    port = "19005"

    service_scale = 3
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    # Stop instance
    container_name = \
        env.name + FIELD_SEPARATOR + service.name + FIELD_SEPARATOR + "2"
    containers = client.list_container(name=container_name).data
    assert len(containers) == 1
    container = containers[0]
    stop_container_from_host(client, container)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(client, service)
    time.sleep(30)
    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_delete_purge_instance(
        client, socat_containers):

    port = "19006"

    service_scale = 3
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    # Delete instance
    container_name = \
        env.name + FIELD_SEPARATOR + service.name + FIELD_SEPARATOR + "1"
    containers = client.list_container(name=container_name).data
    assert len(containers) == 1
    container = containers[0]
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_for_scale_to_adjust(client, service)
    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_restart_instance(
        client, socat_containers):

    port = "19029"

    service_scale = 3
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    # restart instance
    container_name = \
        env.name + FIELD_SEPARATOR + service.name + FIELD_SEPARATOR + "1"
    containers = client.list_container(name=container_name).data
    assert len(containers) == 1
    container = containers[0]
    container = client.wait_success(container.restart(), 120)
    wait_for_condition(client, container,
                       lambda x: x.state == 'running',
                       lambda x: 'State is: ' + x.state)
    wait_for_condition(client, container,
                       lambda x: x.startCount == 2,
                       lambda x: 'State is: ' + x.state)
    time.sleep(30)
    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_deactivate_activate_lbservice(
        client, socat_containers):

    port = "19008"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    lb_service = lb_service.deactivate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "inactive"
    wait_until_instances_get_stopped(client, lb_service)

    lb_service = lb_service.activate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    time.sleep(30)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_deactivate_activate_service(
        client, socat_containers):

    port = "19009"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_deactivate_activate_environment(
        client, socat_containers):

    port = "19010"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "inactive"

    wait_until_instances_get_stopped(client, lb_service)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lb_services_add_remove_servicelinks_service(
        client, socat_containers):
    port = "19011"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    # Add another service to environment
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config,
                                     scale=2)
    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    service1 = service1.activate()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    # Add another target to the LB service
    port_rules = lb_service.lbConfig.portRules
    port_rule = {"serviceId": service1.id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    lb_config = {"portRules": port_rules}

    print("port rules:" + str(port_rules))
    lb_service = client.update(lb_service, lbConfig=lb_config)
    lb_service = client.wait_success(lb_service, 120)

    wait_for_lb_service_to_become_active(client,
                                         [service, service1], lb_service)
    validate_lb_service(client, lb_service, port,
                        [service, service1])

    # Remove one of the existing targets from LB service

    port_rules = []
    port_rule = {"serviceId": service1.id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    lb_config = {"portRules": port_rules}
    lb_service = client.update(lb_service, lbConfig=lb_config)
    lb_service = client.wait_success(lb_service, 120)

    wait_for_lb_service_to_become_active(client,
                                         [service1], lb_service)

    validate_lb_service(
        client,  lb_service, port, [service1])
    delete_all(client, [env])


def test_lb_services_add_remove_servicelinks_lb(
        client, socat_containers):
    port = "19011"
    port2 = "19111"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    # Add another LB service to environment
    port_rules = []
    port_rule = {"serviceId": service.id,
                 "sourcePort": port2,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    launch_config_lb = {"ports": [port2],
                        "imageUuid": get_haproxy_image()}
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_Config = {"portRules": port_rules}
    lb2_service = client.create_loadBalancerService(
        name=service_name, stackId=env.id,
        launchConfig=launch_config_lb,
        scale=1, lbConfig=lb_Config)

    lb2_service = client.wait_success(lb2_service)
    assert lb2_service.state == "inactive"

    lb2_service = lb2_service.activate()
    lb2_service = client.wait_success(lb2_service, 120)
    assert lb2_service.state == "active"

    wait_for_lb_service_to_become_active(client,
                                         [service], lb2_service)
    validate_lb_service(client,
                        lb2_service, port2, [service])

    # Remove existing target from first LB service
    lb_config = {"portRules": []}
    lb_service = client.update(lb_service, lbConfig=lb_config)
    lb_service = client.wait_success(lb_service, 120)

    # Make sure the new LB service continues to redirect traffic to the targets
    wait_for_lb_service_to_become_active(client,
                                         [service], lb2_service)
    validate_lb_service(client,
                        lb2_service, port2, [service])
    delete_all(client, [env])


def test_lb_services_delete_service_add_service(
        client, socat_containers):

    port = "19012"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"

    # Add another service to environment and link to LB
    launch_config = {"imageUuid": WEB_IMAGE_UUID}

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

    # Add this target to LB service
    port_rules = []
    port_rule = {"serviceId": service1.id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    lb_config = {"portRules": port_rules}
    lb_service = client.update(lb_service, lbConfig=lb_config)
    lb_service = client.wait_success(lb_service, 120)
    wait_for_lb_service_to_become_active(client,
                                         [service1], lb_service)
    validate_lb_service(
        client,  lb_service, port, [service1])

    delete_all(client, [env])


def test_lb_services_delete_lb_service(
        client, socat_containers):

    port = "19013"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)
    validate_lb_service(client, lb_service, port, [service])

    # Delete LB Service

    lb_service = client.wait_success(client.delete(lb_service))
    assert lb_service.state == "removed"

    # Make sure you are able to add another LB service using the same port

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_stop_start_lb_instance(
        client, socat_containers):

    port = "19014"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    lb_instances = get_service_container_list(client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # Stop lb instance
    stop_container_from_host(client, lb_instance)
    lb_service = client.wait_success(lb_service)

    wait_for_scale_to_adjust(client, lb_service)

    time.sleep(30)
    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_lb_instance_restart(
        client, socat_containers):

    port = "19015"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)
    validate_lb_service(client, lb_service, port, [service])

    lb_instances = get_service_container_list(client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # Restart lb instance
    lb_instance = client.wait_success(lb_instance.restart(), 120)
    assert lb_instance.state == 'running'

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])

    delete_all(client, [env])


def test_lb_services_lb_instance_delete(
        client, socat_containers):

    port = "19016"

    service_scale = 2
    lb_scale = 2

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port)

    validate_lb_service(client, lb_service, port, [service])

    lb_instances = get_service_container_list(client, lb_service)
    assert len(lb_instances) == lb_scale
    lb_instance = lb_instances[0]

    # delete lb instance
    lb_instance = client.wait_success(client.delete(lb_instance))
    assert lb_instance.state == 'removed'

    wait_for_scale_to_adjust(client, lb_service)

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])

    delete_all(client, [env])


def test_lbservice_internal(client, socat_containers):

    port = "19017"
    con_port = "9018"

    hosts = client.list_host(kind='docker', removed_null=True, state="active").data
    assert len(hosts) > 0

    lb_scale = 1
    service_scale = 2
    host = hosts[0]

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port, internal=True)

    # Deploy container in same network to test accessibility of internal LB
    hosts = client.list_host(kind='docker', removed_null=True, state="active").data
    assert len(hosts) > 0
    host = hosts[0]

    client_con = client.create_container(
        name=random_str(), imageUuid=SSH_IMAGE_UUID,
        ports=[con_port+":22/tcp"], requestedHostId=host.id)
    client_con = client.wait_success(client_con, 120)
    assert client_con.state == "running"

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    # Wait for exposed port to be available
    time.sleep(sleep_interval)
    validate_internal_lb(client, lb_service, [service], host,
                         con_port, port)

    # Check that port in the host where LB Agent is running is not accessible
    lb_containers = get_service_container_list(client, lb_service)
    assert len(lb_containers) == lb_service.scale
    for lb_con in lb_containers:
        host = client.by_id('host', lb_con.hosts[0].id)
        assert check_for_no_access(host, port)
    delete_all(client, [env, client_con])


def test_multiple_lbservice_internal_same_host_port(
        client, socat_containers):

    port = "19019"
    con_port = "19020"

    hosts = client.list_host(kind='docker', removed_null=True, state="active").data
    assert len(hosts) > 0

    lb_scale = len(hosts)
    service_scale = 2
    host = hosts[0]

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port, internal=True)

    # Deploy container in same network to test accessibility of internal LB
    hosts = client.list_host(kind='docker', removed_null=True, state="active").data
    assert len(hosts) > 0
    host = hosts[0]

    client_con = client.create_container(
        name=random_str(), imageUuid=SSH_IMAGE_UUID,
        ports=[con_port+":22/tcp"], requestedHostId=host.id)
    client_con = client.wait_success(client_con, 120)
    assert client_con.state == "running"
    # Wait for exposed port to be available
    time.sleep(sleep_interval)
    validate_internal_lb(client, lb_service, [service],
                         host, con_port, port)

    env2, service2, lb_service2 = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port, internal=True)
    validate_internal_lb(client, lb_service2, [service2], host,
                         con_port, port)

    delete_all(client, [env, env2, client_con])


def test_lbservice_custom_haproxy_1(
        client, socat_containers):

    port = "1921"
    lb_scale = 1
    service_scale = 2

    haproxy_cfg = "defaults\nbalance first\nglobal\ngroup haproxy\n"

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port,
        config=haproxy_cfg)
    check_for_balancer_first(client, lb_service, port, [service])
    delete_all(client, [env])


def test_lbservice_custom_haproxy_2(
        client, socat_containers):

    port = "1922"
    lb_scale = 1
    service_scale = 2

    default_cfg = "defaults\ntimeout client 30000\n"
    global_cfg = "global\nmaxconn 5096\n"
    frontend_cfg = "frontend " + port + " \ntimeout connect 3000"
    haproxy_cfg = default_cfg + global_cfg + frontend_cfg
    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port,
        config=haproxy_cfg)
    delete_all(client, [env])


def test_lbservice_custom_haproxy_3(
        client, socat_containers):
    port = "1923"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http",
                 "backendName": "myrule1"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    config = "backend myrule1\nbalance first\n"

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count,
        port_rules, config)

    wait_for_lb_service_to_become_active(client,
                                         services, lb_service)

    validate_lb_service(client,
                        lb_service, port, [services[1]],
                        "www.abc2.com", "/service2.html")

    check_for_balancer_first(client, lb_service, port,
                             [services[0]], {"host": "www.abc1.com"},
                             "service1.html")
    delete_all(client, [env])


def test_lbservice_lbcookie(
        client, socat_containers):

    port = "19023"
    lb_scale = 1
    service_scale = 2
    lbcookie_policy = {"mode": "insert",
                       "cookie": "cookie-1",
                       "indirect": True,
                       "nocache": True,
                       "postonly": False
                       }

    env, service, lb_service = create_environment_with_balancer_services(
        client, service_scale, lb_scale, port, False,
        lbcookie_policy)
    check_for_lbcookie_policy(client,
                              lb_service, port, [service])
    delete_all(client, [env])


def test_lb_tcp(
        client, socat_containers):

    port = "20000"

    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, lb_protocol="tcp")

    lb_service = activate_svc(client, lb_service)
    service = activate_svc(client, service)

    wait_for_lb_service_to_become_active(client,
                                         [service], lb_service)
    validate_lb_service(client, lb_service, port, [service])
    delete_all(client, [env])


@if_container_refactoring
def test_lb_with_container(client, socat_containers):
    lb_scale = 1
    port = "20001"
    env, cons, lb_service = create_lb_services_with_sa_con_targets(
        client, lb_scale, port)
    delete_all(client, [env])
    delete_all(client, cons)


@if_container_refactoring
def test_lb_with_container_scale_up(client, socat_containers):
    lb_scale = 1
    final_lb_scale = 2
    port = "20002"
    env, cons, lb_service = create_lb_services_with_sa_con_targets(
        client, lb_scale, port)
    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale
    validate_lb_with_sa_con_targets(client,
                                    cons, lb_service, port)
    delete_all(client, [env])
    delete_all(client, cons)


@if_container_refactoring
def test_lb_with_container_stop_container(
        client, socat_containers):
    lb_scale = 1
    port = "20003"
    env, cons, lb_service = create_lb_services_with_sa_con_targets(
        client, lb_scale, port)
    # Stop container from host
    con1 = cons[0]
    stop_container_from_host(client, con1)
    con1 = wait_for_condition(
        client, con1,
        lambda x: x.state == "stopped",
        lambda x: 'State is: ' + x.state,
        timeout=60)
    validate_lb_with_sa_con_targets(client,
                                    [cons[1]], lb_service, port)
    con1 = client.wait_success(con1.start(), 120)
    assert con1.state == "running"
    validate_lb_with_sa_con_targets(client,
                                    cons, lb_service, port)
    delete_all(client, [env])
    delete_all(client, cons)


@if_container_refactoring
def test_lb_with_container_restart_container(
        client, socat_containers):
    lb_scale = 1
    port = "20004"
    env, cons, lb_service = create_lb_services_with_sa_con_targets(
        client, lb_scale, port)
    # Restart container
    con1 = cons[0]
    con1 = client.wait_success(con1.restart(), 120)
    assert con1.state == "running"
    validate_lb_with_sa_con_targets(client,
                                    cons, lb_service, port)
    delete_all(client, [env])
    delete_all(client, cons)


@if_container_refactoring
def test_lb_with_container_delete_container(
        client, socat_containers):
    lb_scale = 1
    port = "20005"
    env, cons, lb_service = create_lb_services_with_sa_con_targets(
        client, lb_scale, port)
    # Delete container from host
    con1 = cons[0]
    con1 = client.delete(con1)
    con1 = wait_for_condition(
        client, con1,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state,
        timeout=60)
    validate_lb_with_sa_con_targets(client,
                                    [cons[1]], lb_service, port)
    delete_all(client, [env])
    delete_all(client, cons)


@if_container_refactoring
def test_lb_with_container_deactivate_and_activate_lb_service(
        client, socat_containers):
    lb_scale = 1
    port = "20006"

    env, cons, lb_service = create_lb_services_with_sa_con_targets(
        client, lb_scale, port)
    lb_service = lb_service.deactivate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "inactive"
    wait_until_instances_get_stopped(client, lb_service)

    lb_service = lb_service.activate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    validate_lb_with_sa_con_targets(client,
                                    cons, lb_service, port)
    delete_all(client, [env])
    delete_all(client, cons)


@if_container_refactoring
def test_lb_with_container_unhealthy_container(
        client, socat_containers):
    lb_scale = 1
    port = "20007"
    con_port = "2008"
    env, cons, lb_service = create_lb_services_with_sa_con_targets(
        client, lb_scale, port,
        con_health_check=True, con_port=con_port)

    # Delete requestUrl from one of the containers to trigger health check
    # failure and service reconcile
    con = cons[0]
    mark_container_unhealthy(client, con, int(con_port))

    wait_for_condition(
        client, con,
        lambda x: x.healthState == 'unhealthy',
        lambda x: 'State is: ' + x.healthState)
    con = client.reload(con)
    assert con.healthState == "unhealthy"

    wait_for_condition(
        client, con,
        lambda x: x.state in ('removed', 'purged'),
        lambda x: 'State is: ' + x.healthState)
    new_containers = client.list_container(name=con.name,
                                           state="running",
                                           healthState="healthy").data
    assert len(new_containers) == 1
    validate_lb_with_sa_con_targets(client,
                                    [cons[1], new_containers[0]],
                                    lb_service, port)
    delete_all(client, [env])
    delete_all(client, cons)
