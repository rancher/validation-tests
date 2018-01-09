from common_fixtures import *  # NOQA
from cattle import ApiError
from test_services_lb_balancer import create_environment_with_balancer_services


TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST

LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"


docker_config_running = [{"docker_param_name": "State.Running",
                         "docker_param_value": "true"}]

docker_config_stopped = [{"docker_param_name": "State.Running",
                          "docker_param_value": "false"}]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

total_time = [0]
shared_env = []


@pytest.fixture(scope='session', autouse=True)
def create_env_for_activate_deactivate(request, client):
    service, env = create_env_and_svc_activate(client, 3, False)
    shared_env.append({"service": service,
                       "env": env})

    def fin():
        to_delete = [env]
        delete_all(client, to_delete)

    request.addfinalizer(fin)


def deactivate_activate_service(client, service):

    # Deactivate service
    service = service.deactivate()
    service = client.wait_success(service, 300)
    assert service.state == "inactive"
    # Activate Service
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    return service


def create_env_and_svc_activate(client, scale, check=True,
                                retainIp=False):
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale, check, retainIp)
    return service, env


def create_env_and_svc_activate_launch_config(
        client, launch_config, scale,
        check=True, retainIp=False):
    start_time = time.time()
    service, env = create_env_and_svc(client, launch_config, scale, retainIp)
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    if check:
        check_container_in_service(client, service)
    time_taken = time.time() - start_time
    total_time[0] = total_time[0] + time_taken
    logger.info("time taken - " + str(time_taken))
    logger.info("total time taken - " + str(total_time[0]))
    return service, env


def test_services_docker_options(client, socat_containers):

    hosts = client.list_host(kind='docker', removed_null=True, state="active")

    con_host = hosts[0]

    vol_container = client.create_container(imageUuid=TEST_IMAGE_UUID,
                                            name=random_str(),
                                            requestedHostId=con_host.id
                                            )

    vol_container = client.wait_success(vol_container)

    volume_in_host = "/test/container"
    volume_in_container = "/test/vol1"
    docker_vol_value = volume_in_host + ":" + volume_in_container + ":ro"

    cap_add = ["CHOWN"]
    cap_drop = ["KILL"]
    restart_policy = {"maximumRetryCount": 10, "name": "on-failure"}
    dns_search = ['1.2.3.4']
    dns_name = ['1.2.3.4']
    domain_name = "rancher.io"
    host_name = "test"
    user = "root"
    command = ["sleep", "9000"]
    env_var = {"TEST_FILE": "/etc/testpath.conf"}
    memory = 8000000
    cpu_set = "0"
    cpu_shares = 400

    launch_config = {"imageUuid": TEST_SERVICE_OPT_IMAGE_UUID,
                     "command": command,
                     "dataVolumes": [docker_vol_value],
                     "dataVolumesFrom": [vol_container.id],
                     "environment": env_var,
                     "capAdd": cap_add,
                     "capDrop": cap_drop,
                     "dnsSearch": dns_search,
                     "dns": dns_name,
                     "privileged": True,
                     "domainName": domain_name,
                     "stdinOpen": True,
                     "tty": True,
                     "memory": memory,
                     "cpuSet": cpu_set,
                     "cpuShares": cpu_shares,
                     "restartPolicy": restart_policy,
                     "directory": "/",
                     "hostname": host_name,
                     "user": user,
                     "requestedHostId": con_host.id
                     }

    scale = 2

    service, env = create_env_and_svc(client, launch_config,
                                      scale)

    env = env.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(client, service)

    container_list = get_service_container_list(client, service)

    dns_name.append(RANCHER_DNS_SERVER)
    dns_search.append(env.name+"."+RANCHER_DNS_SEARCH)
    dns_search.append(service.name+"."+env.name+"."+RANCHER_DNS_SEARCH)
    dns_search.append(RANCHER_DNS_SEARCH)

    for c in container_list:
        docker_client = get_docker_client(c.hosts[0])
        inspect = docker_client.inspect_container(c.externalId)

        assert docker_vol_value in inspect["HostConfig"]["Binds"]
        assert inspect["HostConfig"]["VolumesFrom"] == \
            [vol_container.externalId]
        assert inspect["HostConfig"]["PublishAllPorts"] is False
        assert inspect["HostConfig"]["Privileged"] is True
        assert inspect["Config"]["OpenStdin"] is True
        assert inspect["Config"]["Tty"] is True
        assert inspect["HostConfig"]["Dns"] == dns_name
        assert inspect["HostConfig"]["DnsSearch"] == dns_search
        assert inspect["Config"]["Hostname"] == host_name
        assert inspect["Config"]["Domainname"] == domain_name
        assert inspect["Config"]["User"] == user
        assert inspect["HostConfig"]["CapAdd"] == cap_add
        assert inspect["HostConfig"]["CapDrop"] == cap_drop
        assert inspect["HostConfig"]["CpusetCpus"] == cpu_set
#       No support for restart
        assert inspect["HostConfig"]["RestartPolicy"]["Name"] == ""
        assert \
            inspect["HostConfig"]["RestartPolicy"]["MaximumRetryCount"] == 0
        assert inspect["Config"]["Cmd"] == command
        assert inspect["HostConfig"]["Memory"] == memory
        assert "TEST_FILE=/etc/testpath.conf" in inspect["Config"]["Env"]
        assert inspect["HostConfig"]["CpuShares"] == cpu_shares

    delete_all(client, [env])


