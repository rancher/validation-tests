from common_fixtures import *  # NOQA
from test_services \
    import service_with_healthcheck_enabled
from test_machine \
    import action_on_digital_ocean_machine, get_dropletid_for_ha_hosts
ha_droplets = []

if_test_host_down = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY') or
    not os.environ.get('TEST_HOST_DOWN'),
    not os.environ.get('HOST_DISCONN_ACTIVE_TIMEOUT'),
    not os.environ.get('HOST_ACTIVE_DISCONN_TIMEOUT'),
    reason='HOST DOWN PARAMETERS not set')


HOST_DISCONN_ACTIVE_TIMEOUT = os.environ.get('HOST_DISCONN_ACTIVE_TIMEOUT',
                                             900)
HOST_ACTIVE_DISCONN_TIMEOUT = os.environ.get('HOST_ACTIVE_DISCONN_TIMEOUT',
                                             900)


@pytest.fixture(scope='session', autouse=True)
def get_host_droplets(ha_hosts, socat_containers):
    ha_droplets.append(get_dropletid_for_ha_hosts())


@pytest.fixture
def check_host_state_power_on(client):

    print("Power on hosts that are in disconnected or reconnecting state")
    print(ha_droplets)
    inactive_hosts = client.list_host(
        kind='docker', removed_null=True, agentState="disconnected").data

    print("Disconnected hosts:")
    print(inactive_hosts)
    reconn_hosts = client.list_host(
        kind='docker', removed_null=True, agentState="reconnecting").data

    print("Reconnecting hosts:")
    print(reconn_hosts)

    inactive_hosts_dropletids = []
    inactive_hosts_list = []
    # Get droplet Id and hosts from disconnected hosts
    for host in inactive_hosts:
        host_name = host.hostname
        print(host_name)
        droplet_id = ha_droplets[0][host_name]
        inactive_hosts_dropletids.append(droplet_id)
        inactive_hosts_list.append(host)

    # Get droplet Id and hosts from reconnecting hosts
    # and append to the inactive host/droplet lists
    for host in reconn_hosts:
        host_name = host.hostname
        print(host_name)
        droplet_id = ha_droplets[0][host_name]
        inactive_hosts_dropletids.append(droplet_id)
        inactive_hosts_list.append(host)

    print("List of all disconnected/reconnecting hosts")
    print(inactive_hosts_list)
    print(inactive_hosts_dropletids)

    # Power on the droplets
    for dropletid in inactive_hosts_dropletids:
        print("Power on droplet " + str(droplet_id))
        action_on_digital_ocean_machine(dropletid, "power_on")

    # Wait for the host agent state to become active
    for host in inactive_hosts_list:
        print("In host wait method")
        wait_for_host_agent_state(client, host, "active", 600)


@if_test_host_down
def test_service_with_healthcheck_1_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    host_down_with_healthcheck_services(
        client, host_down_count=1)


@if_test_host_down
def test_service_with_healthcheck_2_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    host_down_with_healthcheck_services(
        client, host_down_count=2)


@if_test_host_down
def test_service_with_healthcheck_3_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    host_down_with_healthcheck_services(
        client, host_down_count=3)


@if_test_host_down
def test_service_with_healthcheck_and_retainIp_2_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    host_down_with_healthcheck_services(
        client, host_down_count=2, retainIp=True)


@if_test_host_down
def test_lbservice_with_healthcheck_1_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    lb_port = "7770"
    host_down_with_lb_services(
        client, lb_port, host_down_count=1)


@if_test_host_down
def test_lbservice_with_healthcheck_2_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    lb_port = "7771"
    host_down_with_lb_services(
        client, lb_port, host_down_count=2)


@if_test_host_down
def test_global_lbservice_with_healthcheck_1_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    lb_port = "7772"
    host_down_with_lb_services(
        client, lb_port, host_down_count=1, globalf=True)


@if_test_host_down
def test_global_lbservice_with_healthcheck_2_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    lb_port = "7773"
    host_down_with_lb_services(
        client, lb_port, host_down_count=2, globalf=True)


@if_test_host_down
def test_service_with_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    host_down_with_services(
        client, host_down_count=2)


@if_test_host_down
def test_global_service_with_host_down(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):
    host_down_with_services(
        client, host_down_count=2, globalf=True)


@if_test_host_down
def test_global_service_with_reconnecting_host(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):

    global_service_with_reconn_disconn_host(client, state="reconnecting")


@if_test_host_down
def test_global_service_with_disconnected_host(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):

    global_service_with_reconn_disconn_host(client, state="disconnected")


