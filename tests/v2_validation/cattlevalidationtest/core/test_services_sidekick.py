from common_fixtures import *  # NOQA

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"

logger = logging.getLogger(__name__)


def env_with_sidekick_config(client, service_scale,
                             launch_config_consumed_service,
                             launch_config_service, env=None):

    if env is None:
        # Create Environment
        random_name = random_str()
        env_name = random_name.replace("-", "")
        env = client.create_stack(name=env_name)
        env = client.wait_success(env)
        assert env.state == "active"

    # Create service

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")

    launch_config_consumed_service["name"] = consumed_service_name
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, stackId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service])

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name = \
        get_sidekick_service_name(env, service, consumed_service_name)
    service_name = get_service_name(env, service)
    return env, service, service_name, consumed_service_name


def create_env_with_sidekick(client, service_scale, expose_port, env=None):
    launch_config_consumed_service = {
        "imageUuid": WEB_IMAGE_UUID}

    # Adding service anti-affinity rule to workaround bug-1419
    launch_config_service = {
        "imageUuid": SSH_IMAGE_UUID,
        "ports": [expose_port+":22/tcp"],
        "labels": {
            'io.rancher.scheduler.affinity:container_label_ne':
                "io.rancher.stack_service.name" +
                "=${stack_name}/${service_name}"
        }
    }
    env, service, service_name, consumed_service_name = \
        env_with_sidekick_config(client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service, env)

    return env, service, service_name, consumed_service_name


def create_env_with_sidekick_for_linking(client, service_scale, env=None):
    launch_config_consumed_service = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": WEB_IMAGE_UUID}

    env, service, service_name, consumed_service_name = \
        env_with_sidekick_config(client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service, env)

    return env, service, service_name, consumed_service_name


def create_env_with_sidekick_anti_affinity(client, service_scale):
    launch_config_consumed_service = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": SSH_IMAGE_UUID,
        "labels": {
            'io.rancher.scheduler.affinity:container_label_ne':
                "io.rancher.stack_service.name" +
                "=${stack_name}/${service_name}"
        }
    }

    env, service, service_name, consumed_service_name = \
        env_with_sidekick_config(client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service)

    return env, service, service_name, consumed_service_name


def create_env_with_exposed_port_on_secondary(client, service_scale,
                                              expose_port):
    launch_config_consumed_service = {
        "imageUuid": WEB_IMAGE_UUID,
        "ports": [expose_port+":80/tcp"]}

    launch_config_service = {
        "imageUuid": WEB_IMAGE_UUID}

    env, service, service_name, consumed_service_name = \
        env_with_sidekick_config(client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service)

    return env, service, service_name, consumed_service_name


def create_env_with_exposed_ports_on_primary_and_secondary(
        client, service_scale, expose_port_pri, expose_port_sec):
    launch_config_consumed_service = {
        "imageUuid": SSH_IMAGE_UUID,
        "ports": [expose_port_pri+":22/tcp"]}

    launch_config_service = {
        "imageUuid": WEB_IMAGE_UUID,
        "ports": [expose_port_sec+":22/tcp"]}

    env, service, service_name, consumed_service_name = \
        env_with_sidekick_config(client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service)

    return env, service, service_name, consumed_service_name


def create_env_with_multiple_sidekicks(client, service_scale, expose_port):

    launch_config_consumed_service1 = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_consumed_service2 = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": SSH_IMAGE_UUID,
        "ports": [expose_port+":22/tcp"],
        "labels": {
            'io.rancher.scheduler.affinity:container_label_ne':
                "io.rancher.stack_service.name" +
                "=${stack_name}/${service_name}"
        }}

    random_name = random_str()
    consumed_service_name1 = random_name.replace("-", "")

    random_name = random_str()
    consumed_service_name2 = random_name.replace("-", "")

    launch_config_consumed_service1["name"] = consumed_service_name1
    launch_config_consumed_service2["name"] = consumed_service_name2

    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_stack(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, stackId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service1,
                                launch_config_consumed_service2]
    )

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name1 = \
        get_sidekick_service_name(env, service, consumed_service_name1)
    consumed_service_name2 = \
        get_sidekick_service_name(env, service, consumed_service_name2)
    service_name = get_service_name(env, service)
    return env, service, service_name, \
        consumed_service_name1, consumed_service_name2


def env_with_sidekick(admin_client, client, service_scale, exposed_port):

    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick(client, service_scale, exposed_port)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"

    dnsname = service.secondaryLaunchConfigs[0].name

    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    return env, service, service_name, consumed_service_name


def test_sidekick_activate_env(client, admin_client):

    exposed_port = "7000"
    service_scale = 2

    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick(client, service_scale, exposed_port)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"

    dnsname = service.secondaryLaunchConfigs[0].name

    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    delete_all(client, [env])


def test_multiple_sidekick_activate_service(client, admin_client):

    exposed_port = "7003"
    service_scale = 2

    env, service, service_name, consumed_service1, consumed_service2 =\
        create_env_with_multiple_sidekicks(
            client, service_scale, exposed_port)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service1, exposed_port, dnsname)

    dnsname = service.secondaryLaunchConfigs[1].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service2, exposed_port, dnsname)

    delete_all(client, [env])