def test_services_docker_options_2(client, socat_containers):

    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    cpu_shares = 400
    ulimit = {"hard": 1024, "name": "cpu", "soft": 1024}
    ulimit_inspect = {"Hard": 1024, "Name": "cpu", "Soft": 1024}
    ipcMode = "host"
    sysctls = {"net.ipv4.ip_forward": "1"}
    dev_opts = {
        '/dev/null': {
            'readIops': 2000,
            'writeIops': 3000,
            'readBps': 4000,
            'writeBps': 200,
        }
    }
    cpu_shares = 400
    blkio_weight = 1000
    cpu_period = 10000
    cpu_quota = 20000
    cpu_set = "0"
    cpu_setmems = "0"
    dns_opt = ["abc"]
    group_add = ["root"]
    kernel_memory = 6000000
    memory_reservation = 5000000
    memory_swap = -1
    memory_swappiness = 100
    oom_killdisable = True
    oom_scoreadj = 100
    read_only = True
    shm_size = 1024
    stop_signal = "SIGTERM"
    uts = "host"

    dev_opts_inspect = {u"Path": "/dev/null",
                        u"Rate": 400}
    cgroup_parent = "xyz"
    extraHosts = ["host1:10.1.1.1", "host2:10.2.2.2"]
    tmp_fs = {"/tmp": "rw"}
    security_opt = ["label=user:USER", "label=role:ROLE"]

    launch_config = {"imageUuid": TEST_SERVICE_OPT_IMAGE_UUID,
                     "extraHosts": extraHosts,
                     "privileged": True,
                     "cpuShares": cpu_shares,
                     "blkioWeight": blkio_weight,
                     "blkioDeviceOptions": dev_opts,
                     "cgroupParent": cgroup_parent,
                     "cpuShares": cpu_shares,
                     "cpuPeriod": cpu_period,
                     "cpuQuota": cpu_quota,
                     "cpuSet": cpu_set,
                     "cpuSetMems": cpu_setmems,
                     "dnsOpt": dns_opt,
                     "groupAdd": group_add,
                     "kernelMemory": kernel_memory,
                     "memoryReservation": memory_reservation,
                     "memorySwap": memory_swap,
                     "memorySwappiness": memory_swappiness,
                     "oomKillDisable": oom_killdisable,
                     "oomScoreAdj": oom_scoreadj,
                     "readOnly": read_only,
                     "securityOpt": security_opt,
                     "shmSize": shm_size,
                     "stopSignal": stop_signal,
                     "sysctls": sysctls,
                     "tmpfs": tmp_fs,
                     "ulimits": [ulimit],
                     "ipcMode": ipcMode,
                     "uts": uts,
                     "requestedHostId": hosts[0].id
                     }

    scale = 2

    service, env = create_env_and_svc(client, launch_config,
                                      scale)

    env = env.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(client, service)

    container_list = get_service_container_list(client, service)

    for c in container_list:
        docker_client = get_docker_client(c.hosts[0])
        inspect = docker_client.inspect_container(c.externalId)

        assert inspect["HostConfig"]["ExtraHosts"] == extraHosts
        assert inspect["HostConfig"]["BlkioWeight"] == blkio_weight
        dev_opts_inspect["Path"] = "/dev/null"
        dev_opts_inspect["Rate"] = 4000
        assert \
            inspect["HostConfig"]["BlkioDeviceReadBps"] == [dev_opts_inspect]
        dev_opts_inspect["Path"] = "/dev/null"
        dev_opts_inspect["Rate"] = 200
        assert \
            inspect["HostConfig"]["BlkioDeviceWriteBps"] == [dev_opts_inspect]
        dev_opts_inspect["Path"] = "/dev/null"
        dev_opts_inspect["Rate"] = 2000
        assert \
            inspect["HostConfig"]["BlkioDeviceReadIOps"] == [dev_opts_inspect]
        dev_opts_inspect["Path"] = "/dev/null"
        dev_opts_inspect["Rate"] = 3000
        assert \
            inspect["HostConfig"]["BlkioDeviceWriteIOps"] == [dev_opts_inspect]
        assert inspect["HostConfig"]["CpuShares"] == cpu_shares
        assert inspect["HostConfig"]["CgroupParent"] == cgroup_parent
        assert inspect["HostConfig"]["CpuPeriod"] == cpu_period
        assert inspect["HostConfig"]["CpuQuota"] == cpu_quota
        assert inspect["HostConfig"]["CpusetCpus"] == cpu_set
        assert inspect["HostConfig"]["CpusetMems"] == cpu_setmems
        assert inspect["HostConfig"]["KernelMemory"] == kernel_memory
        assert inspect["HostConfig"]["MemoryReservation"] == memory_reservation
        assert inspect["HostConfig"]["MemorySwap"] == memory_swap
        assert inspect["HostConfig"]["MemorySwappiness"] == memory_swappiness
        assert inspect["HostConfig"]["OomKillDisable"]
        assert inspect["HostConfig"]["OomScoreAdj"] == oom_scoreadj
        assert inspect["HostConfig"]["ReadonlyRootfs"]
        assert inspect["HostConfig"]["SecurityOpt"] == security_opt
        assert inspect["HostConfig"]["Tmpfs"] == tmp_fs
        assert inspect["HostConfig"]["ShmSize"] == shm_size
        assert inspect["Config"]["StopSignal"] == stop_signal
        assert inspect["HostConfig"]["Ulimits"] == [ulimit_inspect]
        assert inspect["HostConfig"]["IpcMode"] == ipcMode
        assert inspect["HostConfig"]["UTSMode"] == uts
        assert inspect["HostConfig"]["DnsOptions"] == dns_opt
        assert inspect["HostConfig"]["GroupAdd"] == group_add
    delete_all(client, [env])


def test_services_port_and_link_options(client,
                                        socat_containers):

    hosts = client.list_host(kind='docker', removed_null=True, state="active")

    host = hosts[0]
    link_host = hosts[1]

    link_name = "WEB1"
    link_port = 80
    exposed_port = 9999

    link_container = client.create_container(
        imageUuid=LB_IMAGE_UUID,
        environment={'CONTAINER_NAME': link_name},
        name=random_str(),
        requestedHostId=host.id
        )

    link_container = client.wait_success(link_container)

    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [str(exposed_port)+":22/tcp"],
                     "instanceLinks": {
                         link_name:
                             link_container.id},
                     "requestedHostId": link_host.id,
                     }

    service, env = create_env_and_svc(client, launch_config, 1)

    env = env.activateservices()
    service = client.wait_success(service, 300)

    container_name = get_container_name(env, service, 1)
    containers = client.list_container(name=container_name, state="running")
    assert len(containers) == 1
    con = containers[0]

    validate_exposed_port_and_container_link(client, con, link_name,
                                             link_port, exposed_port)

    delete_all(client, [env, link_container])


def test_services_multiple_expose_port(client):

    public_port = range(2080, 2092)
    private_port = range(80, 92)
    port_mapping = []
    for i in range(0, len(public_port)):
        port_mapping.append(str(public_port[i])+":" +
                            str(private_port[i]) + "/tcp")
    launch_config = {"imageUuid": MULTIPLE_EXPOSED_PORT_UUID,
                     "ports": port_mapping,
                     }

    service, env = create_env_and_svc(client, launch_config, 3)

    env = env.activateservices()
    service = client.wait_success(service, 300)

    validate_exposed_port(client, service, public_port)

    delete_all(client, [env])


