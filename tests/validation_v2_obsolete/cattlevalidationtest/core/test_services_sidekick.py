from common_fixtures import *  # NOQA

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"


def create_env_with_sidekick(testname, client, service_scale, expose_port):
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
        env_with_sidekick_config(testname, client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service)

    return env, service, service_name, consumed_service_name


def validate_sidekick(super_client, primary_service, service_name,
                      consumed_service_name, exposed_port=None, dnsname=None):
    print "Validating service - " + service_name
    containers = get_service_containers_with_name(super_client,
                                                  primary_service,
                                                  service_name)
    assert len(containers) == primary_service.scale

    print "Validating Consumed Services: " + consumed_service_name
    consumed_containers = get_service_containers_with_name(
        super_client, primary_service, consumed_service_name)
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
            super_client, primary_service, consumed_service_name, label)
        sec_host = secondary_con.hosts[0].id
        print secondary_con.name + " - " + label + " - " + sec_host
        assert sec_host == pri_host

    if exposed_port is not None and dnsname is not None:
        # Check for DNS resolution
        secondary_con = get_service_containers_with_name(
            super_client, primary_service, consumed_service_name)
        validate_dns(super_client, containers, secondary_con, exposed_port,
                     dnsname)


def validate_dns(super_client, service_containers, consumed_service,
                 exposed_port, dnsname):
    time.sleep(5)

    for service_con in service_containers:
        host = super_client.by_id('host', service_con.hosts[0].id)

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


def create_env_with_multiple_sidekicks(testname, client, service_scale,
                                       expose_port):

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
    # random_name = random_str()
    # env_name = random_name.replace("-", "")
    env = client.create_environment(name=testname)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service1,
                                launch_config_consumed_service2]
    )

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name1 = \
        env.name + "_" + service.name + "_" + consumed_service_name1

    consumed_service_name2 = \
        env.name + "_" + service.name + "_" + consumed_service_name2

    service_name = env.name + "_" + service.name
    return env, service, service_name, \
        consumed_service_name1, consumed_service_name2


def env_with_sidekick_config(testname, client, service_scale,
                             launch_config_consumed_service,
                             launch_config_service):

    env = client.create_environment(name=testname)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")

    launch_config_consumed_service["name"] = consumed_service_name
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service])

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name = \
        env.name + "_" + service.name + "_" + consumed_service_name

    service_name = env.name + "_" + service.name
    return env, service, service_name, consumed_service_name


def create_env_with_sidekick_for_linking(testname, client, service_scale):
    launch_config_consumed_service = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": WEB_IMAGE_UUID}

    env, service, service_name, consumed_service_name = \
        env_with_sidekick_config(testname, client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service)

    return env, service, service_name, consumed_service_name


def create_env_with_sidekick_anti_affinity(testname, client, service_scale):
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
        env_with_sidekick_config(testname, client, service_scale,
                                 launch_config_consumed_service,
                                 launch_config_service)

    return env, service, service_name, consumed_service_name