def global_service_with_reconn_disconn_host(client, state):

    # Pick one of the host and power down hosts
    host_down = ha_host_list[0]
    host_name = ha_host_list[0].hostname
    print("power down- " + host_name)
    action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_off")
    wait_for_host_agent_state(client, host_down, state,
                              HOST_ACTIVE_DISCONN_TIMEOUT)

    # Create service
    launch_config = {"imageUuid": HEALTH_CHECK_IMAGE_UUID}
    launch_config["labels"] = {"io.rancher.scheduler.global": "true"}
    service, env = create_env_and_svc(client, launch_config)
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    container_list = get_service_container_list(client, service)
    assert len(container_list) == get_service_instance_count(client, service)

    # Power on the host
    action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_on")
    wait_for_host_agent_state(client, host_down, "active",
                              HOST_DISCONN_ACTIVE_TIMEOUT)

    service = wait_success(client, service, 300)
    container_list = get_service_container_list(client, service)
    assert len(container_list) == get_service_instance_count(client, service)
    instance_list = get_containers_on_host_for_service(
        client, host_down, service)
    assert len(instance_list) == 1


@if_test_host_down
def test_global_service_with_inactive_host(
        client, ha_hosts, socat_containers,
        check_host_state_power_on):

    # Pick one of the host and deactivate this host
    host_down = ha_host_list[0]
    host_name = ha_host_list[0].hostname
    print("Deactivate " + host_name)
    host_down.deactivate()
    host_down = wait_for_condition(client,
                                   host_down,
                                   lambda x: x.state == "inactive",
                                   lambda x: 'Host state is ' + x.state,
                                   timeout=300)
    # Create service
    launch_config = {"imageUuid": HEALTH_CHECK_IMAGE_UUID}
    launch_config["labels"] = {"io.rancher.scheduler.global": "true"}
    service, env = create_env_and_svc(client, launch_config)
    service = service.activate()
    service = wait_success(client, service, 300)
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == get_service_instance_count(client, service)

    # Activate the host that is in deactivated state
    print("Activate " + host_name)
    host_down.activate()
    host_down = wait_for_condition(client,
                                   host_down,
                                   lambda x: x.state == "active",
                                   lambda x: 'Host state is ' + x.state,
                                   timeout=300)
    service = wait_success(client, service, 300)
    container_list = get_service_container_list(client, service)
    assert len(container_list) == get_service_instance_count(client, service)
    instance_list = get_containers_on_host_for_service(
        client, host_down, service)
    assert len(instance_list) == 1


def host_down_with_lb_services(client, lb_port, host_down_count,
                               scale=2, lb_scale=2, globalf=False):

    # Wait for hosts in "reconnecting" state to get to "active" state
    check_hosts_state(client)

    # Create environment with lb_service and 2 healthcheck enabled
    # service targets
    env, lb_service, service1, service2 = \
        env_with_lb_service_with_health_check_enabled_targets(
            client, lb_port, scale, lb_scale, globalf)

    # Pick hosts (and collect instances that will fgo unhealthy) that need
    # to be powered down
    down_hosts = []
    down_instances = []

    for i in range(0, len(ha_host_list)):
        host = ha_host_list[i]
        instance_list = \
            get_containers_on_host_for_service(client, host, lb_service)
        if len(instance_list) > 0:
            down_instances.extend(instance_list)
            down_hosts.append(host)
            if len(down_hosts) == host_down_count:
                break

    # Power Down hosts where lb service instances are running

    for host in down_hosts:
        host_name = host.hostname
        print("power down- " + host_name)
        print(ha_droplets[0])
        action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_off")

    print("Waiting for the hosts to go to disconnected state")
    for host in down_hosts:
        wait_for_host_agent_state(client, host, "disconnected",
                                  HOST_ACTIVE_DISCONN_TIMEOUT)

    # Check for service reconcile
    check_for_service_reconcile(
        client, lb_service, down_instances,
        instance_list, globalf)
    validate_lb_service(client, lb_service,
                        lb_port, [service1, service2])

    # Power on hosts that were powered off
    for host in down_hosts:
        host_name = host.hostname
        print("power on- " + host_name)
        action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_on")

    print("Waiting for the hosts to go to active state")
    for host in down_hosts:
        wait_for_host_agent_state(client, host, "active",
                                  HOST_DISCONN_ACTIVE_TIMEOUT)

    # if service is global, validate that new instances of the service gets
    # created on the host that gets powered on

    if (globalf):
        check_hosts_state(client)
        wait_for_scale_to_adjust(client, service1, timeout=300)
        wait_for_scale_to_adjust(client, service2, timeout=300)
        wait_for_scale_to_adjust(client, lb_service, timeout=300)
        validate_lb_service(client, lb_service,
                            lb_port, [service1, service2])

    delete_all(client, [env])


