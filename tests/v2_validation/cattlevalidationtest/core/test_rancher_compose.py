from common_fixtures import *  # NOQA

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST
LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"

logger = logging.getLogger(__name__)

if_compose_data_files = pytest.mark.skipif(
    not os.environ.get('CATTLE_TEST_DATA_DIR'),
    reason='Docker compose files directory location not set')


def test_rancher_compose_service(admin_client, client,
                                 rancher_compose_container,
                                 socat_containers):

    vol_container = client.create_container(imageUuid=TEST_IMAGE_UUID,
                                            name=random_str(),
                                            labels={"c1": "vol"}
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
    # Not including "dataVolumesFrom": [vol_container.id] since it is not
    # implemented yet

    launch_config = {"imageUuid": TEST_SERVICE_OPT_IMAGE_UUID,
                     "command": command,
                     "dataVolumes": [docker_vol_value],
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
                     "labels":
                         {"io.rancher.scheduler.affinity:container_label":
                          "c1=vol"}
                     }

    scale = 1

    service, env = create_env_and_svc(client, launch_config,
                                      scale)
    launch_rancher_compose(client, env)

    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_service = get_rancher_compose_service(
        client, rancher_env.id, service)

    check_container_in_service(admin_client, rancher_service)

    container_list = get_service_container_list(admin_client, rancher_service)

    dns_name.append(RANCHER_DNS_SERVER)
    dns_search.append(rancher_env.name+"."+RANCHER_DNS_SEARCH)
    dns_search.append(
        rancher_service.name+"."+rancher_env.name+"."+RANCHER_DNS_SEARCH)
    dns_search.append(RANCHER_DNS_SEARCH)

    for c in container_list:
        print c
        docker_client = get_docker_client(c.hosts[0])
        inspect = docker_client.inspect_container(c.externalId)

        assert inspect["HostConfig"]["Binds"] == [docker_vol_value]
#        assert inspect["HostConfig"]["VolumesFrom"] == \
#            [vol_container.externalId]
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
#        assert inspect["Config"]["Cpuset"] == cpu_set
#       No support for restart
        assert inspect["HostConfig"]["RestartPolicy"]["Name"] == ""
        assert \
            inspect["HostConfig"]["RestartPolicy"]["MaximumRetryCount"] == 0
        assert inspect["Config"]["Cmd"] == command
        assert inspect["Config"]["Memory"] == memory
        assert "TEST_FILE=/etc/testpath.conf" in inspect["Config"]["Env"]
        assert inspect["Config"]["CpuShares"] == cpu_shares
    delete_all(client, [env, rancher_env])


def test_rancher_compose_service_option_2(admin_client, client,
                                          rancher_compose_container,
                                          socat_containers):
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    cpu_shares = 400
    ulimit = {"hard": 1024, "name": "cpu", "soft": 1024}
    ulimit_inspect = {"Hard": 1024, "Name": "cpu", "Soft": 1024}
    ipcMode = "host"
    sysctls = {"net.ipv4.ip_forward": "1"}
    dev_opts = {
        '/dev/sda': {
            'readIops': 2000,
            'writeIops': 3000
        },
        '/dev/null': {
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
    cgroup = "abc"
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
                     "cgroup": cgroup,
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

    launch_rancher_compose(client, env)

    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_service = get_rancher_compose_service(
        client, rancher_env.id, service)

    check_container_in_service(admin_client, rancher_service)

    container_list = get_service_container_list(admin_client, rancher_service)

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
        dev_opts_inspect["Path"] = "/dev/sda"
        dev_opts_inspect["Rate"] = 2000
        assert \
            inspect["HostConfig"]["BlkioDeviceReadIOps"] == [dev_opts_inspect]
        dev_opts_inspect["Path"] = "/dev/sda"
        dev_opts_inspect["Rate"] = 3000
        assert \
            inspect["HostConfig"]["BlkioDeviceWriteIOps"] == [dev_opts_inspect]
        assert inspect["Config"]["CpuShares"] == cpu_shares
        assert inspect["HostConfig"]["Cgroup"] == cgroup
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


@pytest.mark.skipif(True, reason='not implemented yet')
def test_rancher_compose_services_port_and_link_options(
        admin_client, client, rancher_compose_container, socat_containers):

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

    launch_rancher_compose(client, env)

    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_service = get_rancher_compose_service(
        client, rancher_env.id, service)

    container_name = get_container_name(rancher_env, rancher_service, 1)
    containers = client.list_container(name=container_name, state="running")
    assert len(containers) == 1
    con = containers[0]

    validate_exposed_port_and_container_link(admin_client, con, link_name,
                                             link_port, exposed_port)

    delete_all(client, [env, rancher_env, link_container])


def test_rancher_compose_lbservice(admin_client, client,
                                   rancher_compose_container):

    port = "7900"

    # Add LB service and do not activate services
    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    # Add another target to LB service
    launch_config = {"imageUuid": WEB_IMAGE_UUID}
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config,
                                     scale=2)
    service1 = client.wait_success(service1)
    assert service1.state == "inactive"
    service = activate_svc(client, service)
    service1 = activate_svc(client, service1)
    # Set LB targets
    port_rules = lb_service.lbConfig["portRules"]
    protocol = "http"
    target_port = "80"
    service_id = service1.id
    port_rule = {"sourcePort": port, "protocol": protocol,
                 "serviceId": service_id, "targetPort": target_port}
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))

    launch_rancher_compose(client, env)

    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_lb_service = get_rancher_compose_service(
        client, rancher_env.id, lb_service)

    client.wait_success(rancher_lb_service)

    validate_lb_service(admin_client, client, rancher_lb_service, port,
                        [service, service1])
    delete_all(client, [env, rancher_env])