def env_with_sidekick(testname, super_client, client, service_scale,
                      exposed_port):

    env, service, service_name, consumed_service_name = \
        create_env_with_sidekick(testname, client, service_scale, exposed_port)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"

    dnsname = service.secondaryLaunchConfigs[0].name

    validate_sidekick(super_client, service, service_name,
                      consumed_service_name, exposed_port, dnsname)

    return env, service, service_name, consumed_service_name


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSideKickActivateEnv:

    testname = "TestSideKickActivateEnv"
    exposed_port = "7000"
    service_scale = 2

    @pytest.mark.create
    def test_sidekick_activate_env_create(self, client, super_client):

        env, service, service_name, consumed_service_name = \
            create_env_with_sidekick(self.testname, client, self.service_scale,
                                     self.exposed_port)

        env = env.activateservices()
        env = client.wait_success(env, 120)
        assert env.state == "active"

        service = client.wait_success(service, 120)
        assert service.state == "active"

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_activate_env_validate(self, client, super_client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        logger.info("service_name is: %s", (service_name))

        consumed_service_name = data[3]
        logger.info("consumed service name is: %s",
                    (consumed_service_name))

        dnsname = data[4]
        logger.info("dns is: %s", (dnsname))

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestMultipleSidekickActivateService:

    testname = "TestMultipleSidekickActivateService"
    exposed_port = "7003"
    service_scale = 2

    @pytest.mark.create
    def test_multiple_sidekick_activate_service_create(self, client,
                                                       super_client):
        env, service, service_name, consumed_service1, consumed_service2 =\
            create_env_with_multiple_sidekicks(
                self.testname, client, self.service_scale, self.exposed_port)
        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"
        dnsname = service.secondaryLaunchConfigs[0].name
        data = [env.uuid, service.uuid, service_name, consumed_service1,
                consumed_service2, dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_multiple_sidekick_activate_service_validate(self, client,
                                                         super_client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        logger.info("service_name is: %s", (service_name))

        consumed_service1 = data[3]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 name is: %s", (consumed_service1))

        consumed_service2 = data[4]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", (consumed_service2))

        dnsname = data[5]
        logger.info("dns is: %s", (dnsname))

        validate_sidekick(super_client, service, service_name,
                          consumed_service1, self.exposed_port, dnsname)

        dnsname = service.secondaryLaunchConfigs[1].name
        validate_sidekick(super_client, service, service_name,
                          consumed_service2, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickActivateEnv:
    testname = "TestSidekickActivateEnv"
    exposed_port = "7000"
    service_scale = 2

    @pytest.mark.create
    def test_sidekick_activate_env_create(self, client, super_client):

        env, service, service_name, consumed_service_name = \
            create_env_with_sidekick(self.testname, client, self.service_scale,
                                     self.exposed_port)

        env = env.activateservices()
        env = client.wait_success(env, 120)
        assert env.state == "active"

        service = client.wait_success(service, 120)
        assert service.state == "active"
        dnsname = service.secondaryLaunchConfigs[0].name
        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_activate_env_validate(self, client, super_client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        logger.info("service_name is: %s", (service_name))

        consumed_service_name = data[3]
        logger.info("consumed_service_name is: %s",
                    (consumed_service_name))

        dnsname = data[4]
        logger.info("dns name : %s", (dnsname))

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekick:

    testname = "TestSidekick"
    service_scale = 2

    @pytest.mark.create
    def test_sidekick_create(self, client, super_client):

        env, service, service_name, consumed_service_name = \
            create_env_with_sidekick_for_linking(self.testname, client,
                                                 self.service_scale)
        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"
        data = [env.uuid, service.uuid, service_name, consumed_service_name]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_validate(self, client, super_client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        logger.info("service_name is: %s", (service_name))

        consumed_service_name = data[3]
        logger.info("consumed_service_name is: %s",
                    (consumed_service_name))

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickWithAntiAffinity:

    testname = "TestSidekickWithAntiAffinity"
    service_scale = 2

    @pytest.mark.create
    def test_sidekick_with_anti_affinity_create(self, client, super_client):
        env, service, service_name, consumed_service_name = \
            create_env_with_sidekick_anti_affinity(self.testname, client,
                                                   self.service_scale)
        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"
        data = [env.uuid, service.uuid, service_name, consumed_service_name]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_with_anti_affinity_validate(self, client, super_client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = client.list_service(uuid=data[2])
        logger.info("service_name is: %s", format(service_name))

        consumed_service_name = client.list_service(uuid=data[2])
        logger.info("consumed_service_name is: %s",
                    format(consumed_service_name))

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name)


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestServiceLinksToSidekick:

    testname = "TestServiceLinksToSidekick"
    service_scale = 2
    client_port = "7004"

    def test_service_links_to_sidekick_create(self, client, super_client):

        env, linked_service, linked_service_name, linked_consumed_service_name\
            = create_env_with_sidekick_for_linking(self.testname, client,
                                                   self.service_scale)

        launch_config = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [self.client_port+":22/tcp"]}

        service = create_svc(client, env, launch_config, 1)
        link_svc(super_client, service, [linked_service])

        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        service_containers = get_service_container_list(super_client, service)

        primary_consumed_service = get_service_containers_with_name(
            super_client, linked_service, linked_service_name)

        secondary_consumed_service = get_service_containers_with_name(
            super_client, linked_service, linked_consumed_service_name)

        dnsname = linked_service.name
        validate_dns(super_client, service_containers,
                     primary_consumed_service, self.client_port, dnsname)

        dnsname = \
            linked_service.secondaryLaunchConfigs[0].name + "." + \
            linked_service.name

        data = [env.uuid, linked_service.uuid, linked_service_name,
                linked_consumed_service_name,
                secondary_consumed_service.uuid, dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    def test_service_links_to_sidekick_validate(self, client, super_client):

        data = load(self)

        env = client.list_environment(uuid=data[0])
        logger.info("env is: %s", format(env))

        linked_service = client.list_service(uuid=data[1])
        assert len(linked_service) > 0
        linked_service = linked_service[0]
        logger.info("service is: %s", format(linked_service))

        linked_service_name = client.list_service(uuid=data[2])
        logger.info("service_name is: %s", format(linked_service_name))

        consumed_service_name = client.list_service(uuid=data[2])
        logger.info("consumed_service_name is: %s",
                    format(consumed_service_name))

        validate_dns(super_client, service_containers,
                     secondary_consumed_service, client_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickServiceScaleUp:

    testname = "TestSidekickServiceScaleUp"
    service_scale = 2
    exposed_port = "7005"
    final_service_scale = 3

    @pytest.mark.create
    def test_sidekick_service_scale_up_create(self, client, super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_service_scale_up_validate(self, client, super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickScaleDown:

    testname = "TestSidekickScaleDown"
    service_scale = 3
    exposed_port = "7006"
    final_service_scale = 2

    @pytest.mark.create
    def test_sidekick_scale_down_create(self, client, super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_scale_down_validate(self, client, super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickConsumedServicesStopStart:

    testname = "TestSidekickConsumedServicesStopStart"
    service_scale = 2
    exposed_port = "7007"

    @pytest.mark.create
    def test_sidekick_consumed_services_stop_start_instance(self, client,
                                                            super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        container_name = consumed_service_name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Stop instance
        container = client.wait_success(container.stop(), 120)
        client.wait_success(service)

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_consumed_services_stop_start_instance_validate(
            self, client, super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickConsumedServicesRestartInstance:

    testname = "TestSidekickConsumedServicesRestartInstance"
    service_scale = 2
    exposed_port = "7008"

    @pytest.mark.create
    def test_sidekick_consumed_services_restart_instance_create(self, client,
                                                                super_client):
        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        container_name = consumed_service_name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # restart instance
        container = client.wait_success(container.restart(), 120)
        assert container.state == 'running'

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_consumed_services_restart_instance_validate(
            self, client, super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestSidekickConsumedServicesDeleteInstance:

    testname = "TestSidekickConsumedServicesDeleteInstance"
    service_scale = 3
    exposed_port = "7009"

    def test_sidekick_consumed_services_delete_instance_create(self, client,
                                                               super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        container_name = consumed_service_name + "_1"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        print container_name
        primary_container = get_side_kick_container(
            super_client, container, service, service_name)
        print primary_container.name

        # Delete instance
        container = client.wait_success(client.delete(container))
        assert container.state == 'removed'

        client.wait_success(service)

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname, primary_container.name]
        logger.info("data to save: %s", data)
        save(data, self)

    def test_sidekick_consumed_services_delete_instance_validate(self, client,
                                                                 super_client):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)

        c = client.list_container(name=data[5])
        # Check that the consumed container is not recreated
        primary_container = client.reload(c)
        print primary_container.state
        assert primary_container.state == "running"


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickDeactivateActivateEnvironment:

    testname = "TestSidekickDeactivateActivateEnvironment"
    service_scale = 2
    exposed_port = "7010"

    @pytest.mark.create
    def test_sidekick_deactivate_activate_environment_create(self, client,
                                                             super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        env = env.deactivateservices()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"

        wait_until_instances_get_stopped_for_service_with_sec_launch_configs(
            super_client, service)

        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_deactivate_activate_environment_validate(self, client,
                                                               super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickServicesStopStartInstance:

    testname = "TestSidekickServicesStopStartInstance"
    service_scale = 2
    exposed_port = "7011"

    @pytest.mark.create
    def test_sidekick_services_stop_start_instance_create(self, client,
                                                          super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Stop instance
        container = client.wait_success(container.stop(), 120)
        client.wait_success(service)

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_services_stop_start_instance_validate(self, client,
                                                            super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickServicesRestartInstance:

    testname = "TestSidekickServicesRestartInstance"
    service_scale = 3
    exposed_port = "7012"

    @pytest.mark.create
    def test_sidekick_services_restart_instance_create(self, client,
                                                       super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # restart instance
        container = client.wait_success(container.restart(), 120)
        assert container.state == 'running'

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_services_restart_instance_validate(self, client,
                                                         super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port,
                          dnsname)


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestSidekickServicesDeleteInstance:

    testname = "TestSidekickServicesDeleteInstance"
    service_scale = 2
    exposed_port = "7013"

    def test_sidekick_services_delete_instance_create(self, client,
                                                      super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        container_name = env.name + "_" + service.name + "_1"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        print container_name
        consumed_container = get_side_kick_container(
            super_client, container, service, consumed_service_name)
        print consumed_container.name

        # Delete instance
        container = client.wait_success(client.delete(container))
        assert container.state == 'removed'

        client.wait_success(service)

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname, consumed_container.name]
        logger.info("data to save: %s", data)
        save(data, self)

    def test_sidekick_services_delete_instance_validate(self, client,
                                                        super_client):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]
        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port,
                          dnsname)

        c = client.list_container(name=data[4])
        # Check that the consumed container is not recreated
        consumed_container = client.reload(c)
        print consumed_container.state
        assert consumed_container.state == "running"


@pytest.mark.P0
@pytest.mark.Sidekick
@pytest.mark.incremental
class TestSidekickServicesDeactivateActivate:

    testname = "TestSidekickServicesDeactivateActivate"
    service_scale = 2
    exposed_port = "7014"

    @pytest.mark.create
    def test_sidekick_services_deactivate_activate_create(self, client,
                                                          super_client):

        env, service, service_name, consumed_service_name = \
            env_with_sidekick(self.testname, super_client, client,
                              self.service_scale,
                              self.exposed_port)

        service = service.deactivate()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"

        wait_until_instances_get_stopped_for_service_with_sec_launch_configs(
            super_client, service)

        service = service.activate()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        dnsname = service.secondaryLaunchConfigs[0].name

        data = [env.uuid, service.uuid, service_name, consumed_service_name,
                dnsname]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_sidekick_services_deactivate_activate_validate(self, client,
                                                            super_client):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        service_name = data[2]
        consumed_service_name = data[3]
        dnsname = data[4]

        validate_sidekick(super_client, service, service_name,
                          consumed_service_name, self.exposed_port, dnsname)
