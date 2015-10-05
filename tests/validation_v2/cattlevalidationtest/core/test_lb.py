from common_fixtures import *  # NOQA

LB_IMAGE_UUID = "docker:sangeetha/lbtest:latest"

CONTAINER_HOST_NAMES = ["container1", "container2", "container3"]

containers_in_host = []
logger = logging.getLogger(__name__)

if_lb_containers = pytest.mark.skipif(
    not os.environ.get('EXECUTE_STANDALONE_LB') or
    os.environ.get('EXECUTE_STANDALONE_LB').lower() != "true",
    reason='LB support for containers is terminated')


@pytest.fixture(scope='session', autouse=True)
def lb_targets(request, client):

    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    assert len(hosts) > 1, "Need at least 2 hosts for executing Lb test cases"

    for n in range(0, 2):
        con_name = random_str()
        con1 = client.create_container(name=con_name,
                                       networkMode=MANAGED_NETWORK,
                                       imageUuid=LB_IMAGE_UUID,
                                       environment={'CONTAINER_NAME':
                                                    CONTAINER_HOST_NAMES[n]
                                                    },
                                       requestedHostId=hosts[n].id
                                       )

        con1 = client.wait_success(con1, timeout=180)
        containers_in_host.append(con1)


def create_lb_for_container_lifecycle(client, host, port):

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=LB_IMAGE_UUID,
                                   environment={'CONTAINER_NAME':
                                                CONTAINER_HOST_NAMES[2]
                                                },
                                   requestedHostId=host.id
                                   )
    con1 = client.wait_success(con1, timeout=180)

    lb = lb.addtarget(
        loadBalancerTarget={"instanceId": con1.id, "ports": ["80"]})
    validate_add_target(client, con1, lb)

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    return lb, lb_config, listener, con1


def create_lb_with_one_listener_one_host_two_targets(client,
                                                     host, port,
                                                     lb_config=None,
                                                     lb_config_params=None,
                                                     listener_algorithm=None,
                                                     containers=None):
    """
    This method creates a LB rule.
    Adds the host that is passed to LB.

    Adds targets to the host. These targets are the containers parameter
    if passed, else shared containers are used.

    If lb_config is not passed , a new LB configuration is created which has a
    Lb listener with listener_algorithm if it is provided.If listener_algorithm
    is not provided , then it gets defaulted to round_robin.

    If lb_config is passed , this LB configuration is used for the LB rule.

    If listener_algorithm parameter is passed , listener gets created with
    default listener algorithm(round robin).

    """
    listener_config = {"name": random_str(),
                       "sourcePort": port,
                       "targetPort": '80',
                       "sourceProtocol": 'http',
                       "targetProtocol": 'http'
                       }
    listener = None
    if listener_algorithm is not None:
        listener_config["algorithm"] = listener_algorithm

    if lb_config is None:
        # Create Listener
        listener = client.create_loadBalancerListener(**listener_config)
        listener = client.wait_success(listener)

        # Create LB Config

        if lb_config_params is not None:
            lb_config = client.create_loadBalancerConfig(name=random_str(),
                                                         **lb_config_params)
        else:
            lb_config = client.create_loadBalancerConfig(name=random_str())

        lb_config = client.wait_success(lb_config)

        lb_config = lb_config.addlistener(loadBalancerListenerId=listener.id)
        validate_add_listener(client, listener, lb_config)

    # Create LB

    lb = client.create_loadBalancer(name=random_str(),
                                    loadBalancerConfigId=lb_config.id)
    lb = client.wait_success(lb)
    assert lb.state == "active"

    # Add host to LB

    lb = lb.addhost(hostId=host.id)
    validate_add_host(client, host, lb)

    # Add container to LB

    if containers is None:
        # Add default containers to LB
        for n in range(0, 2):
            target = {"instanceId": containers_in_host[n].id, "ports": ["80"]}
            lb = lb.addtarget(loadBalancerTarget=target)
            validate_add_target(client, containers_in_host[n], lb)
    else:
        for container in containers:
            target = {"instanceId": container.id, "ports": ["80"]}
            lb = lb.addtarget(loadBalancerTarget=target)
            validate_add_target(client, container, lb)

    if lb_config_params is None and listener_algorithm is None \
            and containers is None:
        con_hostname = CONTAINER_HOST_NAMES[0:2]
        check_round_robin_access(con_hostname, host, port)

    return lb, lb_config, listener