def host_down_with_healthcheck_services(client, host_down_count,
                                        retainIp=False):
    # Wait for hosts in "reconnecting" state to get to "active" state
    check_hosts_state(client)

    # Create service that is healthcheck enabled
    scale = 10
    env, service = service_with_healthcheck_enabled(
        client, scale, retainIp=retainIp)

    # Pick hosts (and collect instances that will fgo unhealthy) that need
    # to be powered down
    down_hosts = []
    down_instances = []

    for i in range(0, len(ha_host_list)):
        host = ha_host_list[i]
        instance_list = \
            get_containers_on_host_for_service(client, host, service)
        if len(instance_list) > 0:
            down_instances.extend(instance_list)
            down_hosts.append(host)
            if len(down_hosts) == host_down_count:
                break

    # Power Down hosts where service instances are running
    for host in down_hosts:
        host_name = host.hostname
        print("power down- " + host_name)
        print(ha_droplets[0])
        action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_off")

    print("Waiting for the hosts to go to disconnected state")
    for host in down_hosts:
        wait_for_host_agent_state(client, host, "disconnected",
                                  HOST_ACTIVE_DISCONN_TIMEOUT)

    # Check for service reconcile
    check_for_service_reconcile(
        client, service, down_instances, instance_list)

    # If retainIp is turned on , make sure that ip address assigned to
    # reconciled instances are the same

    if (retainIp):
        for con in down_instances:
            container_name = con.name
            containers = client.list_container(name=container_name,
                                               removed_null=True).data
            assert len(containers) == 1
            container = containers[0]
            assert container.primaryIpAddress == con.primaryIpAddress
            assert container.externalId != con.externalId

    # Power on hosts that were powered off
    delete_all(client, [env])
    for host in down_hosts:
        host_name = host.hostname
        print("power on- " + host_name)
        action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_on")

    print("Waiting for the hosts to go to active state")
    for host in down_hosts:
        wait_for_host_agent_state(client, host, "active",
                                  HOST_DISCONN_ACTIVE_TIMEOUT)


def host_down_with_services(client, host_down_count,
                            globalf=False):
    # Wait for hosts in "reconnecting" state to get to "active" state
    check_hosts_state(client)

    # Create service
    launch_config = {"imageUuid": HEALTH_CHECK_IMAGE_UUID}
    if globalf:
        launch_config["labels"] = {"io.rancher.scheduler.global": "true"}
        scale = 0
    else:
        scale = 10
    service, env = create_env_and_svc(client, launch_config, scale)
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    container_list = get_service_container_list(client, service)
    assert len(container_list) == get_service_instance_count(client, service)

    # Pick hosts (and collect instances that will go unhealthy) that need
    # to be powered down
    down_hosts = []
    down_instances = []

    for i in range(0, len(ha_host_list)):
        host = ha_host_list[i]
        instance_list = \
            get_containers_on_host_for_service(client, host, service)
        if len(instance_list) > 0:
            down_instances.extend(instance_list)
            down_hosts.append(host)
            if len(down_hosts) == host_down_count:
                break

    # Power Down hosts where service instances are running

    for host in down_hosts:
        host_name = host.hostname
        print("power down- " + host_name)
        print(ha_droplets[0])
        action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_off")

    print("Waiting for the hosts to go to disconnected state")
    for host in down_hosts:
        wait_for_host_agent_state(client, host, "disconnected",
                                  HOST_DISCONN_ACTIVE_TIMEOUT)

    # There will be no service reconcile since the instances will continue
    # to be "running" state in rancher-server

    for con in down_instances:
        assert con.state == "running"

    service = client.reload(service)
    assert service.state == "active"

    # Power on hosts that were powered off .
    # "stopped" state of the containers on the host will get synced and
    # service reconcile will trigger containers to be started.

    for host in down_hosts:
        host_name = host.hostname
        print("power on- " + host_name)
        action_on_digital_ocean_machine(ha_droplets[0][host_name], "power_on")

    print("Waiting for the hosts to go to active state")
    for host in down_hosts:
        wait_for_host_agent_state(client, host, "active",
                                  HOST_DISCONN_ACTIVE_TIMEOUT)

    wait_for_condition(
        client, service,
        lambda x: x.state == 'active',
        lambda x: 'State is: ' + x.state)

    for con in down_instances:
        assert con.state == "running"

    delete_all(client, [env])