def test_services_random_expose_port(client):

    launch_config = {"imageUuid": MULTIPLE_EXPOSED_PORT_UUID,
                     "ports": ["80/tcp", "81/tcp"]
                     }
    service, env = create_env_and_svc(client, launch_config, 3)

    env = env.activateservices()
    service = client.wait_success(service, 300)

    port = service.launchConfig["ports"][0]
    exposedPort1 = int(port[0:port.index(":")])
    assert exposedPort1 in range(49153, 65535)

    port = service.launchConfig["ports"][1]
    exposedPort2 = int(port[0:port.index(":")])
    assert exposedPort2 in range(49153, 65535)

    print service.publicEndpoints
    validate_exposed_port(client, service, [exposedPort1, exposedPort2])

    delete_all(client, [env])


def test_services_random_expose_port_exhaustrange(
        admin_client, client):

    # Set random port range to 6 ports and exhaust 5 of them by creating a
    # service that has 5 random ports exposed
    project = admin_client.list_project(name=PROJECT_NAME)[0]
    project = admin_client.update(
        project, servicesPortRange={"startPort": 65500, "endPort": 65505})
    project = wait_success(client, project)

    launch_config = {"imageUuid": MULTIPLE_EXPOSED_PORT_UUID,
                     "ports":
                         ["80/tcp", "81/tcp", "82/tcp", "83/tcp", "84/tcp"]
                     }

    service, env = create_env_and_svc(client, launch_config, 3)

    env = env.activateservices()
    service = client.wait_success(service, 60)

    wait_for_condition(client,
                       service,
                       lambda x: len(x.publicEndpoints) == 15,
                       lambda x:
                       "publicEndpoints is " + str(x.publicEndpoints))
    exposedPorts = []
    for i in range(0, 5):
        port = service.launchConfig["ports"][0]
        exposedPort = int(port[0:port.index(":")])
        exposedPorts.append(exposedPort)
        assert exposedPort in range(65500, 65506)

    validate_exposed_port(client, service, exposedPorts)

    # Create a service that has 2 random exposed ports when there is only 1
    # free port available in the random port range
    # Validate that the service gets created with no ports exposed

    launch_config = {"imageUuid": MULTIPLE_EXPOSED_PORT_UUID,
                     "ports":
                         ["80/tcp", "81/tcp"]
                     }
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config,
                                     scale=3,
                                     startOnCreate=True)
    time.sleep(5)
    assert service1.state == "registering"
    """
    service1, env1 = create_env_and_svc(client, launch_config, 3)
    env1 = env1.activateservices()
    service1 = client.wait_success(service1, 60)
    print service.publicEndpoints
    wait_for_condition(client,
                       service1,
                       lambda x: x.publicEndpoints is not None,
                       lambda x:
                       "publicEndpoints is " + str(x.publicEndpoints))
    service1 = client.reload(service1)
    print service.publicEndpoints
    assert len(service1.publicEndpoints) == 0
    """

    # Delete the service that consumed 5 random ports
    delete_all(client, [service])
    wait_for_condition(
        client, service,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)

    # Wait for service that is stuck in "registering" state to get to "active"
    # state

    wait_for_condition(
        client, service1,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state,
        120)

    wait_for_condition(client,
                       service1,
                       lambda x: x.publicEndpoints is not None,
                       lambda x:
                       "publicEndpoints is " + str(x.publicEndpoints))
    service1 = client.reload(service1)
    assert service1.publicEndpoints is not None
    assert len(service1.publicEndpoints) == 6

    exposedPorts = []
    for i in range(0, 2):
        port = service1.launchConfig["ports"][0]
        exposedPort = int(port[0:port.index(":")])
        exposedPorts.append(exposedPort)
        assert exposedPort in range(65500, 65506)

    validate_exposed_port(client, service1, exposedPorts)

    delete_all(client, [env])


def test_environment_activate_deactivate_delete(client,
                                                socat_containers):

    launch_config = {"imageUuid": TEST_IMAGE_UUID}

    scale = 1

    service1, env = create_env_and_svc(client, launch_config,
                                       scale)

    service2 = create_svc(client, env, launch_config, scale)

    # Environment Activate Services
    env = env.activateservices()

    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    check_container_in_service(client, service1)

    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    check_container_in_service(client, service2)

    # Environment Deactivate Services
    env = env.deactivateservices()

    wait_until_instances_get_stopped(client, service1)
    wait_until_instances_get_stopped(client, service2)

    service1 = client.wait_success(service1, 300)
    assert service1.state == "inactive"
    check_stopped_container_in_service(client, service1)

    service2 = client.wait_success(service2, 300)
    assert service2.state == "inactive"
    check_stopped_container_in_service(client, service2)

    # Environment Activate Services
    env = env.activateservices()

    service1 = client.wait_success(service1, 300)
    assert service1.state == "active"
    check_container_in_service(client, service1)

    service2 = client.wait_success(service2, 300)
    assert service2.state == "active"
    check_container_in_service(client, service2)

    # Delete Environment
    env = client.wait_success(client.delete(env))
    assert env.state == "removed"

    # Deleting service results in instances of the service to be "removed".
    # instance continues to be part of service , until the instance is purged.

    check_for_deleted_service(client, env, service1)
    check_for_deleted_service(client, env, service2)

    delete_all(client, [env])


def test_service_activate_deactivate_delete(client,
                                            socat_containers):

    launch_config = {"imageUuid": TEST_IMAGE_UUID}

    scale = 2

    service, env = create_env_and_svc(client, launch_config,
                                      scale)
    # Activate Services
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(client, service)

    # Deactivate Services
    service = service.deactivate()
    service = client.wait_success(service, 300)
    assert service.state == "inactive"
    wait_until_instances_get_stopped(client, service)
    check_stopped_container_in_service(client, service)

    # Activate Services
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(client, service)

    # Delete Service
    service = client.wait_success(client.delete(service))
    assert service.state == "removed"

    check_for_deleted_service(client, env, service)

    delete_all(client, [env])


def test_service_activate_stop_instance(
        client, socat_containers):

    service = shared_env[0]["service"]
    check_for_service_reconciliation_on_stop(client, service)


def test_service_activate_delete_instance(
        client, socat_containers):

    service = shared_env[0]["service"]
    check_for_service_reconciliation_on_delete(client, service)


def test_service_activate_purge_instance(
        client, socat_containers):

    service = shared_env[0]["service"]

    # Purge 2 instances
    containers = get_service_container_list(client, service)
    container1 = containers[0]
    container1 = client.wait_success(client.delete(container1))
    container1 = client.wait_success(container1.purge())
    container2 = containers[1]
    container2 = client.wait_success(client.delete(container2))
    container2 = client.wait_success(container2.purge())

    wait_for_scale_to_adjust(client, service)

    check_container_in_service(client, service)