@if_lb_containers
def test_lb_with_targets(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    host = hosts[0]
    port = "8081"

    logger.info("Create LB for 2 targets on port - " + port)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client, host, "8081")

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_add_host_target_in_parallel(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    host = hosts[0]
    port = "9081"

    listener_config = {"name": random_str(),
                       "sourcePort": port,
                       "targetPort": '80',
                       "sourceProtocol": 'http',
                       "targetProtocol": 'http'
                       }

    listener = client.create_loadBalancerListener(**listener_config)
    listener = client.wait_success(listener)

    lb_config = client.create_loadBalancerConfig(name=random_str())
    listener = client.wait_success(listener)

    lb = client.create_loadBalancer(name=random_str(),
                                    loadBalancerConfigId=lb_config.id)
    lb = client.wait_success(lb)
    assert lb.state == "active"

    # Add host to LB , container to LB and listener to Lb config associated
    # with LB in parallel

    lb = lb.addhost(hostId=host.id)

    for n in range(0, 2):
        target = {"instanceId": containers_in_host[n].id, "ports": ["80"]}
        lb = lb.addtarget(loadBalancerTarget=target)

    lb_config = lb_config.addlistener(loadBalancerListenerId=listener.id)

    validate_add_listener(client, listener, lb_config)
    validate_add_host(client, host, lb)

    for n in range(0, 2):
        validate_add_target(client, containers_in_host[n], lb)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_add_target(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    host = hosts[0]
    port = "8082"

    logger.info("Create LB for 2 targets on port - " + port)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=LB_IMAGE_UUID,
                                   environment={'CONTAINER_NAME':
                                                CONTAINER_HOST_NAMES[2]
                                                },
                                   requestedHostId=host.id
                                   )
    con1 = client.wait_success(con1, timeout=180)

    # Add target to existing LB
    lb = lb.addtarget(
        loadBalancerTarget={"instanceId": con1.id, "ports": ["80"]})
    validate_add_target(client, con1, lb)

    logger.info("Check LB access after adding target with container name: "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_remove_target(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    host = hosts[0]
    port = "8083"

    logger.info("Create LB for 2 targets on port - " + port)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=LB_IMAGE_UUID,
                                   environment={'CONTAINER_NAME':
                                                CONTAINER_HOST_NAMES[2]
                                                },
                                   requestedHostId=host.id
                                   )

    con1 = client.wait_success(con1, timeout=180)

    # Add target to existing LB
    lb = lb.addtarget(
        loadBalancerTarget={"instanceId": con1.id, "ports": ["80"]})
    validate_add_target(client, con1, lb)

    logger.info("Check LB access after adding target with container name: "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    # Remove target to existing LB

    lb = lb.removetarget(
        loadBalancerTarget={"instanceId": con1.id, "ports": ["80"]})
    validate_remove_target(client, con1, lb)

    logger.info("Check LB access after removing target with container name: "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_add_listener(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    host = hosts[0]
    port1 = "8084"
    port2 = "8085"

    logger.info("Create LB for 2 targets on port - " + port1)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client, host, port1)

    # Create Listener

    listener = client.create_loadBalancerListener(name=random_str(),
                                                  sourcePort=port2,
                                                  targetPort='80',
                                                  sourceProtocol='http',
                                                  targetProtocol='http')
    listener = client.wait_success(listener)

    # Add listener to LB config which is associated to LB

    lb_config = lb_config.addlistener(loadBalancerListenerId=listener.id)
    validate_add_listener(client, listener, lb_config)

    logger.info("Check LB access after adding listener for port: " + port2)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port1)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port2)

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_remove_listener(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]

    port1 = "8086"
    port2 = "8087"

    logger.info("Create LB for 2 targets on port - " + port1)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port1)

    # Create Listener

    listener = client.create_loadBalancerListener(name=random_str(),
                                                  sourcePort=port2,
                                                  targetPort='80',
                                                  sourceProtocol='http',
                                                  targetProtocol='http')
    listener = client.wait_success(listener)

    # Add listener to LB config which is associated to LB

    lb_config = lb_config.addlistener(loadBalancerListenerId=listener.id)
    validate_add_listener(client, listener, lb_config)

    logger.info("Check LB access after adding listener for port: " + port2)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port1)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port2)

    # Remove listener to LB config which is associated to LB

    lb_config = lb_config.removelistener(loadBalancerListenerId=listener.id)
    validate_remove_listener(client, listener, lb_config)

    logger.info("Check LB access after removing listener for port: " + port2)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port1)

    check_no_access(host, port2)

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_add_host(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 1

    host = hosts[0]
    host2 = hosts[1]
    port = "8088"

    logger.info("Create LB for 2 targets on port - " + port)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    # Add host to existing LB
    lb = lb.addhost(hostId=host2.id)
    validate_add_host(client, host2, lb)

    logger.info("Check LB access after adding host: " + host.id)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)
    check_round_robin_access(con_hostname, host2, port)

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_remove_host(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 1

    host = hosts[0]
    host2 = hosts[1]
    port = "8089"

    logger.info("Create LB for 2 targets on port - " + port)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host,  port)

    # Add host to LB
    lb = lb.addhost(hostId=host2.id)
    validate_add_host(client, host2, lb)

    logger.info("Check LB access after adding host: " + host.id)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)
    check_round_robin_access(con_hostname, host2, port)

    # Remove host to LB

    lb = lb.removehost(hostId=host2.id)
    validate_remove_host(client,  host2, lb)

    logger.info("Check LB access after removing host: " + host.id)

    check_round_robin_access(con_hostname, host, port)

    # Check no access on host2 - TBD
    check_no_access(host2, port)

    # Add host to LB
    lb = lb.addhost(hostId=host2.id)
    validate_add_host(client, host2, lb)

    logger.info("Check LB access after adding host: " + host.id)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)
    check_round_robin_access(con_hostname, host2, port)

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_container_lifecycle_stop_start(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    host = hosts[0]
    port = "9090"

    logger.info("Create LB for 2 targets on port - " + port)

    lb, lb_config, listener, con1 =\
        create_lb_for_container_lifecycle(client, host, port)
    # Stop container

    con1 = client.wait_success(con1.stop())
    assert con1.state == 'stopped'

    logger.info("Check LB access after stopping container "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)

    # Start Container
    con1 = client.wait_success(con1.start())
    assert con1.state == 'running'

    logger.info("Check LB access after starting container "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_container_lifecycle_restart(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "9091"

    logger.info("Create LB for 3 targets on port - " + port)

    lb, lb_config, listener, con1 = \
        create_lb_for_container_lifecycle(client, host, port)
    # Restart Container
    con1 = client.wait_success(con1.restart())
    assert con1.state == 'running'

    logger.info(
        "Check LB access after restarting container " +
        CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
@pytest.mark.skipif(True, reason='not implemented yet')
def test_lb_container_lifecycle_delete_restore(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "9092"

    logger.info("Create LB for 3 targets on port - " + port)

    lb, con1 = create_lb_for_container_lifecycle(client, host, port)

    # Delete Container
    con1 = client.wait_success(client.delete(con1))
    assert con1.state == 'removed'

    logger.info("Check LB access after deleting container "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)

    # Restore Container
    con1 = client.wait_success(con1.restore())
    assert con1.state == 'stopped'

    con1 = client.wait_success(con1.start())
    assert con1.state == 'running'

    logger.info("Check LB access after restoring container "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_container_lifecycle_delete_purge(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "9093"

    logger.info("Create LB for 3 targets on port - " + port)

    lb, lb_config, listener, con1 =\
        create_lb_for_container_lifecycle(client, host, port)

    # Delete Container and purge it
    con1 = client.wait_success(client.delete(con1))
    assert con1.state == 'removed'

    con1 = client.wait_success(con1.purge())

    logger.info("Check LB access after purging container "
                + CONTAINER_HOST_NAMES[2])

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)

    target_maps = client.list_loadBalancerTarget(loadBalancerId=lb.id,
                                                 instanceId=con1.id)

    assert len(target_maps) == 1
    target_map = target_maps[0]
    target_map = wait_for_condition(client, target_map,
                                    lambda x: x.state == 'removed',
                                    lambda x: 'State is: ' + x.state)

    assert target_map.state == "removed"

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_add_target_in_different_host(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 1
    host = hosts[0]
    host2 = hosts[1]
    port = "8091"

    logger.info("Create LB for 2 targets on port - " + port)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host,
                                                         port)

    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=LB_IMAGE_UUID,
                                   environment={'CONTAINER_NAME':
                                                CONTAINER_HOST_NAMES[2]
                                                },
                                   requestedHostId=host2.id
                                   )
    con1 = client.wait_success(con1, timeout=180)

    lb = lb.addtarget(
        loadBalancerTarget={"instanceId": con1.id, "ports": ["80"]})
    validate_add_target(client, con1, lb)

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_config_shared_by_2_lb_instances(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 1
    host = hosts[0]
    host2 = hosts[1]
    port = "8092"

    logger.info("Create LB for 2 targets on port - " + port)

    lb1, lb_config1, listener1 = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    # Create another LB using the same the Lb configuration
    lb2, lb_config2, listener2 = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host2, port,
                                                         lb_config1)

    delete_all(client, [lb1])
    cleanup_lb(client, lb2, lb_config2, listener2)


@if_lb_containers
def test_modify_lb_config_shared_by_2_lb_instances(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 1
    host1 = hosts[0]
    host2 = hosts[1]
    port1 = "8093"
    port2 = "8094"

    logger.info("Create LB for 2 targets on port - " + port1 +
                "- host-" + str(host1.id))

    # Create LB - LB1
    lb1, lb_config, listener1 = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host1, port1)

    logger.info("Create LB for 2 targets on port - " + port1 +
                "- host-" + str(host2.id))

    # Create another LB - LB2 using the same the Lb configuration
    lb2, lb_config, listener2 = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host2, port1,
                                                         lb_config)

    # Add new listener to existing LB configuration that is attached to 2 LBs.
    listener2 = client.create_loadBalancerListener(name=random_str(),
                                                   sourcePort=port2,
                                                   targetPort='80',
                                                   sourceProtocol='http',
                                                   targetProtocol='http')
    listener2 = client.wait_success(listener2)

    # Add listener to lB config
    lb_config = lb_config.addlistener(loadBalancerListenerId=listener2.id)
    validate_add_listener(client, listener2, lb_config)

    # Check is new listener is associated with LB1
    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host1, port1)
    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host1, port2)

    # Check is new listener is associated with LB2
    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host2, port1)
    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host2, port2)

    # Remove listener from lB config
    lb_config = lb_config.removelistener(loadBalancerListenerId=listener2.id)
    validate_remove_listener(client, listener2, lb_config)

    # Check if removed listener is not associated with LB1 anymore
    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host1, port1)
    check_no_access(host1, port2)

    # Check if removed listener is not associated with LB2 anymore
    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host2, port1)
    check_no_access(host2, port2)

    cleanup_lb(client, lb1, None, listener1)
    cleanup_lb(client, lb2, lb_config, listener2)