def test_rancher_compose_lbservice_internal(admin_client, client,
                                            rancher_compose_container):

    port = "7911"
    con_port = "7912"

    # Deploy container in same network to test accessibility of internal LB
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    assert len(hosts) > 0
    host = hosts[0]
    client_con = client.create_container(
        name=random_str(), imageUuid=SSH_IMAGE_UUID,
        ports=[con_port+":22/tcp"], requestedHostId=host.id)
    client_con = client.wait_success(client_con, 120)
    assert client_con.state == "running"

    # Add an internal LB service and do not activate services
    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, internal=True)

    # Add another target to LB service
    launch_config = {"imageUuid": WEB_IMAGE_UUID}
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config,
                                     scale=2)
    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    service = activate_svc(client, service)
    service1 = activate_svc(client, service1)
    # Set LB targets
    port_rules = lb_service.lbConfig["portRules"]
    protocol = "http"
    target_port = "80"
    service_id = service1.id
    port_rule = {"sourcePort": port, "protocol": protocol,
                 "serviceId": service_id, "targetPort": target_port}
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))

    launch_rancher_compose(client, env)

    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_lb_service = get_rancher_compose_service(
        client, rancher_env.id, lb_service)

    client.wait_success(rancher_lb_service)
    validate_internal_lb(admin_client, rancher_lb_service,
                         [service, service1],
                         host, con_port, port)
    # Check that port in the host where LB Agent is running is not accessible
    lb_containers = get_service_container_list(
        admin_client, rancher_lb_service)
    assert len(lb_containers) == lb_service.scale
    for lb_con in lb_containers:
        host = admin_client.by_id('host', lb_con.hosts[0].id)
        assert check_for_no_access(host, port)

    delete_all(client, [env, rancher_env])


def test_rancher_compose_service_links(admin_client, client,
                                       rancher_compose_container):

    port = "7901"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service = create_env_with_2_svc(
        client, service_scale, consumed_service_scale, port)

    service_link = {"serviceId": consumed_service.id, "ports": ["80"]}
    service.addservicelink(serviceLink=service_link)

    service = client.wait_success(service, 120)

#   Launch env using docker compose

    launch_rancher_compose(client, env)
    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_service = get_rancher_compose_service(
        client, rancher_env.id, service)

    rancher_consumed_service = get_rancher_compose_service(
        client, rancher_env.id, consumed_service)

    client.wait_success(rancher_service)
    client.wait_success(rancher_consumed_service)
    validate_add_service_link(admin_client, rancher_service,
                              rancher_consumed_service)

    validate_linked_service(admin_client, rancher_service,
                            [rancher_consumed_service], port)
    delete_all(client, [env, rancher_env])


def test_rancher_compose_dns_services(admin_client, client,
                                      rancher_compose_container):
    port = "7902"
    rancher_compose_dns_services(admin_client, client, port,
                                 rancher_compose_container)


def test_rancher_compose_dns_services_cross_stack(admin_client, client,
                                                  rancher_compose_container):
    port = "7903"
    rancher_compose_dns_services(admin_client, client, port,
                                 rancher_compose_container, True)


def test_rancher_compose_external_services(admin_client, client,
                                           rancher_compose_container):

    port = "7904"

    service_scale = 1

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    service_link = {"serviceId": ext_service.id}
    service.addservicelink(serviceLink=service_link)

#   Launch env using docker compose

    launch_rancher_compose(client, env)
    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_service = get_rancher_compose_service(
        client, rancher_env.id, service)
    rancher_ext_service = get_rancher_compose_service(
        client, rancher_env.id, ext_service)

    client.wait_success(con_list[0])
    client.wait_success(con_list[1])
    client.wait_success(rancher_service)
    client.wait_success(rancher_ext_service)

    validate_add_service_link(admin_client, rancher_service,
                              rancher_ext_service)

    validate_external_service(admin_client, rancher_service,
                              [rancher_ext_service],
                              port, con_list)
    delete_all(client, [env, rancher_env])