def test_sidekick_for_lb(client, admin_client, socat_containers):
    service_scale = 2
    port = "7080"
    env, service1, service1_name, consumed_service_name = \
        create_env_with_sidekick_for_linking(client, service_scale)
    env = env.activateservices()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    validate_sidekick(admin_client, service1, service1_name,
                      consumed_service_name)

    env, service2, service2_name, consumed_service_name = \
        create_env_with_sidekick_for_linking(client, service_scale, env)
    service2 = client.wait_success(service2.activate(), 120)
    assert service2.state == "active"

    validate_sidekick(admin_client, service2, service2_name,
                      consumed_service_name)

    # Add LB services

    launch_config_lb = {"ports": [port+":80"]}
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name, stackId=env.id, launchConfig=launch_config_lb,
        scale=1)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    lb_service.setservicelinks(
        serviceLinks=[{"serviceId": service1.id, "ports": []},
                      {"serviceId": service2.id, "ports": []}])

    lb_service = lb_service.activate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_add_service_link(admin_client, lb_service, service1)

    validate_add_service_link(admin_client, lb_service, service2)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         [service1, service2], lb_service)

    target_count = service1.scale + service2.scale
    container_name1 = get_service_containers_with_name(admin_client,
                                                       service1,
                                                       service1_name)
    container_name2 = get_service_containers_with_name(admin_client,
                                                       service2,
                                                       service2_name)
    containers = container_name1 + container_name2
    container_names = []
    for c in containers:
        if c.state == "running":
            container_names.append(c.externalId[:12])
    assert len(container_names) == target_count

    validate_lb_service_con_names(admin_client, client, lb_service, port,
                                  container_names)

    delete_all(client, [env])


def test_sidekick(client, admin_client):
    service_scale = 2
    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick_for_linking(client, service_scale)
    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name)

    delete_all(client, [env])


def test_sidekick_with_anti_affinity(client, admin_client):
    service_scale = 2
    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick_anti_affinity(client, service_scale)
    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name)
    delete_all(client, [env])


def test_service_links_to_sidekick(client, admin_client):

    service_scale = 2
    env, linked_service, linked_service_name, linked_consumed_service_name = \
        create_env_with_sidekick_for_linking(client, service_scale)

    client_port = "7004"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [client_port+":22/tcp"]}

    service = create_svc(client, env, launch_config, 1)
    link_svc(admin_client, service, [linked_service])

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    service_containers = get_service_container_list(admin_client, service)

    primary_consumed_service = get_service_containers_with_name(
        admin_client, linked_service, linked_service_name)

    secondary_consumed_service = get_service_containers_with_name(
        admin_client, linked_service, linked_consumed_service_name)

    dnsname = linked_service.name
    validate_dns(admin_client, service_containers, primary_consumed_service,
                 client_port, dnsname)

    dnsname = \
        linked_service.secondaryLaunchConfigs[0].name + "." + \
        linked_service.name
    validate_dns(admin_client, service_containers, secondary_consumed_service,
                 client_port, dnsname)

    delete_all(client, [env])


def test_sidekick_service_scale_up(client, admin_client):

    service_scale = 2
    exposed_port = "7005"
    final_service_scale = 3

    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)
    delete_all(client, [env])


def test_sidekick_scale_down(client, admin_client):
    service_scale = 3
    exposed_port = "7006"
    final_service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)
    delete_all(client, [env])


def test_sidekick_consumed_services_stop_start_instance(client,  admin_client):

    service_scale = 2
    exposed_port = "7007"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    container_name = consumed_service_name + FIELD_SEPARATOR + "2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 120)
    wait_state(client, service, "active")

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    delete_all(client, [env])


def test_sidekick_consumed_services_restart_instance(client,  admin_client):
    service_scale = 2
    exposed_port = "7008"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    container_name = consumed_service_name + FIELD_SEPARATOR + "2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    delete_all(client, [env])


def test_sidekick_consumed_services_delete_instance(client,  admin_client):

    service_scale = 3
    exposed_port = "7009"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    container_name = consumed_service_name + FIELD_SEPARATOR + "1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    print container_name
    primary_container = get_side_kick_container(
        admin_client, container, service, service_name)
    print primary_container.name

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_state(client, service, "active")

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    # Check that the consumed container is not recreated
    primary_container = client.reload(primary_container)
    print primary_container.state
    assert primary_container.state == "running"

    delete_all(client, [env])


def test_sidekick_deactivate_activate_environment(client, admin_client):

    service_scale = 2
    exposed_port = "7010"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    wait_until_instances_get_stopped_for_service_with_sec_launch_configs(
        admin_client, service)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    delete_all(client, [env])


def test_sidekick_services_stop_start_instance(client,  admin_client):

    service_scale = 2
    exposed_port = "7011"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    container_name = get_container_name(env, service, "2")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 120)
    wait_state(client, service, "active")

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    delete_all(client, [env])


