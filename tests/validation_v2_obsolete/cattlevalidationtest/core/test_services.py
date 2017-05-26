from common_fixtures import *  # NOQA

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST

LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"

docker_config_running = [{"docker_param_name": "State.Running",
                          "docker_param_value": "true"}]

docker_config_stopped = [{"docker_param_name": "State.Running",
                          "docker_param_value": "false"}]

total_time = [0]
shared_env = []


# @pytest.fixture(scope='session', autouse=True)
def create_env_for_activate_deactivate(testname, request, client,
                                       super_client):
    service, env = create_env_and_svc_activate(testname, super_client, client,
                                               3, False)
    shared_env.append({"service": service,
                       "env": env})

    def fin():
        to_delete = [env]
        delete_all(client, to_delete)

    request.addfinalizer(fin)


def deactivate_activate_service(super_client, client, service):

    # Deactivate service
    service = service.deactivate()
    service = client.wait_success(service, 300)
    assert service.state == "inactive"
    # Activate Service
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    return service


def create_env_and_svc_activate(testname, super_client, client, scale,
                                check=True):
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service, env = create_env_and_svc_activate_launch_config(
        testname, super_client, client, launch_config, scale, check)
    return service, env


def create_env_and_svc_activate_launch_config(
        testname, super_client, client, launch_config, scale, check=True):
    start_time = time.time()
    service, env = create_env_and_svc(testname, client, launch_config, scale)
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    if check:
        check_container_in_service(super_client, service)
    time_taken = time.time() - start_time
    total_time[0] = total_time[0] + time_taken
    logger.info("time taken - " + str(time_taken))
    logger.info("total time taken - " + str(total_time[0]))
    return service, env


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServicesDockerOptions:

    testname = "TestServicesDockerOptions"
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
    scale = 2
    volume_in_host = "/test/container"
    volume_in_container = "/test/vol1"
    launch_config = {"imageUuid": TEST_SERVICE_OPT_IMAGE_UUID,
                     "command": command,
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
                     }

    @pytest.mark.create
    def test_services_docker_options_create(self, client, socat_containers):

        hosts = client.list_host(kind='docker', removed_null=True,
                                 state="active")
        logger.info("hosts is: %s", format(hosts))
        con_host = hosts[0]
        logger.info("con_host is: %s", format(con_host))
        vol_container = client.create_container(imageUuid=TEST_IMAGE_UUID,
                                                name=random_str(),
                                                requestedHostId=con_host.id
                                                )
        vol_container = client.wait_success(vol_container)
        docker_vol_value = self.volume_in_host + ":" + \
            self.volume_in_container + ":ro"
        launch_config = self.launch_config
        logger.info("launch_config is: %s", format(launch_config))
        launch_config.update({"dataVolumes": [docker_vol_value],
                              "dataVolumesFrom": [vol_container.id],
                              "requestedHostId": con_host.id})
        logger.info("launch_config after update is: %s", format(launch_config))

        service, env = create_env_and_svc(self.testname, client,
                                          self.launch_config,
                                          self.scale)

        env = env.activateservices()
        logger.info("env is: %s", format(env))

        service = client.wait_success(service, 300)
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        data = [env.uuid, service.uuid, vol_container.uuid, launch_config]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_services_docker_options_validate(self, super_client, client,
                                              socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        assert service.state == "active"
        check_container_in_service(super_client, service)
        vol_container = client.list_container(uuid=data[2])
        logger.info("vol_container is: %s", format(vol_container))
        launch_config = service.launchConfig
        logger.info("launch_config is: %s", format(launch_config))

        container_list = get_service_container_list(super_client, service)
        for c in container_list:
            logger.info("container is: %s", format(c))
            logger.info("container's host is: %s", c.hosts()[0])
            docker_client = get_docker_client(c.hosts()[0])
            logger.info("docker client is: %s", docker_client)
            logger.info("container's externalId is: %s", c.externalId)
            inspect = docker_client.inspect_container(c.externalId)
            logger.info("inspect is: %s", inspect)
            assert inspect["HostConfig"]["Binds"] == \
                launch_config["dataVolumes"]
            assert inspect["HostConfig"]["PublishAllPorts"] is False
            assert inspect["HostConfig"]["Privileged"] is True
            assert inspect["Config"]["OpenStdin"] is True
            assert inspect["Config"]["Tty"] is True
            assert inspect["HostConfig"]["Dns"] == launch_config['dns']
            assert inspect["HostConfig"]["DnsSearch"] == \
                launch_config['dnsSearch']
            assert inspect["Config"]["Hostname"] == launch_config['hostname']
            assert inspect["Config"]["Domainname"] == \
                launch_config['domainName']
            assert inspect["Config"]["User"] == launch_config['user']
            assert inspect["HostConfig"]["CapAdd"] == launch_config['capAdd']
            assert inspect["HostConfig"]["CapDrop"] == launch_config['capDrop']
            assert inspect["Config"]["Cpuset"] == launch_config['cpuSet']
            assert inspect["HostConfig"]["RestartPolicy"]["Name"] == \
                launch_config['restartPolicy']['name']
            assert inspect["HostConfig"]["RestartPolicy"]["MaximumRetryCount"]\
                == launch_config['restartPolicy']['maximumRetryCount']
            assert inspect["Config"]["Cmd"] == launch_config['command']
            assert inspect["Config"]["Memory"] == launch_config['memory']
            assert "TEST_FILE=/etc/testpath.conf" in inspect["Config"]["Env"]
            assert inspect["Config"]["CpuShares"] == launch_config['cpuShares']

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServicesPortAndLinkOptions:

    testname = "TestServicesPortAndLinkOptions"
    link_name = "WEB1"
    link_port = 80
    exposed_port = 9999

    @pytest.mark.create
    def test_services_port_and_link_options_create(self, super_client, client,
                                                   socat_containers):

        hosts = client.list_host(kind='docker', removed_null=True,
                                 state="active")
        host = hosts[0]
        link_host = hosts[1]
        link_container = client.create_container(
            imageUuid=LB_IMAGE_UUID,
            environment={'CONTAINER_NAME': self.link_name},
            name=random_str(),
            requestedHostId=host.id
            )

        link_container = client.wait_success(link_container)

        launch_config = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [str(self.exposed_port)+":22/tcp"],
                         "instanceLinks": {
                             self.link_name:
                                 link_container.id},
                         "requestedHostId": link_host.id,
                         }

        service, env = create_env_and_svc(self.testname, client,
                                          launch_config, 1)

        env = env.activateservices()
        service = client.wait_success(service, 300)

        container_name = env.name + "_" + service.name + "_1"
        containers = client.list_container(name=container_name,
                                           state="running")
        assert len(containers) == 1
        con = containers[0]
        logger.info("con: %s", con)

        data = [env.uuid, service.uuid, con.name]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_services_port_and_link_options_validate(self, super_client,
                                                     client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        con = client.list_container(name=data[2])[0]
        assert len(con) > 0
        logger.info("con is: %s", format(con))

        validate_exposed_port_and_container_link(super_client, con,
                                                 self.link_name,
                                                 self.link_port,
                                                 self.exposed_port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestEnvironmentActivateDeactivateDelete:

    testname = "TestEnvironmentActivateDeactivateDelete"
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    scale = 1

    @pytest.mark.create
    def test_environment_activate_deactivate_delete_create(self, super_client,
                                                           client,
                                                           socat_containers):

        service1, env = create_env_and_svc(self.testname, client,
                                           self.launch_config,
                                           self.scale)
        service2 = create_svc(client, env, self.launch_config, self.scale)

        # Environment Activate Services
        env = env.activateservices()

        service1 = client.wait_success(service1, 300)
        assert service1.state == "active"
        check_container_in_service(super_client, service1)

        service2 = client.wait_success(service2, 300)
        assert service2.state == "active"
        check_container_in_service(super_client, service2)

        data = [env.uuid, service1.uuid, service2.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_environment_activate_deactivate_delete_validate(self,
                                                             super_client,
                                                             client,
                                                             socat_containers):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service1 = client.list_service(uuid=data[1])[0]
        assert len(service1) > 0
        logger.info("service is: %s", format(service1))
        assert service1.state == "active"

        service2 = client.list_service(uuid=data[2])[0]
        assert len(service2) > 0
        logger.info("service is: %s", format(service2))
        assert service2.state == "active"

        # Environment Deactivate Services
        env = env.deactivateservices()

        wait_until_instances_get_stopped(super_client, service1)
        wait_until_instances_get_stopped(super_client, service2)

        service1 = client.wait_success(service1, 300)
        assert service1.state == "inactive"
        check_stopped_container_in_service(super_client, service1)

        service2 = client.wait_success(service2, 300)
        assert service2.state == "inactive"
        check_stopped_container_in_service(super_client, service2)

        # Environment Activate Services
        env = env.activateservices()

        service1 = client.wait_success(service1, 300)
        assert service1.state == "active"
        check_container_in_service(super_client, service1)

        service2 = client.wait_success(service2, 300)
        assert service2.state == "active"
        check_container_in_service(super_client, service2)

        # Delete Environment
        env = client.wait_success(client.delete(env))
        assert env.state == "removed"

        # Deleting service results in instances of the service to be "removed".
        # instance continues to be part of service
        # until the instance is purged.

        check_for_deleted_service(super_client, env, service1)
        check_for_deleted_service(super_client, env, service2)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiveActivateDeactivateDelete:

    testname = "TestServiveActivateDeactivateDelete"
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    scale = 2

    @pytest.mark.create
    def test_service_activate_deactivate_delete_create(self, super_client,
                                                       client,
                                                       socat_containers):

        service, env = create_env_and_svc(self.testname, client,
                                          self.launch_config,
                                          self.scale)
        # Activate Services
        service = service.activate()
        service = client.wait_success(service, 300)
        assert service.state == "active"

        check_container_in_service(super_client, service)

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_service_activate_deactivate_delete_validate(self, super_client,
                                                         client,
                                                         socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Deactivate Services
        service = service.deactivate()
        service = client.wait_success(service, 300)
        assert service.state == "inactive"
        wait_until_instances_get_stopped(super_client, service)
        check_stopped_container_in_service(super_client, service)

        # Activate Services
        service = service.activate()
        service = client.wait_success(service, 300)
        assert service.state == "active"

        check_container_in_service(super_client, service)

        # Delete Service
        service = client.wait_success(client.delete(service))
        assert service.state == "removed"

        check_for_deleted_service(super_client, env, service)

        delete_all(client, [env])


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestServiceActivateStopInstance:

    testname = "TestServiceActivateStopInstance"

    def test_service_activate_stop_instance_create(
            self, super_client, client, socat_containers):

        service = shared_env[0]["service"]
        env = shared_env[1]["env"]

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    def test_service_activate_stop_instance_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        assert service.state == "active"
        check_for_service_reconciliation_on_stop(super_client, client, service)

        delete_all(client, [env])


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestServiceActivateDeleteInstance:

    def test_service_activate_delete_instance_create(
            self, super_client, client, socat_containers):

        service = shared_env[0]["service"]
        env = shared_env[1]["env"]

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    def test_service_activate_delete_instance_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        assert service.state == "active"
        check_for_service_reconciliation_on_delete(super_client, client,
                                                   service)

        delete_all(client, [env])


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestServiceActivatePurgeInstance:

    def test_service_activate_purge_instance(
            self, super_client, client, socat_containers):

        service = shared_env[0]["service"]

        # Purge 2 instances
        containers = get_service_container_list(super_client, service)
        container1 = containers[0]
        container1 = client.wait_success(client.delete(container1))
        container1 = client.wait_success(container1.purge())
        container2 = containers[1]
        container2 = client.wait_success(client.delete(container2))
        container2 = client.wait_success(container2.purge())

        wait_for_scale_to_adjust(super_client, service)

        check_container_in_service(super_client, service)


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestServiveActivateRestoreInstance:

    def test_service_activate_restore_instance(
            self, super_client, client, socat_containers):

        service = shared_env[0]["service"]

        # Restore 2 instances
        containers = get_service_container_list(super_client, service)
        container1 = containers[0]
        container1 = client.wait_success(client.delete(container1))
        container1 = client.wait_success(container1.restore())
        container2 = containers[1]
        container2 = client.wait_success(client.delete(container2))
        container2 = client.wait_success(container2.restore())

        assert container1.state == "stopped"
        assert container2.state == "stopped"

        wait_for_scale_to_adjust(super_client, service)

        check_container_in_service(super_client, service)


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceScaleUp:

    testname = "TestServiceScaleUp"
    initial_scale = 2
    final_scale = 4
    removed_instance_count = 0

    @pytest.mark.create
    def test_service_scale_up_create(self, super_client, client,
                                     socat_containers):
        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_scale_up_validate(self, super_client, client,
                                       socat_containers):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"
        assert service.scale == self.final_scale

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceScaleDown:

    testname = "TestServiceScaleDown"
    initial_scale = 4
    final_scale = 2
    removed_instance_count = 2

    @pytest.mark.create
    def test_service_scale_down_create(self, super_client, client,
                                       socat_containers):
        service, env = create_env_and_svc_activate(self.testname, super_client,
                                                   client,
                                                   self.initial_scale)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_scale_down_validate(self, super_client, client,
                                         socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"
        assert service.scale == self.final_scale

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateDeleteInstanceScaleUp:

    testname = "TestServiceActivateDeleteInstanceScaleUp"
    initial_scale = 3
    final_scale = 4
    delete_instance_index = [1]

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_up_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client,
                                                   client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_up_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"
        assert service.scale == self.initial_scale

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
         """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateStopInstanceScaleDown:

    testname = "TestServiceActivateStopInstanceScaleDown"
    initial_scale = 3
    final_scale = 4
    delete_instance_index = [1]

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_down_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client,
                                                   client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_down_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"
        assert service.scale == self.initial_scale

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
         """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateDeleteInstanceScaleDown:

    testname = "TestServiceActivateDeleteInstanceScaleDown"
    initial_scale = 3
    final_scale = 4
    delete_instance_index = [1]

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_down_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_down_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"
        assert service.scale == self.initial_scale

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
         """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateStopInstanceScaleUp1:

    testname = "TestServiceActivateStopInstanceScaleUp1"
    initial_scale = 3
    final_scale = 4
    stop_instance_index = [1]
    removed_instance_count = 0

    @pytest.mark.create
    def test_service_activate_stop_instance_scale_up_1_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_svc_activate_stop_instance_scale_up_1_validate(self,
                                                            super_client,
                                                            client,
                                                            socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop instance
        for i in self.stop_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(container.stop(), 300)
            # assert container.state == 'stopped'
            logger.info("Stopped container - " + container_name)
            service = client.wait_success(service)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale and \
                self.removed_instance_count > 0:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateDeleteInstanceScaleUp1:

    testname = "TestServiceActivateDeleteInstanceScaleUp1"
    initial_scale = 3
    final_scale = 4
    delete_instance_index = [3]
    removed_instance_count = 0

    @pytest.mark.create
    def test_svc_activate_dlt_instance_scale_up_1_create(self,
                                                         super_client,
                                                         client,
                                                         socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_svc_activate_dlt_instance_scale_up_1_validate(self,
                                                           super_client,
                                                           client,
                                                           socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
        """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiveActivateStopInstanceScaleDown:

    testname = "TestServiveActivateStopInstanceScaleDown"
    initial_scale = 4
    final_scale = 1
    stop_instance_index = [4]
    removed_instance_count = 3

    @pytest.mark.create
    def test_service_activate_stop_instance_scale_down_1_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname, super_client,
                                                   client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_stop_instance_scale_down_1_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop instance
        for i in self.stop_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(container.stop(), 300)
            # assert container.state == 'stopped'
            logger.info("Stopped container - " + container_name)
            service = client.wait_success(service)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale and \
                self.removed_instance_count > 0:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateStopInstanceScaleUp2:

    testname = "TestServiceActivateStopInstanceScaleUp2"
    initial_scale = 3
    final_scale = 4
    stop_instance_index = [1, 2, 3]
    removed_instance_count = 0

    @pytest.mark.create
    def test_svc_activate_stop_instance_scale_up_2_create(self,
                                                          super_client,
                                                          client,
                                                          socat_containers):
        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_svc_activate_stop_instance_scale_up_2_validate(self,
                                                            super_client,
                                                            client,
                                                            socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop instance
        for i in self.stop_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(container.stop(), 300)
            # assert container.state == 'stopped'
            logger.info("Stopped container - " + container_name)
            service = client.wait_success(service)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale and \
                self.removed_instance_count > 0:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateDeleteInstanceScaleUp2:

    testname = "TestServiceActivateDeleteInstanceScaleUp2"
    initial_scale = 3
    final_scale = 4
    delete_instance_index = [1, 2, 3]
    removed_instance_count = 0

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_up_2_create(
            self, super_client, client, socat_containers):
        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client,
                                                   client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_up_2_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
        """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateStopInstanceScaleDown2:

    testname = "TestServiceActivateStopInstanceScaleDown2"
    initial_scale = 3
    final_scale = 4
    stop_instance_index = [1, 2, 3, 4]
    removed_instance_count = 3

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_up_2_create(
            self, super_client, client, socat_containers):
        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client,
                                                   client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_up_2_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop instance
        for i in self.stop_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(container.stop(), 300)
            # assert container.state == 'stopped'
            logger.info("Stopped container - " + container_name)
            service = client.wait_success(service)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale and \
                self.removed_instance_count > 0:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateDeleteInstanceScaleDown2:

    testname = "TestServiceActivateDeleteInstanceScaleDown2"
    initial_scale = 4
    final_scale = 1
    delete_instance_index = [1, 2, 3, 4]
    removed_instance_count = 0

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_down_2_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_down_2_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
        """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServivceActivateStopInstanceScaleUp3:

    testname = "TestServivceActivateStopInstanceScaleUp3"
    initial_scale = 3
    final_scale = 4
    stop_instance_index = [2]
    removed_instance_count = 0

    @pytest.mark.create
    def test_service_activate_stop_instance_scale_up_3_create(
            self, super_client, client, socat_containers):
        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client,
                                                   client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_stop_instance_scale_up_3_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop instance
        for i in self.stop_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(container.stop(), 300)
            # assert container.state == 'stopped'
            logger.info("Stopped container - " + container_name)
            service = client.wait_success(service)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale and \
                self.removed_instance_count > 0:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateDeleteInstanceScaleUp3:

    testname = "TestServiceActivateDeleteInstanceScaleUp3"
    initial_scale = 4
    final_scale = 1
    delete_instance_index = [1, 2, 3, 4]
    removed_instance_count = 0

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_down_2_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client,
                                                   client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_down_2_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
        """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceActivateDeleteInstanceScaleDown3:

    testname = "TestServiceActivateDeleteInstanceScaleDown3"
    initial_scale = 4
    final_scale = 1
    delete_instance_index = [2]
    removed_instance_count = 3

    @pytest.mark.create
    def test_service_activate_delete_instance_scale_down_2_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_delete_instance_scale_down_2_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete instance
        for i in self.delete_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(client.delete(container))
            assert container.state == 'removed'
            logger.info("Delete Container -" + container_name)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)
        """
        # Check for destroyed containers in case of scale down
        if final_scale < initial_scale and removed_instance_count > 0:
            if removed_instance_count is not None:
                check_container_removed_from_service(super_client, service,
                env, removed_instance_count)
        """

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiveActivateStopInstanceScaleDown3:

    testname = "TestServiveActivateStopInstanceScaleDown3"
    initial_scale = 4
    final_scale = 1
    stop_instance_index = [2]
    removed_instance_count = 3

    @pytest.mark.create
    def test_service_activate_stop_instance_scale_up_3_create(
            self, super_client, client, socat_containers):
        service, env = create_env_and_svc_activate(self.testname,
                                                   super_client, client,
                                                   self.initial_scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_activate_stop_instance_scale_up_3_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop instance
        for i in self.stop_instance_index:
            container_name = env.name + "_" + service.name + "_" + str(i)
            containers = client.list_container(name=container_name)
            assert len(containers) == 1
            container = containers[0]
            container = client.wait_success(container.stop(), 300)
            # assert container.state == 'stopped'
            logger.info("Stopped container - " + container_name)
            service = client.wait_success(service)

        # Scale service
        service = client.update(service, name=service.name,
                                scale=self.final_scale)
        service = client.wait_success(service, 300)
        assert service.state == "active"
        assert service.scale == self.final_scale
        logger.info("Scaled service - " + str(self.final_scale))

        check_container_in_service(super_client, service)

        # Check for destroyed containers in case of scale down
        if self.final_scale < self.initial_scale and \
                self.removed_instance_count > 0:
            check_container_removed_from_service(super_client, service, env,
                                                 self.removed_instance_count)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServicesHostnameOverride1:

    testname = "TestServicesHostnameOverride1"

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

    @pytest.mark.create
    def test_services_hostname_override_1_create(self, super_client,
                                                 client, socat_containers):

        service, env = create_env_and_svc(self.testname, client,
                                          self.launch_config,
                                          self.scale)

        env = env.activateservices()
        service = client.wait_success(service, 300)
        assert service.state == "active"

        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_services_hostname_override_1_validate(self, super_client, client,
                                                   socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        check_container_in_service(super_client, service)

        container_list = get_service_container_list(super_client, service)
        assert len(container_list) == service.scale
        print container_list
        for c in container_list:
            docker_client = get_docker_client(c.hosts()[0])
            inspect = docker_client.inspect_container(c.externalId)

            assert inspect["Config"]["Hostname"] == c.name

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServicesHostnameOverride2:

    testname = "TestServicesHostnameOverride2"
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "labels":
                         {"io.rancher.container.hostname_override":
                          "container_name"}
                     }
    scale = 2

    @pytest.mark.create
    def test_services_hostname_override_2_create(self, super_client, client,
                                                 socat_containers):
        service, env = create_env_and_svc(self.testname, client,
                                          self.launch_config,
                                          self.scale)

        env = env.activateservices()
        service = client.wait_success(service, 300)
        assert service.state == "active"
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_services_hostname_override_2_validate(self, super_client, client,
                                                   socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        check_container_in_service(super_client, service)

        container_list = get_service_container_list(super_client, service)
        assert len(container_list) == service.scale
        for c in container_list:
            docker_client = get_docker_client(c.hosts()[0])
            inspect = docker_client.inspect_container(c.externalId)

            assert inspect["Config"]["Hostname"] == c.name

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileStopInstanceRestartPolicyAlways:

    testname = "TestServiceReconcileStopInstanceRestartPolicyAlways"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "always"}}

    @pytest.mark.create
    def test_service_reconcile_stop_instance_restart_policy_always_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_reconcile_stop_instance_restart_policy_always_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        check_for_service_reconciliation_on_stop(super_client, client, service)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileDeleteInstanceRestartPolicyAlways:

    testname = "TestServiceReconcileDeleteInstanceRestartPolicyAlways"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "always"}}

    @pytest.mark.create
    def test_service_reconcile_delete_instance_restart_policy_always_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_reconcile_delete_instance_restart_policy_always_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete 2 containers of the service
        containers = get_service_container_list(super_client, service)
        container1 = containers[0]
        container1 = client.wait_success(client.delete(container1))
        container2 = containers[1]
        container2 = client.wait_success(client.delete(container2))

        assert container1.state == 'removed'
        assert container2.state == 'removed'

        wait_for_scale_to_adjust(super_client, service)

        check_container_in_service(super_client, service)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileStopInstanceRestartPolicyNo:

    testname = "TestServiceReconcileStopInstanceRestartPolicyNo"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "no"}}

    @pytest.mark.create
    def test_service_reconcile_stop_instance_restart_policy_no_create(
            self, super_client, client, socat_containers):
        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)

        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_reconcile_stop_instance_restart_policy_no_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileDeleteInstanceRestartPolicyNo:

    testname = "TestServiceReconcileDeleteInstanceRestartPolicyNo"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "no"}}

    @pytest.mark.create
    def test_service_reconcile_delete_instance_restart_policy_no_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_reconcile_delete_instance_restart_policy_no_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop 2 containers of the service
        assert service.scale > 1
        containers = get_service_container_list(super_client, service)
        assert len(containers) == service.scale
        assert service.scale > 1
        container1 = containers[0]
        container1 = client.wait_success(container1.stop())
        container2 = containers[1]
        container2 = client.wait_success(container2.stop())

        service = client.wait_success(service)
        time.sleep(30)
        assert service.state == "active"

        # Make sure that the containers continue to remain in "stopped" state
        container1 = client.reload(container1)
        container2 = client.reload(container2)
        assert container1.state == 'stopped'
        assert container2.state == 'stopped'

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileStopInstanceRestartPolicyFailure:

    testname = "TestServiceReconcileStopInstanceRestartPolicyFailure"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "on-failure"}}

    @pytest.mark.create
    def test_service_reconcile_stop_instance_restart_policy_failure_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_reconcile_stop_instance_restart_policy_failure_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop 2 containers of the service
        assert service.scale > 1
        containers = get_service_container_list(super_client, service)
        assert len(containers) == service.scale
        assert service.scale > 1
        container1 = containers[0]
        container1 = client.wait_success(container1.stop())
        container2 = containers[1]
        container2 = client.wait_success(container2.stop())

        service = client.wait_success(service)

        wait_for_scale_to_adjust(super_client, service)

        check_container_in_service(super_client, service)
        container1 = client.reload(container1)
        container2 = client.reload(container2)
        assert container1.state == 'running'
        assert container2.state == 'running'

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileDeleteInstanceRestartPolicyFailure:

    testname = "TestServiceReconcileDeleteInstanceRestartPolicyFailure"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"name": "on-failure"}
                     }

    @pytest.mark.create
    def test_service_reconcile_delete_instance_restart_policy_failure_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_service_reconcile_delete_instance_restart_policy_failure_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete 2 containers of the service
        containers = get_service_container_list(super_client, service)
        container1 = containers[0]
        container1 = client.wait_success(client.delete(container1))
        container2 = containers[1]
        container2 = client.wait_success(client.delete(container2))

        assert container1.state == 'removed'
        assert container2.state == 'removed'

        wait_for_scale_to_adjust(super_client, service)

        check_container_in_service(super_client, service)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileDeleteStopInstanceRestartPolicyFailureCount:

    testname = \
        "TestServiceReconcileDeleteStopInstanceRestartPolicyFailureCount"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"maximumRetryCount": 5,
                                       "name": "on-failure"}
                     }

    @pytest.mark.create
    def test_svc_reconcile_stop_instance_restart_policy_failure_count_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_svc_reconcile_stop_instance_restart_policy_failure_count_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Stop 2 containers of the service
        assert service.scale > 1
        containers = get_service_container_list(super_client, service)
        assert len(containers) == service.scale
        assert service.scale > 1
        container1 = containers[0]
        container1 = client.wait_success(container1.stop())
        container2 = containers[1]
        container2 = client.wait_success(container2.stop())

        service = client.wait_success(service)

        wait_for_scale_to_adjust(super_client, service)

        check_container_in_service(super_client, service)
        container1 = client.reload(container1)
        container2 = client.reload(container2)
        assert container1.state == 'running'
        assert container2.state == 'running'

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.Services
@pytest.mark.incremental
class TestServiceReconcileDeleteInstanceRestartPolicyFailureCount:

    testname = "TestServiceReconcileDeleteInstanceRestartPolicyFailureCount"
    scale = 3
    launch_config = {"imageUuid": TEST_IMAGE_UUID,
                     "restartPolicy": {"maximumRetryCount": 5,
                                       "name": "on-failure"}
                     }

    @pytest.mark.create
    def test_svc_reconcile_dlt_instance_restart_policy_failure_count_create(
            self, super_client, client, socat_containers):

        service, env = create_env_and_svc_activate_launch_config(
            self.testname, super_client, client, self.launch_config,
            self.scale)
        data_to_save = [env.uuid, service.uuid]
        save(data_to_save, self)

    @pytest.mark.validate
    def test_svc_reconcile_dlt_instance_restart_policy_failure_count_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        # Delete 2 containers of the service
        containers = get_service_container_list(super_client, service)
        container1 = containers[0]
        container1 = client.wait_success(client.delete(container1))
        container2 = containers[1]
        container2 = client.wait_success(client.delete(container2))

        assert container1.state == 'removed'
        assert container2.state == 'removed'

        wait_for_scale_to_adjust(super_client, service)

        check_container_in_service(super_client, service)

        delete_all(client, [env])


def check_service_scale(super_client, client, socat_containers,
                        initial_scale, final_scale,
                        removed_instance_count=0):

    service, env = create_env_and_svc_activate(super_client, client,
                                               initial_scale)

    # Scale service
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale

    check_container_in_service(super_client, service)

    # Check for destroyed containers in case of scale down
    if final_scale < initial_scale:
        check_container_removed_from_service(super_client, service, env,
                                             removed_instance_count)


def check_service_activate_stop_instance_scale(super_client, client,
                                               socat_containers,
                                               initial_scale, final_scale,
                                               stop_instance_index,
                                               removed_instance_count=0):

    service, env = create_env_and_svc_activate(super_client, client,
                                               initial_scale)

    # Stop instance
    for i in stop_instance_index:
        container_name = env.name + "_" + service.name + "_" + str(i)
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]
        container = client.wait_success(container.stop(), 300)
        # assert container.state == 'stopped'
        logger.info("Stopped container - " + container_name)
        service = client.wait_success(service)

    # Scale service
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale
    logger.info("Scaled service - " + str(final_scale))

    check_container_in_service(super_client, service)

    # Check for destroyed containers in case of scale down
    if final_scale < initial_scale and removed_instance_count > 0:
        check_container_removed_from_service(super_client, service, env,
                                             removed_instance_count)


def check_service_activate_delete_instance_scale(super_client, client,
                                                 socat_containers,
                                                 initial_scale, final_scale,
                                                 delete_instance_index,
                                                 removed_instance_count=0):

    service, env = create_env_and_svc_activate(super_client, client,
                                               initial_scale)

    # Delete instance
    for i in delete_instance_index:
        container_name = env.name + "_" + service.name + "_" + str(i)
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]
        container = client.wait_success(client.delete(container))
        assert container.state == 'removed'
        logger.info("Delete Container -" + container_name)

    # Scale service
    service = client.update(service, name=service.name, scale=final_scale)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == final_scale
    logger.info("Scaled service - " + str(final_scale))

    check_container_in_service(super_client, service)
    """
    # Check for destroyed containers in case of scale down
    if final_scale < initial_scale and removed_instance_count > 0:
        if removed_instance_count is not None:
            check_container_removed_from_service(super_client, service, env,
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


def check_stopped_container_in_service(super_client, service):

    container_list = get_service_container_list(super_client, service)

    assert len(container_list) == service.scale

    for container in container_list:
        assert container.state == "stopped"
        containers = super_client.list_container(
            externalId=container.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(container.externalId)
        logger.info("Checked for container stopped - " + container.name)
        assert inspect["State"]["Running"] is False


def check_container_removed_from_service(super_client, service, env,
                                         removed_count):
    container = []
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="removed")
    start = time.time()

    while len(instance_maps) != removed_count:
        time.sleep(5)
        instance_maps = super_client.list_serviceExposeMap(
            serviceId=service.id, state="removed")
        if time.time() - start > 30:
            raise Exception('Timed out waiting for Service Expose map to be ' +
                            'removed for scaled down instances')

    for instance_map in instance_maps:
        container = super_client.by_id('container', instance_map.instanceId)
        wait_for_condition(
            super_client, container,
            lambda x: x.state == "removed" or x.state == "purged",
            lambda x: 'State is: ' + x.state)
        if container.state == "removed":
            containers = super_client.list_container(name=container.name,
                                                     include="hosts")
            assert len(containers) == 1
            docker_client = get_docker_client(containers[0].hosts[0])
            inspect = docker_client.inspect_container(container.externalId)
            logger.info("Checked for containers removed from service - " +
                        container.name)
            assert inspect["State"]["Running"] is False


def check_for_deleted_service(super_client, env, service):

    service_maps = super_client.list_serviceExposeMap(serviceId=service.id)

    for service_map in service_maps:
        wait_for_condition(
            super_client, service_map,
            lambda x: x.state == "removed",
            lambda x: 'State is: ' + x.state)
        container = super_client.by_id('container', service_map.instanceId)
        wait_for_condition(
            super_client, container,
            lambda x: x.state == "purged",
            lambda x: 'State is: ' + x.state)
        logger.info("Checked for purged container - " + container.name)


def check_service_map(super_client, service, instance, state):
    instance_service_map = super_client.\
        list_serviceExposeMap(serviceId=service.id, instanceId=instance.id)
    assert len(instance_service_map) == 1
    assert instance_service_map[0].state == state


def get_service_container_list(super_client, service):

    container = []
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    start = time.time()

    while len(instance_maps) != service.scale:
        time.sleep(.5)
        instance_maps = super_client.list_serviceExposeMap(
            serviceId=service.id, state="active")
        if time.time() - start > 30:
            raise Exception('Timed out waiting for Service Expose map to be ' +
                            'created for all instances')

    for instance_map in instance_maps:
        logger.info(instance_map.instanceId + " - " + instance_map.serviceId)
        c = super_client.by_id('container', instance_map.instanceId)
        container.append(c)

    return container


def check_for_service_reconciliation_on_stop(super_client, client, service):
    # Stop 2 containers of the service
    assert service.scale > 1
    containers = get_service_container_list(super_client, service)
    assert len(containers) == service.scale
    assert service.scale > 1
    container1 = containers[0]
    container1 = client.wait_success(container1.stop())
    container2 = containers[1]
    container2 = client.wait_success(container2.stop())

    service = client.wait_success(service)

    wait_for_scale_to_adjust(super_client, service)

    check_container_in_service(super_client, service)
    container1 = client.reload(container1)
    container2 = client.reload(container2)
    assert container1.state == 'running'
    assert container2.state == 'running'


def check_for_service_reconciliation_on_delete(super_client, client, service):
    # Delete 2 containers of the service
    containers = get_service_container_list(super_client, service)
    container1 = containers[0]
    container1 = client.wait_success(client.delete(container1))
    container2 = containers[1]
    container2 = client.wait_success(client.delete(container2))

    assert container1.state == 'removed'
    assert container2.state == 'removed'

    wait_for_scale_to_adjust(super_client, service)

    check_container_in_service(super_client, service)
