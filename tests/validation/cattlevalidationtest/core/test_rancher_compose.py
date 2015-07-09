from common_fixtures import *  # NOQA

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST
LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"

logger = logging.getLogger(__name__)


def test_rancher_compose_service(super_client, client,
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
    launch_rancher_compose(client, env, "service_options")

    rancher_envs = client.list_environment(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_services = client.list_service(name=service.name,
                                           environmentId=rancher_env.id,
                                           removed_null=True)
    assert len(rancher_services) == 1
    rancher_service = rancher_services[0]
    assert rancher_service.scale == service.scale

    rancher_service = client.wait_success(rancher_service, 120)

    check_container_in_service(super_client, rancher_service)

    container_list = get_service_container_list(super_client, rancher_service)
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
        assert inspect["HostConfig"]["RestartPolicy"]["Name"] == \
            restart_policy["name"]
        assert inspect["HostConfig"]["RestartPolicy"]["MaximumRetryCount"] == \
            restart_policy["maximumRetryCount"]
        assert inspect["Config"]["Cmd"] == command
        assert inspect["Config"]["Memory"] == memory
        assert "TEST_FILE=/etc/testpath.conf" in inspect["Config"]["Env"]
        assert inspect["Config"]["CpuShares"] == cpu_shares
    delete_all(client, [env, rancher_env])


@pytest.mark.skipif(True, reason='not implemented yet')
def test_rancher_compose_services_port_and_link_options(
        super_client, client, rancher_compose_container, socat_containers):

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

    launch_rancher_compose(client, env, "service_link_port")

    rancher_envs = client.list_environment(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_services = client.list_service(name=service.name,
                                           environmentId=rancher_env.id,
                                           removed_null=True)
    assert len(rancher_services) == 1
    rancher_service = rancher_services[0]
    assert rancher_service.scale == service.scale

    rancher_service = client.wait_success(rancher_service, 120)

    container_name = rancher_env.name + "_" + rancher_service.name + "_1"
    containers = client.list_container(name=container_name, state="running")
    assert len(containers) == 1
    con = containers[0]

    validate_exposed_port_and_container_link(super_client, con, link_name,
                                             link_port, exposed_port)

    delete_all(client, [env, rancher_env, link_container])


def test_rancher_compose_lbservice(super_client, client,
                                   rancher_compose_container):

    port = "7900"

    # Add LB service and do not activate services
    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port)

    service_link = {"serviceId": service.id, "ports": ["80"]}
    lb_service.addservicelink(serviceLink=service_link)

    validate_add_service_link(super_client, lb_service, service)

    # Add another service link to the LB service
    launch_config = {"imageUuid": WEB_IMAGE_UUID}
    service_name = random_str()
    service1 = client.create_service(name=service_name,
                                     environmentId=env.id,
                                     launchConfig=launch_config,
                                     scale=2)
    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    service_link = {"serviceId": service1.id, "ports": ["80"]}
    lb_service.addservicelink(serviceLink=service_link)
    validate_add_service_link(super_client, lb_service, service1)

    launch_rancher_compose(client, env, "lb_service")

    rancher_envs = client.list_environment(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_services = client.list_service(name=service.name,
                                           environmentId=rancher_env.id,
                                           removed_null=True)
    assert len(rancher_services) == 1
    rancher_service = rancher_services[0]
    assert rancher_service.scale == service.scale

    rancher_services1 = client.list_service(name=service1.name,
                                            environmentId=rancher_env.id,
                                            removed_null=True)
    assert len(rancher_services1) == 1
    rancher_service1 = rancher_services1[0]
    assert rancher_service1.scale == service1.scale

    rancher_lb_services = client.list_service(name=lb_service.name,
                                              environmentId=rancher_env.id,
                                              removed_null=True)
    assert len(rancher_lb_services) == 1
    rancher_lb_service = rancher_lb_services[0]
    assert rancher_lb_service.scale == lb_service.scale

    client.wait_success(rancher_service)
    client.wait_success(rancher_service1)
    client.wait_success(rancher_lb_service)
    validate_add_service_link(
        super_client, rancher_lb_service, rancher_service)
    validate_add_service_link(
        super_client, rancher_lb_service, rancher_service1)

    validate_lb_service(super_client, client, rancher_env,
                        [rancher_service, rancher_service1],
                        rancher_lb_service, port)
    delete_all(client, [env, rancher_env])


def test_rancher_compose_service_links(super_client, client,
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

    launch_rancher_compose(client, env, "service_link")
    rancher_envs = client.list_environment(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_services = client.list_service(name=service.name,
                                           environmentId=rancher_env.id,
                                           removed_null=True)
    assert len(rancher_services) == 1
    rancher_service = rancher_services[0]
    assert rancher_service.scale == service.scale

    rancher_consumed_services = client.list_service(
        name=consumed_service.name, environmentId=rancher_env.id,
        removed_null=True)
    assert len(rancher_consumed_services) == 1
    rancher_consumed_service = rancher_consumed_services[0]
    assert rancher_service.scale == service.scale

    client.wait_success(rancher_service)
    client.wait_success(rancher_consumed_service)
    validate_add_service_link(super_client, rancher_service,
                              rancher_consumed_service)

    validate_linked_service(super_client, rancher_service,
                            [rancher_consumed_service], port)
    delete_all(client, [env, rancher_env])


def test_rancher_compose_dns_services(super_client, client,
                                      rancher_compose_container):

    port = "7902"

    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_env_with_2_svc_dns(
            client, service_scale, consumed_service_scale, port)

    service_link = {"serviceId": dns.id}
    service.addservicelink(serviceLink=service_link)

    service_link = {"serviceId": consumed_service.id}
    dns.addservicelink(serviceLink=service_link)

    service_link = {"serviceId": consumed_service1.id}
    dns.addservicelink(serviceLink=service_link)

#   Launch env using docker compose

    launch_rancher_compose(client, env, "service_dns")
    rancher_envs = client.list_environment(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_dnss = client.list_service(name=dns.name,
                                       environmentId=rancher_env.id,
                                       removed_null=True)
    assert len(rancher_dnss) == 1
    rancher_dns = rancher_dnss[0]

    rancher_services = client.list_service(name=service.name,
                                           environmentId=rancher_env.id,
                                           removed_null=True)
    assert len(rancher_services) == 1
    rancher_service = rancher_services[0]
    assert rancher_service.scale == service.scale

    rancher_consumed_services = client.list_service(
        name=consumed_service.name,
        environmentId=rancher_env.id,
        removed_null=True)
    assert len(rancher_consumed_services) == 1
    rancher_consumed_service = rancher_consumed_services[0]
    assert rancher_consumed_service.scale == consumed_service.scale

    rancher_consumed_services1 = client.list_service(
        name=consumed_service1.name,
        environmentId=rancher_env.id,
        removed_null=True)
    assert len(rancher_consumed_services1) == 1
    rancher_consumed_service1 = rancher_consumed_services1[0]
    assert rancher_consumed_service1.scale == consumed_service1.scale

    client.wait_success(rancher_dns)
    client.wait_success(rancher_consumed_service)
    client.wait_success(rancher_consumed_service1)
    client.wait_success(rancher_service)
    validate_add_service_link(super_client, rancher_service,
                              rancher_dns)
    validate_add_service_link(super_client, rancher_dns,
                              rancher_consumed_service)
    validate_add_service_link(super_client, rancher_dns,
                              rancher_consumed_service1)

    validate_dns_service(super_client, rancher_service,
                         [rancher_consumed_service, rancher_consumed_service1],
                         port, rancher_dns.name)
    delete_all(client, [env, rancher_env])


def test_rancher_compose_external_services(super_client, client,
                                           rancher_compose_container):

    port = "7903"

    service_scale = 1

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    service_link = {"serviceId": ext_service.id}
    service.addservicelink(serviceLink=service_link)

#   Launch env using docker compose

    launch_rancher_compose(client, env, "ext_service")
    rancher_envs = client.list_environment(name=env.name+"rancher")
    assert len(rancher_envs) == 1
    rancher_env = rancher_envs[0]

    rancher_services = client.list_service(name=service.name,
                                           environmentId=rancher_env.id,
                                           removed_null=True)
    assert len(rancher_services) == 1
    rancher_service = rancher_services[0]
    assert rancher_service.scale == service.scale

    rancher_ext_services = client.list_service(name=ext_service.name,
                                               environmentId=rancher_env.id,
                                               removed_null=True)
    assert len(rancher_ext_services) == 1
    rancher_ext_service = rancher_ext_services[0]

    client.wait_success(con_list[0])
    client.wait_success(con_list[1])
    client.wait_success(rancher_service)
    client.wait_success(rancher_ext_service)

    validate_add_service_link(super_client, rancher_service,
                              rancher_ext_service)

    validate_external_service(super_client, rancher_service,
                              [rancher_ext_service],
                              port, con_list)
    delete_all(client, [env, rancher_env])