@pytest.mark.skipif(
    True, reason="Skip since there is no support for restore from v1.6.0")
def test_service_activate_restore_instance(
        client, socat_containers):

    service = shared_env[0]["service"]

    # Restore 2 instances
    containers = get_service_container_list(client, service)
    container1 = containers[0]
    container1 = client.wait_success(client.delete(container1))
    container1 = client.wait_success(container1.restore())
    container2 = containers[1]
    container2 = client.wait_success(client.delete(container2))
    container2 = client.wait_success(container2.restore())

    assert container1.state == "stopped"
    assert container2.state == "stopped"

    wait_for_scale_to_adjust(client, service)

    check_container_in_service(client, service)
    delete_all(client, [container1, container2])


def test_service_scale_up(client, socat_containers):
    check_service_scale(client, socat_containers, 2, 4)


def test_service_scale_down(client, socat_containers):
    check_service_scale(client, socat_containers, 4, 2, 2)


@if_ontag
def test_service_activate_stop_instance_scale_up(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 3, 4, [1])


def test_service_activate_delete_instance_scale_up(
        client, socat_containers):
    check_service_activate_delete_instance_scale(
        client, socat_containers, 3, 4, [1])


def test_service_activate_stop_instance_scale_down(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 4, 1, [1], 3)


def test_service_activate_delete_instance_scale_down(
        client, socat_containers):
    check_service_activate_delete_instance_scale(
        client, socat_containers, 4, 1, [1], 3)


@if_ontag
def test_service_activate_stop_instance_scale_up_1(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 3, 4, [3])


def test_service_activate_delete_instance_scale_up_1(
        client, socat_containers):
    check_service_activate_delete_instance_scale(
        client, socat_containers, 3, 4, [3])


def test_service_activate_stop_instance_scale_down_1(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 4, 1, [4], 3)


def test_service_activate_delete_instance_scale_down_1(
        client, socat_containers):
    check_service_activate_delete_instance_scale(client,
                                                 socat_containers,
                                                 4, 1, [4], 3)


@if_ontag
def test_service_activate_stop_instance_scale_up_2(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 3, 4, [1, 2, 3])


def test_service_activate_delete_instance_scale_up_2(
        client, socat_containers):
    check_service_activate_delete_instance_scale(
        client, socat_containers, 3, 4, [1, 2, 3])


def test_service_activate_stop_instance_scale_down_2(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 4, 1, [1, 2, 3, 4], 3)


def test_service_activate_delete_instance_scale_down_2(
        client, socat_containers):
    check_service_activate_delete_instance_scale(
        client, socat_containers, 4, 1, [1, 2, 3, 4])


@if_ontag
def test_service_activate_stop_instance_scale_up_3(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 3, 4, [2])


def test_service_activate_delete_instance_scale_up_3(
        client, socat_containers):
    check_service_activate_delete_instance_scale(
        client, socat_containers, 3, 4, [2])


def test_service_activate_stop_instance_scale_down_3(
        client, socat_containers):
    check_service_activate_stop_instance_scale(
        client, socat_containers, 4, 1, [2], 3)


def test_service_activate_delete_instance_scale_down_3(
        client, socat_containers):
    check_service_activate_delete_instance_scale(
        client, socat_containers, 4, 1, [2], 3)


def test_services_hostname_override_1(client, socat_containers):

    host_name = "test"
    domain_name = "abc.com"

    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "domainName": domain_name,
                     "hostname": host_name,
                     "labels":
                         {"io.rancher.container.hostname_override":
                          "container_name"}
                     }

    scale = 2

    service, env = create_env_and_svc(client, launch_config,
                                      scale)

    env = env.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(client, service)

    container_list = get_service_container_list(client, service)
    assert len(container_list) == service.scale
    print container_list
    for c in container_list:
        docker_client = get_docker_client(c.hosts[0])
        inspect = docker_client.inspect_container(c.externalId)

        assert inspect["Config"]["Hostname"] == c.name

    delete_all(client, [env])


def test_services_hostname_override_2(client, socat_containers):

    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "labels":
                         {"io.rancher.container.hostname_override":
                          "container_name"}
                     }

    scale = 2

    service, env = create_env_and_svc(client, launch_config,
                                      scale)

    env = env.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(client, service)

    container_list = get_service_container_list(client, service)
    assert len(container_list) == service.scale
    for c in container_list:
        docker_client = get_docker_client(c.hosts[0])
        inspect = docker_client.inspect_container(c.externalId)

        assert inspect["Config"]["Hostname"] == c.name

    delete_all(client, [env])


def test_service_reconcile_stop_instance_restart_policy_always(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "always"}}
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)
    check_for_service_reconciliation_on_stop(client, service)
    delete_all(client, [env])


def test_service_reconcile_delete_instance_restart_policy_always(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "always"}}
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)
    check_for_service_reconciliation_on_delete(client, service)
    delete_all(client, [env])


def test_service_reconcile_delete_instance_restart_policy_no(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "labels": {"io.rancher.container.start_once": True}
                     }
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)
    check_for_service_reconciliation_on_delete(client, service)
    delete_all(client, [env])


def test_service_reconcile_stop_instance_restart_policy_no(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "labels": {"io.rancher.container.start_once": True}}
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)

    # Stop 2 containers of the service
    assert service.scale > 1
    containers = get_service_container_list(client, service)
    assert len(containers) == service.scale
    assert service.scale > 1
    container1 = containers[0]
    stop_container_from_host(client, container1)
    container2 = containers[1]
    stop_container_from_host(client, container2)

    service = wait_state(client, service, "active")
    time.sleep(30)
    assert service.state == "active"

    # Make sure that the containers continue to remain in "stopped" state
    container1 = client.reload(container1)
    container2 = client.reload(container2)
    assert container1.state == 'stopped'
    assert container2.state == 'stopped'
    delete_all(client, [env])


def test_service_reconcile_stop_instance_restart_policy_failure(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "on-failure"}
                     }
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)
    check_for_service_reconciliation_on_stop(client, service)
    delete_all(client, [env])


def test_service_reconcile_delete_instance_restart_policy_failure(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "on-failure"}
                     }
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)
    check_for_service_reconciliation_on_delete(client, service)
    delete_all(client, [env])


def test_service_reconcile_stop_instance_restart_policy_failure_count(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"maximumRetryCount": 5,
                                       "name": "on-failure"}
                     }
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)
    check_for_service_reconciliation_on_stop(client, service)
    delete_all(client, [env])