def test_rancher_compose_lbservice_host_routing(admin_client, client,
                                                rancher_compose_container):

    port1 = "7906"
    service_scale = 2
    lb_scale = 1
    service_count = 3

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 0,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 1,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port1], service_count, port_rules)

    launch_rancher_compose(client, env)

    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_lb_service = get_rancher_compose_service(client, rancher_env.id,
                                                     lb_service)
    client.wait_success(rancher_lb_service)

    validate_lb_service(admin_client, client,
                        rancher_lb_service, port1, [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        rancher_lb_service, port1, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        rancher_lb_service, port1, [services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        rancher_lb_service, port1, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, rancher_lb_service, port1,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(admin_client, rancher_lb_service, port1,
                                      "www.abc2.com",
                                      "/service1.html")
    delete_all(client, [env, rancher_env])


def test_rancher_compose_lbservice_multiple_port(admin_client, client,
                                                 rancher_compose_container):

    port1 = "7907"
    port2 = "7908"
    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service3.html",
                 "serviceId": 1,
                 "sourcePort": port2,
                 "targetPort": "81",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port1, port2],
        service_count, port_rules)

    launch_rancher_compose(client, env)

    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_lb_service = get_rancher_compose_service(client, rancher_env.id,
                                                     lb_service)
    client.wait_success(rancher_lb_service)

    validate_lb_service(admin_client, client,
                        rancher_lb_service, port1, [services[0]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        rancher_lb_service, port2, [services[1]],
                        "www.abc2.com", "/service3.html")
    delete_all(client, [env, rancher_env])


def test_rancher_compose_external_services_hostname(admin_client, client,
                                                    rancher_compose_container):

    port = "7904"

    service_scale = 1

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port, True)

    service_link = {"serviceId": ext_service.id}
    service.addservicelink(serviceLink=service_link)

#   Launch env using docker compose

    launch_rancher_compose(client, env)
    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_service = get_rancher_compose_service(
        client, rancher_env.id, service)
    rancher_ext_service = get_rancher_compose_service(
        client, rancher_env.id, ext_service)

    client.wait_success(rancher_service)
    client.wait_success(rancher_ext_service)

    validate_add_service_link(admin_client, rancher_service,
                              rancher_ext_service)

    validate_external_service_for_hostname(admin_client, rancher_service,
                                           [rancher_ext_service], port)
    delete_all(client, [env, rancher_env])


def rancher_compose_dns_services(admin_client, client, port,
                                 rancher_compose_container,
                                 cross_linking=False):

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port, cross_linking)

    service_link = {"serviceId": dns.id}
    service.addservicelink(serviceLink=service_link)

    service_link = {"serviceId": consumed_service.id}
    dns.addservicelink(serviceLink=service_link)

    service_link = {"serviceId": consumed_service1.id}
    dns.addservicelink(serviceLink=service_link)

    # Launch dns env using docker compose
    launch_rancher_compose(client, env)
    rancher_envs = client.list_stack(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    # Launch envs using docker compose

    if cross_linking:
        # Launch Consumed Service2
        env_con = get_env(admin_client, consumed_service)
        env_con = env_con.activateservices()
        env_con = client.wait_success(env_con, 120)
        assert env_con.state == "active"
        con_service1_id = env_con.id
        # Launch Consumed Service1
        env_con1 = get_env(admin_client, consumed_service1)
        env_con1 = env_con1.activateservices()
        env_con1 = client.wait_success(env_con1, 120)
        assert env_con1.state == "active"
        con_service2_id = env_con1.id
    else:
        con_service1_id = rancher_env.id
        con_service2_id = rancher_env.id

    rancher_consumed_service = get_rancher_compose_service(
        client, con_service1_id, consumed_service)

    rancher_consumed_service1 = get_rancher_compose_service(
        client, con_service2_id, consumed_service1)

    rancher_dns = get_rancher_compose_service(
        client, rancher_env.id, dns)
    rancher_service = get_rancher_compose_service(
        client, rancher_env.id, service)

    client.wait_success(rancher_dns)
    client.wait_success(rancher_consumed_service)
    client.wait_success(rancher_consumed_service1)
    client.wait_success(rancher_service)
    validate_add_service_link(admin_client, rancher_service,
                              rancher_dns)
    validate_add_service_link(admin_client, rancher_dns,
                              rancher_consumed_service)
    validate_add_service_link(admin_client, rancher_dns,
                              rancher_consumed_service1)

    validate_dns_service(admin_client, rancher_service,
                         [rancher_consumed_service, rancher_consumed_service1],
                         port, rancher_dns.name)
    to_delete = [env, rancher_env]
    if cross_linking:
        to_delete.append(env_con)
        to_delete.append(env_con1)
    delete_all(client, to_delete)


def get_rancher_compose_service(client, rancher_env_id, service):
    rancher_services = client.list_service(name=service.name,
                                           stackId=rancher_env_id,
                                           removed_null=True)
    assert len(rancher_services) == 1
    rancher_service = rancher_services[0]
    print service.kind
    if service.kind != 'externalService' and service.kind != 'dnsService':
        assert rancher_service.scale == service.scale
    rancher_service = client.wait_success(rancher_service, 120)
    return rancher_service