def test_sidekick_services_restart_instance(client, admin_client):
    service_scale = 3
    exposed_port = "7012"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    container_name = get_container_name(env, service, "2")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)
    delete_all(client, [env])


def test_sidekick_services_delete_instance(client,  admin_client):

    service_scale = 2
    exposed_port = "7013"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    container_name = get_container_name(env, service, "1")
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    print container_name
    consumed_container = get_side_kick_container(
        admin_client, container, service, consumed_service_name)
    print consumed_container.name

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    wait_state(client, service, "active")

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    # Check that the consumed container is not recreated
    consumed_container = client.reload(consumed_container)
    print consumed_container.state
    assert consumed_container.state == "running"

    delete_all(client, [env])


def test_sidekick_services_deactivate_activate(client,  admin_client):

    service_scale = 2
    exposed_port = "7014"
    env, service, service_name, consumed_service_name = \
        env_with_sidekick(admin_client, client, service_scale, exposed_port)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    wait_until_instances_get_stopped_for_service_with_sec_launch_configs(
        admin_client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    dnsname = service.secondaryLaunchConfigs[0].name
    validate_sidekick(admin_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    delete_all(client, [env])


def test_sidekick_lbactivation_after_linking(client,
                                             admin_client, socat_containers):
    service_scale = 2
    port = "7091"
    env, service1, service1_name, consumed_service_name = \
        create_env_with_sidekick_for_linking(client, service_scale)
    env = env.activateservices()
    service1 = client.wait_success(service1, 120)
    assert service1.state == "active"

    validate_sidekick(admin_client, service1, service1_name,
                      consumed_service_name)

    # Add LB service

    launch_config_lb = {"ports": [port + ":80"]}
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name, stackId=env.id, launchConfig=launch_config_lb,
        scale=1)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    lb_service.setservicelinks(
        serviceLinks=[{"serviceId": service1.id, "ports": []}])

    validate_add_service_link(admin_client, lb_service, service1)

    # Activate LB service

    lb_service = lb_service.activate()
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(admin_client, client,
                                         [service1], lb_service)

    target_count = service1.scale
    container_name1 = get_service_containers_with_name(admin_client,
                                                       service1,
                                                       service1_name)
    containers = container_name1
    container_names = []
    for c in containers:
        if c.state == "running":
            container_names.append(c.externalId[:12])
    assert len(container_names) == target_count

    validate_lb_service_con_names(admin_client, client, lb_service, port,
                                  container_names)
    delete_all(client, [env])


def validate_sidekick(admin_client, primary_service, service_name,
                      consumed_service_name, exposed_port=None, dnsname=None):
    print "Validating service - " + service_name
    containers = get_service_containers_with_name(admin_client,
                                                  primary_service,
                                                  service_name)
    assert len(containers) == primary_service.scale

    print "Validating Consumed Services: " + consumed_service_name
    consumed_containers = get_service_containers_with_name(
        admin_client, primary_service, consumed_service_name)
    assert len(consumed_containers) == primary_service.scale

    # For every container in the service , make sure that there is 1
    # associated container from each of the consumed service with the same
    # label and make sure that this container is the same host as the
    # primary service container
    for con in containers:
        pri_host = con.hosts[0].id
        label = con.labels["io.rancher.service.deployment.unit"]
        print con.name + " - " + label + " - " + pri_host
        secondary_con = get_service_container_with_label(
            admin_client, primary_service, consumed_service_name, label)
        sec_host = secondary_con.hosts[0].id
        print secondary_con.name + " - " + label + " - " + sec_host
        assert sec_host == pri_host

    if exposed_port is not None and dnsname is not None:
        # Check for DNS resolution
        secondary_con = get_service_containers_with_name(
            admin_client, primary_service, consumed_service_name)
        validate_dns(admin_client, containers, secondary_con, exposed_port,
                     dnsname)


def validate_dns(admin_client, service_containers, consumed_service,
                 exposed_port, dnsname):
    time.sleep(5)

    for service_con in service_containers:
        host = admin_client.by_id('host', service_con.hosts[0].id)

        expected_dns_list = []
        expected_link_response = []
        dns_response = []
        print "Validating DNS for " + dnsname + " - container -" \
              + service_con.name

        for con in consumed_service:
            expected_dns_list.append(con.primaryIpAddress)
            expected_link_response.append(con.externalId[:12])

        print "Expected dig response List" + str(expected_dns_list)
        print "Expected wget response List" + str(expected_link_response)

        # Validate port mapping
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host.ipAddresses()[0].address, username="root",
                    password="root", port=int(exposed_port))

        # Validate link containers
        cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + dnsname + \
              ":80/name.html;cat result.txt"
        print cmd
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        assert len(response) == 1
        resp = response[0].strip("\n")
        print "Actual wget Response" + str(resp)
        assert resp in (expected_link_response)

        # Validate DNS resolution using dig
        cmd = "dig " + dnsname + " +short"
        print cmd
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        print "Actual dig Response" + str(response)
        assert len(response) == len(expected_dns_list)

        for resp in response:
            dns_response.append(resp.strip("\n"))

        for address in expected_dns_list:
            assert address in dns_response