def test_service_reconcile_delete_instance_restart_policy_failure_count(
        client, socat_containers):
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"maximumRetryCount": 5,
                                       "name": "on-failure"}
                     }
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale)
    check_for_service_reconciliation_on_delete(client, service)
    delete_all(client, [env])


def test_service_with_healthcheck(client, socat_containers):
    scale = 3
    env, service = service_with_healthcheck_enabled(
        client, scale)
    delete_all(client, [env])


def test_service_with_healthcheck_none(client, socat_containers):
    scale = 3
    env, service = service_with_healthcheck_enabled(
        client, scale, strategy="none")
    delete_all(client, [env])


def test_service_with_healthcheck_recreate(
        client, socat_containers):
    scale = 10
    env, service = service_with_healthcheck_enabled(
        client, scale, strategy="recreate")
    delete_all(client, [env])


def test_service_with_healthcheck_recreateOnQuorum(
        client, socat_containers):
    scale = 10
    env, service = service_with_healthcheck_enabled(
        client, scale, strategy="recreateOnQuorum", qcount=5)
    delete_all(client, [env])


def test_service_with_healthcheck_container_unhealthy(
        client, socat_containers):
    scale = 2
    port = 9998

    env, service = service_with_healthcheck_enabled(client,
                                                    scale, port)

    # Delete requestUrl from one of the containers to trigger health check
    # failure and service reconcile
    container_list = get_service_container_list(client, service)
    con = container_list[1]
    mark_container_unhealthy(client, con, port)

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
    wait_for_scale_to_adjust(client, service)
    con = client.reload(con)
    assert con.state in ('removed', 'purged')

    container_list = get_service_container_list(client, service)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)
    delete_all(client, [env])


def test_service_with_healthcheck_container_unhealthy_retainip(
        client, socat_containers):
    scale = 2
    port = 799

    env, service = service_with_healthcheck_enabled(client,
                                                    scale, port,
                                                    retainIp=True)

    # Delete requestUrl from one of the containers to trigger health check
    # failure and service reconcile
    container_list = get_service_container_list(client, service)
    con = container_list[1]
    con_name = con.name
    external_id = con.externalId
    ipAddress = con.primaryIpAddress
    mark_container_unhealthy(client, con, port)

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
    wait_for_scale_to_adjust(client, service)
    con = client.reload(con)
    assert con.state in ('removed', 'purged')

    container_list = get_service_container_list(client, service)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)

    # Make sure that the new container that was created has the same ip as the
    # Unhealthy container

    containers = client.list_container(name=con_name,
                                       removed_null=True)
    assert len(containers) == 1
    container = containers[0]
    assert container.state == 'running'

    new_ipAddress = container.primaryIpAddress
    new_externalId = container.externalId

    assert ipAddress == new_ipAddress
    assert external_id != new_externalId

    delete_all(client, [env])


def test_service_with_healthcheck_none_container_unhealthy(
        client, socat_containers):
    scale = 3
    port = 800

    env, service = service_with_healthcheck_enabled(client,
                                                    scale, port,
                                                    strategy="none")

    # Delete requestUrl from one of the containers to trigger health check
    # failure and service reconcile
    container_list = get_service_container_list(client, service)
    con1 = container_list[1]
    mark_container_unhealthy(client, con1, port)

    # Validate that the container is marked unhealthy
    wait_for_condition(
        client, con1,
        lambda x: x.healthState == 'unhealthy',
        lambda x: 'State is: ' + x.healthState)
    con1 = client.reload(con1)
    assert con1.healthState == "unhealthy"

    # Make sure that the container continues to be marked unhealthy
    # and is in "Running" state

    time.sleep(10)
    con1 = client.reload(con1)
    assert con1.healthState == "unhealthy"
    assert con1.state == "running"

    mark_container_healthy(client, container_list[1], port)
    # Make sure that the container gets marked healthy

    wait_for_condition(
        client, con1,
        lambda x: x.healthState == 'healthy',
        lambda x: 'State is: ' + x.healthState)
    con1 = client.reload(con1)
    assert con1.healthState == "healthy"
    assert con1.state == "running"

    delete_all(client, [env])


def test_service_with_healthcheck_none_container_unhealthy_delete(
        client, socat_containers):
    scale = 3
    port = 801

    env, service = service_with_healthcheck_enabled(client,
                                                    scale, port,
                                                    strategy="none")

    # Delete requestUrl from containers to trigger health check
    # failure and service reconcile
    container_list = get_service_container_list(client, service)
    unhealthy_containers = [container_list[0],
                            container_list[1]]

    for con in unhealthy_containers:
        mark_container_unhealthy(client, con, port)

    # Validate that the container is marked unhealthy
    for con in unhealthy_containers:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'unhealthy',
            lambda x: 'State is: ' + x.healthState)
        con = client.reload(con)
        assert con.healthState == "unhealthy"

    # Make sure that the container continues to be marked unhealthy
    # and is in "Running" state

    time.sleep(10)
    for con in unhealthy_containers:
        con = client.reload(con)
        assert con.healthState == "unhealthy"
        assert con.state == "running"

    # Delete 2 containers that are unhealthy
    for con in unhealthy_containers:
        container = client.wait_success(client.delete(con))
        assert container.state == 'removed'

    # Validate that the service reconciles on deletion of unhealthy containers
    wait_for_scale_to_adjust(client, service)
    check_container_in_service(client, service)

    # Validate that all containers of the service get to "healthy" state
    container_list = get_service_container_list(client, service)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)
    delete_all(client, [env])


def test_service_with_healthcheck_quorum_containers_unhealthy_1(
        client, socat_containers):
    scale = 2
    port = 802

    env, service = service_with_healthcheck_enabled(
        client, scale, port, strategy="recreateOnQuorum",
        qcount=1)

    # Make 1 container unhealthy , so there is 1 container that is healthy
    container_list = get_service_container_list(client, service)
    con1 = container_list[1]
    mark_container_unhealthy(client, con1, port)

    # Validate that the container is marked unhealthy
    wait_for_condition(
        client, con1,
        lambda x: x.healthState == 'unhealthy',
        lambda x: 'State is: ' + x.healthState)
    con1 = client.reload(con1)
    assert con1.healthState == "unhealthy"

    # Validate that the containers get removed
    wait_for_condition(
        client, con1,
        lambda x: x.state in ('removed', 'purged'),
        lambda x: 'State is: ' + x.healthState)
    wait_for_scale_to_adjust(client, service)
    con = client.reload(con1)
    assert con.state in ('removed', 'purged')

    # Validate that the service reconciles
    container_list = get_service_container_list(client, service)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)
    delete_all(client, [env])