def get_containers_on_host_for_service(client, host, service):
    instance_list = []
    hosts = client.list_host(
        kind='docker', removed_null=True, state='active', uuid=host.uuid,
        include="instances").data
    assert len(hosts) == 1
    for instance in hosts[0].instances:
        containers = client.list_container(
            state='running', uuid=instance.uuid, include="services").data
        assert len(containers) <= 1
        if (len(containers) == 1 and
                containers[0].createIndex is not None and
                containers[0].services[0].id == service.id):
            instance_list.append(instance)
    return instance_list


def check_for_service_reconcile(client, service, unhealthy_con_list,
                                instance_list, globalf=False):

    # Validate that unhealthy instances in the service get deleted
    # This code segment is commented as unhealthy state is
    # transient and hard to catch
    # for con in unhealthy_con_list:
    #    wait_for_condition(
    #        client, con,
    #        lambda x: x.healthState == 'unhealthy',
    #        lambda x: 'State is: ' + x.healthState, timeout=180)
    #    con = client.reload(con)
    #    assert con.healthState == "unhealthy"

    for con in unhealthy_con_list:
        wait_for_condition(
            client, con,
            lambda x: x.state in ('removed', 'purged'),
            lambda x: 'State is: ' + x.healthState, timeout=120)
        wait_for_scale_to_adjust(client, service, timeout=300)
        con = client.reload(con)
        assert con.state in ('removed', 'purged')

    # Validate all instances in the service are healthy
    container_list = get_service_container_list(client, service)
    if globalf is False:
        assert len(container_list) == service.scale
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState, timeout=120)

    # Validate all existing healthy instances in the service were not deleted
    # and recreated
    for unhealthy_con in unhealthy_con_list:
        for con in instance_list:
            if (unhealthy_con.name == con.name):
                instance_list.remove(con)

    for healthy_con in instance_list:
        healthy_con = client.reload(healthy_con)
        assert healthy_con.state == "running"
        assert healthy_con.healthState == "healthy"

    service = client.reload(service)
    assert service.state == "active"
    assert service.healthState == "healthy"


def check_hosts_state(client, timeout=300):
    print("Check if host state is active")
    start = time.time()
    disconn_host = 1
    while disconn_host != 0:
        time.sleep(.5)
        hosts = client.list_host(
            kind='docker', removed_null=True, agentState="disconnected").data
        disconn_host = len(hosts)
        if time.time() - start > timeout:
            raise Exception(
                'Timed out waiting for all hosts to be active in the setup')
    # Give some time for hosts that just got to"Active" state to settle down
    time.sleep(30)
    print("Host is Active")


def env_with_lb_service_with_health_check_enabled_targets(client,
                                                          lb_port,
                                                          scale=2, lb_scale=2,
                                                          globalf=False):

    # Create Environment with 2 health check enabled service and 1 LB service
    health_check = {"name": "check1", "responseTimeout": 2000,
                    "interval": 2000, "healthyThreshold": 2,
                    "unhealthyThreshold": 3,
                    "requestLine": "GET /name.html HTTP/1.0",
                    "port": 80}
    launch_config = {"imageUuid": HEALTH_CHECK_IMAGE_UUID,
                     "healthCheck": health_check
                     }
    lb_launch_config = {"ports": [lb_port],
                        "imageUuid": get_haproxy_image()}
    if (globalf):
        launch_config["labels"] = {"io.rancher.scheduler.global": "true"}
        lb_launch_config["labels"] = {"io.rancher.scheduler.global": "true"}
        scale = None
        lb_scale = None

    service1, env = create_env_and_svc(
        client, launch_config, scale)

    service1 = activate_svc(client, service1)
    container_list = get_service_container_list(client, service1)
    assert len(container_list) == get_service_instance_count(client, service1)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)

    service2 = create_svc(client, env, launch_config, scale)
    service2 = activate_svc(client, service2)
    container_list = get_service_container_list(client, service2)
    assert len(container_list) == get_service_instance_count(client, service2)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)

    port_rule1 = {"serviceId": service1.id,
                  "sourcePort": lb_port,
                  "targetPort": "80",
                  "protocol": "http"
                  }
    port_rule2 = {"serviceId": service2.id,
                  "sourcePort": lb_port,
                  "targetPort": "80",
                  "protocol": "http"
                  }
    lb_Config = {"portRules": [port_rule1, port_rule2]}
    lb_service = client.create_loadBalancerService(
        name="lb-1",
        stackId=env.id,
        launchConfig=lb_launch_config,
        scale=lb_scale,
        lbConfig=lb_Config)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    lb_service = activate_svc(client, lb_service)

    service_link1 = {"serviceId": service1.id}
    service_link2 = {"serviceId": service2.id}
    lb_service.setservicelinks(
        serviceLinks=[service_link1, service_link2])

    validate_lb_service(client, lb_service,
                        lb_port, [service1, service2])
    return env, lb_service, service1, service2