@if_lb_containers
def test_reuse_port_after_lb_deletion(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "9000"

    logger.info("Create LB for 2 targets on port - " + port)

    lb_1, lb_config_1, listener_1 = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    lb_1 = client.wait_success(client.delete(lb_1))
    assert lb_1.state == 'removed'

    lb_2, lb_config_2, listener_2 = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=LB_IMAGE_UUID,
                                   environment={'CONTAINER_NAME':
                                                CONTAINER_HOST_NAMES[2]
                                                },
                                   requestedHostId=host.id
                                   )

    con1 = client.wait_success(con1, timeout=180)
    lb_2 = lb_2.addtarget(loadBalancerTarget={
        "instanceId": con1.id, "ports": ["80"]})
    validate_add_target(client, con1, lb_2)

    con_hostname = CONTAINER_HOST_NAMES
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb_1, lb_config_1, listener_1)
    cleanup_lb(client, lb_2, lb_config_2, listener_2)


@if_lb_containers
def test_lb_for_container_with_port_mapping(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]

    port1 = "9002"
    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=LB_IMAGE_UUID,
                                   environment={'CONTAINER_NAME':
                                                CONTAINER_HOST_NAMES[0]
                                                },
                                   ports=[port1+":80/tcp"],
                                   requestedHostId=host.id
                                   )
    con1 = client.wait_success(con1, timeout=180)

    port2 = "9003"
    con2 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=LB_IMAGE_UUID,
                                   environment={'CONTAINER_NAME':
                                                CONTAINER_HOST_NAMES[1]
                                                },
                                   ports=[port2+":80/tcp"],
                                   requestedHostId=host.id
                                   )
    con2 = client.wait_success(con2, timeout=180)

    port = "9001"

    logger.info("Create LB for 2 targets which have port "
                "mappings on port - " + port)

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(client,
                                                         host, port)

    # Check LB rule works
    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)

    # Check exposed ports for containers work
    check_access(host, port1, CONTAINER_HOST_NAMES[0])
    check_access(host, port2, CONTAINER_HOST_NAMES[1])

    delete_all(client, [con1, con2])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_with_lb_cookie(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "8095"

    logger.info("Create LB for 2 targets with lbCookieStickinessPolicy " +
                "on port - " + port)

    lbcookie_policy = {"lbCookieStickinessPolicy":
                       {"mode": "insert",
                        "cookie": "cookie-1",
                        "indirect": True,
                        "nocache": True,
                        "postonly": False
                        }
                       }
    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(
            client,
            host, port,
            lb_config_params=lbcookie_policy
            )

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_for_lbcookie_policy(con_hostname, host, port)

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_with_app_cookie(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "8096"
    cookie_name = "appcookie1"

    logger.info("Create LB for 2 targets with appCookieStickinessPolicy " +
                "on port - " + port)

    appcookie_policy = {"appCookieStickinessPolicy":
                        {"mode": "query_string",
                         "requestLearn": True,
                         "timeout": 3600000,
                         "cookie": cookie_name,
                         "maxLength": 40,
                         "prefix": False
                         }
                        }
    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(
            client,
            host, port,
            lb_config_params=appcookie_policy
            )

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_for_appcookie_policy(con_hostname, host, port, cookie_name)

    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_with_health_check_with_uri(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "8097"

    logger.info("Create LB for 2 targets with health check enabled " +
                "on port - " + port)

    health_check = {"healthCheck":
                    {"interval": 2000,
                     "responseTimeout": 2000,
                     "healthyThreshold": 2,
                     "unhealthyThreshold": 3,
                     "uri": "GET /name.html"
                     }
                    }

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(
            client,
            host, port,
            lb_config_params=health_check

            )
    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=TEST_IMAGE_UUID,
                                   requestedHostId=host.id
                                   )
    con1 = client.wait_success(con1, timeout=180)
    lb = lb.addtarget(
        loadBalancerTarget={"instanceId": con1.id, "ports": ["80"]})
    validate_add_target(client, con1, lb)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_with_health_check_without_uri(client):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "8098"

    logger.info("Create LB for 2 targets with health check enabled " +
                "on port - " + port)

    health_check = {"healthCheck":
                    {"interval": 2000,
                     "responseTimeout": 2000,
                     "healthyThreshold": 2,
                     "unhealthyThreshold": 3
                     }
                    }

    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(
            client,
            host, port,
            lb_config_params=health_check
            )

    con1 = client.create_container(name=random_str(),
                                   networkMode=MANAGED_NETWORK,
                                   imageUuid=TEST_IMAGE_UUID,
                                   requestedHostId=host.id
                                   )

    con1 = client.wait_success(con1, timeout=180)
    lb = lb.addtarget(
        loadBalancerTarget={"instanceId": con1.id, "ports": ["80"]})
    validate_add_target(client, con1, lb)

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_round_robin_access(con_hostname, host, port)

    delete_all(client, [con1])
    cleanup_lb(client, lb, lb_config, listener)


@if_lb_containers
def test_lb_with_source(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]
    port = "8101"

    logger.info("Create LB for 2 targets with source algorithm  " +
                "on port - " + port)
    lb, lb_config, listener = \
        create_lb_with_one_listener_one_host_two_targets(
            client,
            host, port,
            listener_algorithm="source"
            )

    con_hostname = CONTAINER_HOST_NAMES[0:2]
    check_for_stickiness(con_hostname, host, port)

    cleanup_lb(client, lb, lb_config, listener)


def check_round_robin_access(container_names, host, port):
    wait_until_lb_is_active(host, port)
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


@if_lb_containers
def check_no_access(host, port):
    try:
        url = "http://" + host.ipAddresses()[0].address + ":" +\
              port + "/name.html"
        requests.get(url)
        assert False
    except requests.ConnectionError:
        logger.info("Connection Error - " + url)


@if_lb_containers
def check_access(host, port, expected_response):
    url = "http://" + host.ipAddresses()[0].address + ":" +\
          port + "/name.html"
    r = requests.get(url)
    response = r.text.strip("\n")
    logger.info(response)
    r.close()
    assert response == expected_response


@if_lb_containers
def check_for_appcookie_policy(container_names, host, port, cookie_name):
    wait_until_lb_is_active(host, port)

    con_hostname = container_names[:]
    url = "http://" + host.ipAddresses()[0].address + \
          ":" + port + "/name.html"
    headers = {"Cookie": cookie_name + "=test123"}

    r = requests.get(url, headers=headers)
    sticky_response = r.text.strip("\n")
    logger.info(sticky_response)
    r.close()
    assert sticky_response in con_hostname

    for n in range(0, 10):
        r = requests.get(url, headers=headers)
        response = r.text.strip("\n")
        r.close()
        logger.info(response)
        assert response == sticky_response


@if_lb_containers
def check_for_lbcookie_policy(container_names, host, port):
    wait_until_lb_is_active(host, port)
    con_hostname = container_names[:]
    url = "http://" + host.ipAddresses()[0].address + \
          ":" + port + "/name.html"

    session = requests.Session()
    r = session.get(url)
    sticky_response = r.text.strip("\n")
    logger.info(sticky_response)
    r.close()
    assert sticky_response in con_hostname

    for n in range(0, 10):
        r = session.get(url)
        response = r.text.strip("\n")
        r.close()
        logger.info(response)
        assert response == sticky_response


@if_lb_containers
def check_for_stickiness(container_names, host, port):
    wait_until_lb_is_active(host, port)

    con_hostname = container_names[:]
    url = "http://" + host.ipAddresses()[0].address + \
          ":" + port + "/name.html"

    r = requests.get(url)
    sticky_response = r.text.strip("\n")
    logger.info(sticky_response)
    r.close()
    assert sticky_response in con_hostname

    for n in range(0, 10):
        r = requests.get(url)
        response = r.text.strip("\n")
        r.close()
        logger.info(response)
        assert response == sticky_response


def validate_add_target(client, container, lb):
    target_maps = client.list_loadBalancerTarget(loadBalancerId=lb.id,
                                                 instanceId=container.id)
    assert len(target_maps) == 1
    target_map = target_maps[0]
    wait_for_condition(
        client, target_map,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state)


def validate_remove_target(client, container, lb):
    target_maps = client.list_loadBalancerTarget(loadBalancerId=lb.id,
                                                 instanceId=container.id)
    assert len(target_maps) == 1
    target_map = target_maps[0]
    wait_for_condition(
        client, target_map,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)


def validate_add_listener(client, listener, lb_config):
    lb_config_maps = client.\
        list_loadBalancerConfigListenerMap(loadBalancerListenerId=listener.id,
                                           loadBalancerConfigId=lb_config.id)
    assert len(lb_config_maps) == 1
    config_map = lb_config_maps[0]
    wait_for_condition(
        client, config_map,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state)


def validate_remove_listener(client, listener, lb_config):
    lb_config_maps = client.\
        list_loadBalancerConfigListenerMap(loadBalancerListenerId=listener.id,
                                           loadBalancerConfigId=lb_config.id)
    assert len(lb_config_maps) == 1
    config_map = lb_config_maps[0]
    wait_for_condition(
        client, config_map,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)


def validate_add_host(client, host, lb):
    host_maps = client.list_loadBalancerHostMap(loadBalancerId=lb.id,
                                                hostId=host.id,
                                                removed_null=True)
    assert len(host_maps) == 1
    host_map = host_maps[0]
    wait_for_condition(
        client, host_map,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state)


def validate_remove_host(client, host, lb):
    host_maps = client.list_loadBalancerHostMap(loadBalancerId=lb.id,
                                                hostId=host.id)
    assert len(host_maps) == 1
    host_map = host_maps[0]
    wait_for_condition(
        client, host_map,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)


def wait_until_lb_is_active(host, port, timeout=45):
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


def cleanup_lb(client, lb, lb_config, listener):
    delete_all(client, [lb])
    if lb_config is not None:
        delete_all(client, [lb_config])
    if listener is not None:
        delete_all(client, [listener])