@pytest.mark.skipif(True, reason="Known issue - #5411")
def test_service_with_healthcheck_quorum_container_unhealthy_2(
        client, socat_containers):
    scale = 3
    port = 803

    env, service = service_with_healthcheck_enabled(
        client, scale, port, strategy="recreateOnQuorum",
        qcount=2)

    # Make 2 containers unhealthy , so 1 container is healthy state
    container_list = get_service_container_list(client, service)

    unhealthy_containers = [container_list[1],
                            container_list[2]]

    for con in unhealthy_containers:
        mark_container_unhealthy(client, con, port)

    # Validate that the container is marked unhealthy
    for con in unhealthy_containers:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'unhealthy',
            lambda x: 'State is: ' + x.healthState)
        con = client.reload(con)
        assert con.healthState == "unhealthy"

    # Make sure that the container continues to be marked unhealthy
    # and is in "Running" state
    time.sleep(10)
    for con in unhealthy_containers:
        con = client.reload(con)
        assert con.healthState == "unhealthy"
        assert con.state == "running"

    delete_all(client, [env])


def test_dns_service_with_healthcheck_none_container_unhealthy(
        client, socat_containers):

    scale = 3
    port = 804
    cport = 805

    # Create HealthCheck enabled Service
    env, service = service_with_healthcheck_enabled(client,
                                                    scale, port,
                                                    strategy="none")
    # Create Client Service for DNS access check
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [str(cport)+":22/tcp"]}
    random_name = random_str()
    service_name = random_name.replace("-", "")
    client_service = client.create_service(name=service_name,
                                           stackId=env.id,
                                           launchConfig=launch_config_svc,
                                           scale=1)
    client_service = client.wait_success(client_service)
    assert client_service.state == "inactive"
    client_service = client.wait_success(client_service.activate())
    assert client_service.state == "active"

    # Check for DNS resolution
    validate_linked_service(client, client_service, [service], cport)

    # Delete requestUrl from one of the containers to trigger health check
    # failure and service reconcile
    container_list = get_service_container_list(client, service)
    con1 = container_list[1]
    mark_container_unhealthy(client, con1, port)

    # Validate that the container is marked unhealthy
    wait_for_condition(
        client, con1,
        lambda x: x.healthState == 'unhealthy',
        lambda x: 'State is: ' + x.healthState)
    con1 = client.reload(con1)
    assert con1.healthState == "unhealthy"

    # Check for DNS resolution
    validate_linked_service(client, client_service, [service],
                            cport, exclude_instance=con1)

    # Make sure that the container continues to be marked unhealthy
    # and is in "Running" state

    time.sleep(10)
    con1 = client.reload(con1)
    assert con1.healthState == "unhealthy"
    assert con1.state == "running"

    mark_container_healthy(client, container_list[1], port)

    # Make sure that the container gets marked healthy

    wait_for_condition(
        client, con1,
        lambda x: x.healthState == 'healthy',
        lambda x: 'State is: ' + x.healthState)
    con1 = client.reload(con1)
    assert con1.healthState == "healthy"
    assert con1.state == "running"

    # Check for DNS resolution
    validate_linked_service(client, client_service, [service], cport)

    delete_all(client, [env])


def test_service_health_check_scale_up(client, socat_containers):

    scale = 1
    final_scale = 3
    env, service = service_with_healthcheck_enabled(
        client, scale)
    # Scale service
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale
    check_container_in_service(client, service)
    check_for_healthstate(client, service)
    delete_all(client, [env])


def test_service_health_check_reconcile_on_stop(
        client, socat_containers):
    scale = 3
    env, service = service_with_healthcheck_enabled(
        client, scale)
    check_for_service_reconciliation_on_stop(client, service)
    check_for_healthstate(client, service)
    delete_all(client, [env])


def test_service_health_check_reconcile_on_delete(
        client, socat_containers):
    scale = 3
    env, service = service_with_healthcheck_enabled(
        client, scale)
    check_for_service_reconciliation_on_delete(client, service)
    check_for_healthstate(client, service)
    delete_all(client, [env])


def test_service_health_check_with_tcp(
        client, socat_containers):
    scale = 3
    env, service = service_with_healthcheck_enabled(
        client, scale, protocol="tcp")
    delete_all(client, [env])


def test_service_with_healthcheck_container_tcp_unhealthy(
        client, socat_containers):
    scale = 2
    port = 9997

    env, service = service_with_healthcheck_enabled(
        client, scale, port, protocol="tcp")

    # Stop ssh service from one of the containers to trigger health check
    # failure and service reconcile
    container_list = get_service_container_list(client, service)
    con = container_list[1]
    con_host = client.by_id('host', con.hosts[0].id)
    hostIpAddress = con_host.ipAddresses()[0].address

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostIpAddress, username="root",
                password="root", port=port)
    cmd = "service ssh stop"
    logger.info(cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)

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
    wait_for_scale_to_adjust(client, service)
    con = client.reload(con)
    assert con.state in ('removed', 'purged')

    container_list = get_service_container_list(client, service)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)
    delete_all(client, [env])


@pytest.mark.skipif(True,
                    reason='Service names not editable from 1.6 release')
def test_service_name_unique(client):
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, 1)
    service_name = service.name

    # Should not be allowed to create service with name when service name is
    # already used by a service in the same stack
    with pytest.raises(ApiError) as e:
        service = client.wait_success(client.create_service(name=service_name,
                                      stackId=env.id,
                                      launchConfig=launch_config,
                                      scale=1))
    assert e.value.error.status == 422
    assert e.value.error.code == 'NotUnique'
    assert e.value.error.fieldName == "name"
    delete_all(client, [env])


def test_service_name_unique_create_after_delete(client):
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, 1)
    service_name = service.name
    # Should be allowed to create service with name when service name is
    # used by service which is already deleted in the same stack
    client.wait_success(client.delete(service))
    service = client.wait_success(client.create_service(name=service_name,
                                  stackId=env.id,
                                  launchConfig=launch_config,
                                  scale=1))
    assert service.state == "inactive"
    delete_all(client, [env])


def test_service_name_unique_edit(client):
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, 1)
    service_name = service.name

    # Should not be allowed to edit existing service and set its name
    # to a service name that already exist in the same stack
    service = client.wait_success(client.create_service(name=random_str(),
                                  stackId=env.id,
                                  launchConfig=launch_config,
                                  scale=1))
    with pytest.raises(ApiError) as e:
        service = client.wait_success(client.update(service, name=service_name,
                                                    scale=1))
    assert e.value.error.status == 422
    assert e.value.error.code == 'NotUnique'
    assert e.value.error.fieldName == "name"
    delete_all(client, [env])


def test_service_retain_ip(client):
    launch_config = {"imageUuid": SSH_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, 3, retainIp=True)
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    container_name = get_container_name(env, service, "1")
    containers = client.list_container(name=container_name,
                                       removed_null=True)
    assert len(containers) == 1
    container = containers[0]
    ipAddress = container.primaryIpAddress
    externalId = container.externalId

    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'
    wait_for_scale_to_adjust(client, service)

    container_name = get_container_name(env, service, 1)
    containers = client.list_container(name=container_name,
                                       removed_null=True)
    assert len(containers) == 1
    container = containers[0]
    assert container.state == 'running'
    new_ipAddress = container.primaryIpAddress
    new_externalId = container.externalId

    assert ipAddress == new_ipAddress
    assert externalId != new_externalId


def test_services_rolling_strategy(client,
                                   socat_containers):
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     }
    service, env = create_env_and_svc(client, launch_config, 5)

    env = env.activateservices()
    service = client.wait_success(service, 300)
    container_list = get_service_container_list(client, service)
    assert len(container_list) == 5
    for con in container_list:
        assert con.state == "running"
        assert con.startCount == 1

    # Specify rolling restart strategy with batchsize 2 and interval of 1000 ms
    rollingrestartstrategy = {"batchSize": 2,
                              "intervalMillis": 1000
                              }
    service = client.wait_success(service.restart(
        rollingRestartStrategy=rollingrestartstrategy))

    assert service.state == "active"
    check_container_in_service(client, service)
    container_list = get_service_container_list(client, service)
    assert len(container_list) == 5
    for con in container_list:
        assert con.state == "running"
        assert con.startCount == 2

    env = client.reload(env)
    assert env.healthState == "healthy"
    delete_all(client, [env])


def test_service_reconcile_on_stop_exposed_port(client,
                                                socat_containers):
    port = "45"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [port+":22/tcp"]}
    service, env = create_env_and_svc(client, launch_config, scale=3)
    env = env.activateservices()
    env = client.wait_success(env, SERVICE_WAIT_TIMEOUT)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    check_for_service_reconciliation_on_stop(client, service)
    delete_all(client, [env])


def test_service_reconcile_on_restart_exposed_port(client,
                                                   socat_containers):
    port = "46"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [port+":22/tcp"]}
    service, env = create_env_and_svc(client, launch_config, scale=3)
    env = env.activateservices()
    env = client.wait_success(env, SERVICE_WAIT_TIMEOUT)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    check_for_service_reconciliation_on_restart(client, service)
    delete_all(client, [env])


def test_service_reconcile_on_delete_exposed_port(client,
                                                  socat_containers):
    port = "47"
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [port+":22/tcp"]}
    service, env = create_env_and_svc(client, launch_config, scale=3)
    env = env.activateservices()
    env = client.wait_success(env, SERVICE_WAIT_TIMEOUT)
    service = client.wait_success(service, SERVICE_WAIT_TIMEOUT)
    check_for_service_reconciliation_on_delete(client, service)
    delete_all(client, [env])


def test_insvc_upgrade_start_first(client, socat_containers):
    service_scale = 1
    lb_scale = 1
    port = "7890"
    # Create a target service for LB service
    env, service, lb_service = \
        create_environment_with_balancer_services(
            client, service_scale, lb_scale, port)
    validate_lb_service(client, lb_service, port, [service])
    # Upgrade the target service to invalid imageuuid so that service is
    # stuck in upgrading state
    inServiceStrategy = {}
    inServiceStrategy["launchConfig"] = {"imageUuid": WEB_IMAGE_UUID + "abc",
                                         'labels': {'foo': "bar"}}
    inServiceStrategy["batchSize"] = 3,
    inServiceStrategy["intervalMillis"] = 100,
    inServiceStrategy["startFirst"] = True
    service = service.upgrade_action(inServiceStrategy=inServiceStrategy)
    assert service.state == "upgrading"

    # Assert that the service is stuck in "upgrading" state
    # because of invalid image id
    time.sleep(10)
    assert service.state == "upgrading"
    validate_lb_service(client, lb_service, port, [service])


@if_container_refactoring
def test_global_service(client):
    min_scale = 2
    max_scale = 4
    increment = 2
    env, service = create_global_service(client, min_scale, max_scale,
                                         increment, host_label=None)
    containers = get_service_container_list(client, service)
    assert len(containers) == 2
    delete_all(client, [env])


def check_service_scale(client, socat_containers,
                        initial_scale, final_scale,
                        removed_instance_count=0):

    service, env = create_env_and_svc_activate(client,
                                               initial_scale)

    container_list = check_container_in_service(client, service)
    # Scale service
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale

    updated_container_list = check_container_in_service(client, service)
    removed_container_list = []

    for con in container_list:
        removed = True
        for updated_con in updated_container_list:
            if (con.id == updated_con.id):
                removed = False
                break
        if removed:
            removed_container_list.append(con)

    # Check for destroyed containers in case of scale down
    if final_scale < initial_scale:
        check_container_removed_from_service(client, service,
                                             removed_container_list)
    delete_all(client, [env])


def check_service_activate_stop_instance_scale(client,
                                               socat_containers,
                                               initial_scale, final_scale,
                                               stop_instance_index,
                                               removed_instance_count=0):

    service, env = create_env_and_svc_activate(client,
                                               initial_scale)
    container_list = check_container_in_service(client, service)
    # Stop instance
    for i in stop_instance_index:
        container_name = get_container_name(env, service, str(i))
        containers = client.list_container(name=container_name,
                                           include="hosts")
        assert len(containers) == 1
        container = containers[0]
        stop_container_from_host(client, container)

    service = wait_state(client, service, "active")

    logger.info("service being updated - " + service.name + " - " + service.id)
    # Scale service
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale
    logger.info("Scaled service - " + str(final_scale))

    updated_container_list = check_container_in_service(client, service)
    removed_container_list = []

    for con in container_list:
        removed = True
        for updated_con in updated_container_list:
            if (con.id == updated_con.id):
                removed = False
                break
        if removed:
            removed_container_list.append(con)

    # Check for destroyed containers in case of scale down
    if final_scale < initial_scale and removed_instance_count > 0:
        check_container_removed_from_service(client, service,
                                             removed_container_list)
    delete_all(client, [env])


def check_service_activate_delete_instance_scale(client,
                                                 socat_containers,
                                                 initial_scale, final_scale,
                                                 delete_instance_index,
                                                 removed_instance_count=0):

    service, env = create_env_and_svc_activate(client,
                                               initial_scale)

    # Delete instance
    for i in delete_instance_index:
        container_name = get_container_name(env, service, str(i))
        container_name = get_container_name(env, service, str(i))
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]
        container = client.wait_success(client.delete(container))
        assert container.state == 'removed'
        logger.info("Delete Container -" + container_name)

    service = wait_state(client, service, "active")

    logger.info("service being updated " + service.name + " - " + service.id)
    # Scale service
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale
    logger.info("Scaled service - " + str(final_scale))

    check_container_in_service(client, service)
    """
    # Check for destroyed containers in case of scale down
    if final_scale < initial_scale and removed_instance_count > 0:
        if removed_instance_count is not None:
            check_container_removed_from_service(client, service,
                                                 removed_instance_count)
    """
    delete_all(client, [env])


def _validate_add_service_link(service, client, scale):
    service_maps = client. \
        list_serviceExposeMap(serviceId=service.id)
    assert len(service_maps) == scale
    service_map = service_maps[0]
    wait_for_condition(
        client, service_map,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state)


def check_stopped_container_in_service(client, service):

    container_list = get_service_container_list(client, service)

    assert len(container_list) == service.scale

    for container in container_list:
        assert container.state == "stopped"
        containers = client.list_container(
            externalId=container.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(container.externalId)
        logger.info("Checked for container stopped - " + container.name)
        assert inspect["State"]["Running"] is False


def check_container_removed_from_service(client, service,
                                         removed_container_list):
    instance_maps = client.list_serviceExposeMap(serviceId=service.id)
    assert len(instance_maps) == service.scale

    for container in removed_container_list:
        wait_for_condition(
            client, container,
            lambda x: x.state == "removed" or x.state == "purged",
            lambda x: 'State is: ' + x.state)
        if container.state == "removed":
            containers = client.list_container(name=container.name,
                                               include="hosts")
            assert len(containers) == 1
            docker_client = get_docker_client(containers[0].hosts[0])
            inspect = docker_client.inspect_container(container.externalId)
            logger.info("Checked for containers removed from service - " +
                        container.name)
            assert inspect["State"]["Running"] is False


def check_for_deleted_service(client, env, service):

    service_maps = client.list_serviceExposeMap(serviceId=service.id)

    for service_map in service_maps:
        wait_for_condition(
            client, service_map,
            lambda x: x.state == "removed",
            lambda x: 'State is: ' + x.state)
        container = client.by_id('container', service_map.instanceId)
        wait_for_condition(
            client, container,
            lambda x: x.state == "purged",
            lambda x: 'State is: ' + x.state,
            timeout=600)
        logger.info("Checked for purged container - " + container.name)


def check_service_map(client, service, instance, state):
    instance_service_map = client.\
        list_serviceExposeMap(serviceId=service.id, instanceId=instance.id)
    assert len(instance_service_map) == 1
    assert instance_service_map[0].state == state


def check_for_service_reconciliation_on_stop(client, service,
                                             stopFromRancher=False,
                                             shouldRestart=True):
    # Stop 2 containers of the service
    assert service.scale > 1
    containers = get_service_container_list(client, service)
    assert len(containers) == service.scale
    assert service.scale > 1
    container1 = containers[0]
    container2 = containers[1]
    if not stopFromRancher:
        stop_container_from_host(client, container1)
        stop_container_from_host(client, container2)
    else:
        client.wait_success(container1.stop(), 120)
        client.wait_success(container2.stop(), 120)
    service = wait_state(client, service, "active")

    wait_for_scale_to_adjust(client, service)

    check_container_in_service(client, service)
    container1 = client.reload(container1)
    container2 = client.reload(container2)
    if shouldRestart:
        assert container1.state == 'running'
        assert container2.state == 'running'
    else:
        assert container1.state == 'stopped'
        assert container2.state == 'stopped'


def check_for_service_reconciliation_on_restart(client, service):
    # Stop 2 containers of the service
    assert service.scale > 1
    containers = get_service_container_list(client, service)
    assert len(containers) == service.scale
    assert service.scale > 1
    container1 = containers[0]
    container1 = client.wait_success(container1.restart())
    container2 = containers[1]
    container2 = client.wait_success(container2.restart())

    service = wait_state(client, service, "active")

    wait_for_scale_to_adjust(client, service)

    check_container_in_service(client, service)
    container1 = client.reload(container1)
    container2 = client.reload(container2)
    assert container1.state == 'running'
    assert container2.state == 'running'


def check_for_service_reconciliation_on_delete(client, service):
    # Delete 2 containers of the service
    containers = get_service_container_list(client, service)
    container1 = containers[0]
    container1 = client.wait_success(client.delete(container1))
    container2 = containers[1]
    container2 = client.wait_success(client.delete(container2))

    assert container1.state == 'removed'
    assert container2.state == 'removed'

    wait_for_scale_to_adjust(client, service)

    check_container_in_service(client, service)


def service_with_healthcheck_enabled(client, scale, port=None,
                                     protocol="http", labels=None,
                                     strategy=None, qcount=None,
                                     retainIp=False):
    health_check = {"name": "check1", "responseTimeout": 2000,
                    "interval": 2000, "healthyThreshold": 2,
                    "unhealthyThreshold": 3}
    launch_config = {"imageUuid": HEALTH_CHECK_IMAGE_UUID,
                     "healthCheck": health_check
                     }

    if protocol == "http":
        health_check["requestLine"] = "GET /name.html HTTP/1.0"
        health_check["port"] = 80

    if protocol == "tcp":
        health_check["requestLine"] = ""
        health_check["port"] = 22

    if strategy is not None:
        health_check["strategy"] = strategy
        if strategy == "recreateOnQuorum":
            health_check['recreateOnQuorumStrategyConfig'] = {"quorum": qcount}
    if port is not None:
        launch_config["ports"] = [str(port)+":22/tcp"]
    if labels is not None:
        launch_config["labels"] = labels
    service, env = create_env_and_svc_activate_launch_config(
        client, launch_config, scale, retainIp=retainIp)
    container_list = get_service_container_list(client, service)
    assert \
        len(container_list) == get_service_instance_count(client, service)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)
    return env, service


def check_for_healthstate(client, service):
    container_list = get_service_container_list(client, service)
    for con in container_list:
        wait_for_condition(
            client, con,
            lambda x: x.healthState == 'healthy',
            lambda x: 'State is: ' + x.healthState)
