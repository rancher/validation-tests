from common_fixtures import *  # NOQA


def create_environment_with_dns_services(testname, super_client, client,
                                         service_scale,
                                         consumed_service_scale,
                                         port, cross_linking=False,
                                         isnetworkModeHost_svc=False,
                                         isnetworkModeHost_consumed_svc=False):
    if not isnetworkModeHost_svc and not isnetworkModeHost_consumed_svc:
        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns(
                testname, client, service_scale, consumed_service_scale, port,
                cross_linking)
    else:
        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns_hostnetwork(
                testname, client, service_scale, consumed_service_scale, port,
                cross_linking, isnetworkModeHost_svc,
                isnetworkModeHost_consumed_svc)
    service.activate()
    consumed_service.activate()
    consumed_service1.activate()
    dns.activate()

    service.addservicelink(serviceLink={"serviceId": dns.id})
    dns.addservicelink(serviceLink={"serviceId": consumed_service.id})
    dns.addservicelink(serviceLink={"serviceId": consumed_service1.id})

    service = client.wait_success(service, 120)
    consumed_service = client.wait_success(consumed_service, 120)
    consumed_service1 = client.wait_success(consumed_service1, 120)
    dns = client.wait_success(dns, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    assert consumed_service1.state == "active"
    assert dns.state == "active"

    validate_add_service_link(super_client, service, dns)
    validate_add_service_link(super_client, dns, consumed_service)
    validate_add_service_link(super_client, dns, consumed_service1)

    return env, service, consumed_service, consumed_service1, dns


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsSvcActivateDnsConsumedSvcLink:

    testname = "TestDnsSvcActivateDnsConsumedSvcLink"
    port = "31100"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_activate_svc_dns_consumed_svc_link_create(self, super_client,
                                                           client):
        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port)
        logger.info("env is : %s", env)
        logger.info("DNS service is: %s", dns)
        logger.info("DNS name is: %s", dns.name)
        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.name]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_activate_svc_dns_consumed_svc_link_validate(self,
                                                             super_client,
                                                             client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dnsname = data[4]
        logger.info("dns name is: %s", dnsname)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dnsname)

        delete_all(client, [env])


def test_dns_cross_link(super_client, client):

    port = "31101"
    testname = "TestDNSCrossLink"
    service_scale = 1
    consumed_service_scale = 2

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            testname, super_client, client, service_scale, consumed_service_scale,
            port, True)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name)

    delete_all(client, [env, get_env(super_client, consumed_service),
                        get_env(super_client, consumed_service1), dns])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsActivateConsumedSvcLinkActivateSvc:

    testname = "TestDnsActivateConsumedSvcLinkActivateSvc"
    port = "31102"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_activate_consumed_svc_link_activate_svc_create(
            self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns(
                self.testname, client, self.service_scale,
                self.consumed_service_scale,
                self.port)

        link_svc(super_client, service, [dns])
        link_svc(super_client, dns, [consumed_service, consumed_service1])
        service = activate_svc(client, service)
        consumed_service = activate_svc(client, consumed_service)
        consumed_service1 = activate_svc(client, consumed_service1)
        dns = activate_svc(client, dns)
        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.name]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_dns_activate_consumed_svc_link_activate_svc_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dnsname = data[4]
        logger.info("dns name is: %s", dnsname)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dnsname)

        delete_all(client, [env])


@pytest.mark.P1
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsActivateSvcLinkActivateConsumedSvc:

    testname = "TestDnsActivateSvcLinkActivateConsumedSvc"
    port = "31103"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_activate_svc_link_activate_consumed_svc_create(self,
                                                                super_client,
                                                                client):
        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns(
                self.testname, client, self.service_scale,
                self.consumed_service_scale,
                self.port)

        service = activate_svc(client, service)
        consumed_service = activate_svc(client, consumed_service)
        consumed_service1 = activate_svc(client, consumed_service1)
        link_svc(super_client, service, [dns])
        link_svc(super_client, dns, [consumed_service, consumed_service1])
        dns = activate_svc(client, dns)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_activate_svc_link_activate_consumed_svc_validate(self,
                                                                  super_client,
                                                                  client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsLinkActivateConsumedSvcActivateSvc:

    testname = "TestDnsLinkActivateConsumedSvcActivateSvc"
    port = "31104"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_link_activate_consumed_svc_activate_svc_create(self,
                                                                super_client,
                                                                client):

        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns(
                self.testname, client, self.service_scale,
                self.consumed_service_scale,
                self.port)

        dns = activate_svc(client, dns)
        link_svc(super_client, service, [dns])
        link_svc(super_client, dns, [consumed_service, consumed_service1])
        service = activate_svc(client, service)
        consumed_service = activate_svc(client, consumed_service)
        consumed_service1 = activate_svc(client, consumed_service1)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_link_activate_consumed_svc_activate_svc_validate(self,
                                                                  super_client,
                                                                  client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service,
            [consumed_service, consumed_service1],
            self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsLinkWhenServicesStillActivating:

    testname = "TestDnsLinkWhenServicesStillActivating"
    port = "31106"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_link_when_services_still_activating_create(self, super_client,
                                                            client):

        env, service, consumed_service, consumed_service1, dns = \
            create_env_with_2_svc_dns(
                self.testname, client, self.service_scale,
                self.consumed_service_scale,
                self.port)

        service.activate()
        consumed_service.activate()
        consumed_service1.activate()
        dns.activate()

        service.addservicelink(serviceLink={"serviceId": dns.id})
        dns.addservicelink(serviceLink={"serviceId": consumed_service.id})
        dns.addservicelink(serviceLink={"serviceId": consumed_service1.id})

        service = client.wait_success(service, 120)
        consumed_service = client.wait_success(consumed_service, 120)
        consumed_service1 = client.wait_success(consumed_service1, 120)
        dns = client.wait_success(dns, 120)

        assert service.state == "active"
        assert consumed_service.state == "active"
        assert consumed_service1.state == "active"

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_link_when_services_still_activating_validate(self,
                                                              super_client,
                                                              client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_add_service_link(super_client, service, dns)
        validate_add_service_link(super_client, dns, consumed_service)
        validate_add_service_link(super_client, dns, consumed_service1)

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServiceScaleUp:

    testname = "TestDnsServiceScaleUp"
    port = "31107"
    service_scale = 1
    consumed_service_scale = 2
    final_service_scale = 3

    @pytest.mark.create
    def test_dns_service_scale_up_create(self, super_client, client):
        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_service_scale_up_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServicesScaleDown:

    testname = "TestDnsServicesScaleDown"
    port = "31108"
    service_scale = 3
    consumed_service_scale = 2
    final_service_scale = 1

    @pytest.mark.create
    def test_dns_services_scale_down_create(self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_services_scale_down_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsConsumedServicesScaleUp:

    testname = "TestDnsConsumedServicesScaleUp"
    port = "31109"
    service_scale = 1
    consumed_service_scale = 2
    final_consumed_service_scale = 4

    @pytest.mark.create
    def test_dns_consumed_services_scale_up_create(self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        consumed_service = client.update(
            consumed_service,
            scale=self.final_consumed_service_scale,
            name=consumed_service.name)

        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"
        assert consumed_service.scale == self.final_consumed_service_scale

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_consumed_services_scale_up_validate(self, super_client,
                                                     client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsConsumedServicesScaleDown:

    testname = "TestDnsConsumedServicesScaleDown"
    port = "3110"
    service_scale = 2
    consumed_service_scale = 3
    final_consumed_svc_scale = 1

    @pytest.mark.create
    def test_dns_consumed_services_scale_down_create(self, super_client,
                                                     client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        consumed_service = client.update(consumed_service,
                                         scale=self.final_consumed_svc_scale,
                                         name=consumed_service.name)
        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"
        assert consumed_service.scale == self.final_consumed_svc_scale

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_consumed_services_scale_down_validate(self, super_client,
                                                       client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsConsumedServicesStopStartInstance:

    testname = "TestDnsConsumedServicesStopStartInstance"
    port = "3111"
    service_scale = 1
    consumed_service_scale = 3

    @pytest.mark.create
    def test_dns_consumed_services_stop_start_instance_create(self,
                                                              super_client,
                                                              client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        container_name = env.name + "_" + consumed_service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Stop instance
        container = client.wait_success(container.stop(), 120)
        consumed_service = client.wait_success(consumed_service)
        wait_for_scale_to_adjust(super_client, consumed_service)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_consumed_services_stop_start_instance_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsConsumedServicesRestartInstance:

    testname = "TestDnsConsumedServicesRestartInstance"
    port = "3112"
    service_scale = 1
    consumed_service_scale = 3

    @pytest.mark.create
    def test_dns_consumed_services_restart_instance_create(self, super_client,
                                                           client):
        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        container_name = env.name + "_" + consumed_service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Restart instance
        container = client.wait_success(container.restart(), 120)
        assert container.state == 'running'

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_consumed_services_restart_instance_validate(self,
                                                             super_client,
                                                             client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsConsumedServicesDeleteInstance:

    testname = "TestDnsConsumedServicesDeleteInstance"
    port = "3113"
    service_scale = 1
    consumed_service_scale = 3

    @pytest.mark.create
    def test_dns_consumed_services_delete_instance_create(self, super_client,
                                                          client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        container_name = env.name + "_" + consumed_service.name + "_1"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Delete instance
        container = client.wait_success(client.delete(container))
        assert container.state == 'removed'

        wait_for_scale_to_adjust(super_client, consumed_service)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_consumed_services_delete_instance_validate(self, super_client,
                                                            client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsConsumedServicesDeactivateActivate:

    testname = "TestDnsConsumedServicesDeactivateActivate"
    port = "3114"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_consumed_services_deactivate_activate_create(self,
                                                              super_client,
                                                              client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        consumed_service = consumed_service.deactivate()
        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "inactive"
        wait_until_instances_get_stopped(super_client, consumed_service)

        consumed_service = consumed_service.activate()
        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_consumed_services_deactivate_activate_validate(self,
                                                                super_client,
                                                                client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServiceDeactivateActivate:

    testname = "TestDnsServiceDeactivateActivate"
    port = "3115"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_service_deactivate_activate_create(self, super_client,
                                                    client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1], self.port,
                             dns.name)

        service = service.deactivate()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"
        wait_until_instances_get_stopped(super_client, service)

        service = service.activate()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_service_deactivate_activate_validate(self, super_client,
                                                      client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsDeactivateActivateEnvironment:

    testname = "TestDnsDeactivateActivateEnvironment"
    port = "3116"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_deactivate_activate_environment_create(self, super_client,
                                                        client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client, self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        env = env.deactivateservices()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"

        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "inactive"

        wait_until_instances_get_stopped(super_client, service)
        wait_until_instances_get_stopped(super_client, consumed_service)

        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_deactivate_activate_environment_validate(self, super_client,
                                                          client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsAddRemoceServicelinks:

    testname = "TestDnsAddRemoceServicelinks"
    port = "3117"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_add_remove_servicelinks_create(self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port, dns.name)

        # Add another service to environment
        launch_config = {"imageUuid": WEB_IMAGE_UUID}

        random_name = random_str()
        consumed_service_name = random_name.replace("-", "")
        consumed_service2 = client.create_service(name=consumed_service_name,
                                                  environmentId=env.id,
                                                  launchConfig=launch_config,
                                                  scale=2)
        consumed_service2 = client.wait_success(consumed_service2)
        assert consumed_service2.state == "inactive"

        consumed_service2 = consumed_service2.activate()
        consumed_service2 = client.wait_success(consumed_service2, 120)
        assert consumed_service2.state == "active"

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, consumed_service2.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_add_remove_servicelinks_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        consumed_service2 = client.list_service(uuid=data[4])[0]
        assert len(consumed_service2) > 0
        logger.info("consumed service1 is: %s", format(consumed_service2))

        dns = client.list_service(uuid=data[5])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        # Add another service link
        dns.addservicelink(serviceLink={"serviceId": consumed_service2.id})
        validate_add_service_link(super_client, dns, consumed_service2)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1,
                                    consumed_service2], self.port, dns.name)

        # Remove existing service link to the service
        dns.removeservicelink(serviceLink={"serviceId": consumed_service.id})
        validate_remove_service_link(super_client, dns, consumed_service)

        validate_dns_service(
            super_client, service, [consumed_service1, consumed_service2],
            self.port, dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServicesDeleteServiceAddServive:

    testname = "TestDnsServicesDeleteServiceAddServive"
    port = "3118"
    service_scale = 2
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_services_delete_service_add_service_create(self, super_client,
                                                            client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        # Delete Service

        service = client.wait_success(client.delete(service))
        assert service.state == "removed"
        validate_remove_service_link(super_client, service, dns)

        port1 = "31180"

        # Add another service and link to dns service
        launch_config = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port1+":22/tcp"]}

        random_name = random_str()
        service_name = random_name.replace("-", "")
        service1 = client.create_service(name=service_name,
                                         environmentId=env.id,
                                         launchConfig=launch_config,
                                         scale=1)
        service1 = client.wait_success(service1)
        assert service1.state == "inactive"

        service1 = service1.activate()
        service1 = client.wait_success(service1, 120)
        assert service1.state == "active"

        service1.addservicelink(serviceLink={"serviceId": dns.id})
        validate_add_service_link(super_client, service1, dns)

        data = [env.uuid, service1.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_services_delete_service_add_service_validate(self,
                                                              super_client,
                                                              client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service1 = client.list_service(uuid=data[1])[0]
        assert len(service1) > 0
        logger.info("service1 is: %s", format(service1))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns: %s", format(dns))
        logger.info("dns.name: %s", dns.name)

        validate_dns_service(
            super_client, service1, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServicesDeleteAndAddConsumedService:

    testname = "TestDnsServicesDeleteAndAddConsumedService"
    port = "3119"
    service_scale = 2
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_services_delete_and_add_consumed_svc_create(self,
                                                             super_client,
                                                             client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        # Delete consume service

        consumed_service = client.wait_success(client.delete(consumed_service))
        assert consumed_service.state == "removed"
        validate_remove_service_link(super_client, dns, consumed_service)

        validate_dns_service(super_client, service, [consumed_service1],
                             self.port,
                             dns.name)

        # Add another consume service and link the service to this newly
        # created service

        launch_config = {"imageUuid": WEB_IMAGE_UUID}

        random_name = random_str()
        service_name = random_name.replace("-", "")
        consumed_service2 = client.create_service(name=service_name,
                                                  environmentId=env.id,
                                                  launchConfig=launch_config,
                                                  scale=1)
        consumed_service2 = client.wait_success(consumed_service2)
        assert consumed_service2.state == "inactive"

        consumed_service2 = consumed_service2.activate()
        consumed_service2 = client.wait_success(consumed_service2, 120)
        assert consumed_service2.state == "active"

        service_link = {"serviceId": consumed_service2.id}
        dns.addservicelink(serviceLink=service_link)

        validate_add_service_link(super_client, dns, consumed_service2)

        data = [env.uuid, service.uuid, consumed_service2.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_services_delete_and_add_consumed_svc_validate(self,
                                                               super_client,
                                                               client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service2 = client.list_service(uuid=data[2])[0]
        assert len(consumed_service2) > 0
        logger.info("consumed service1 is: %s", format(consumed_service2))

        dns = client.list_service(uuid=data[3])[0]
        logger.info("dns is: %s", dns)

        validate_dns_service(super_client, service,
                             [consumed_service2],
                             self.port,
                             dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServicesStopStartInstance:

    testname = "TestDnsServicesStopStartInstance"
    port = "3120"
    service_scale = 2
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_services_stop_start_instance_create(self, super_client,
                                                     client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # Stop service instance
        service_instance = client.wait_success(service_instance.stop(), 120)
        service = client.wait_success(service)
        wait_for_scale_to_adjust(super_client, service)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_services_stop_start_instance_delete(self, super_client,
                                                     client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServicesRestartInstance:

    testname = "TestDnsServicesRestartInstance"
    port = "3121"
    service_scale = 2
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_services_restart_instance_create(self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale,
                self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # Restart service instance
        service_instance = client.wait_success(service_instance.restart(), 120)
        assert service_instance.state == 'running'

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_services_restart_instance_validate(self, super_client,
                                                    client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsServiceRestoreInstance:

    testname = "TestDnsServiceRestoreInstance"
    port = "3122"
    service_scale = 2
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_service_restore_instance_create(self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # delete service instance
        service_instance = client.wait_success(client.delete(service_instance))
        assert service_instance.state == 'removed'

        wait_for_scale_to_adjust(super_client, service)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_service_restore_instance_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsDeactivateActivate:

    testname = "TestDnsDeactivateActivate"
    port = "3114"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_dns_deactivate_activate_create(self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale,
                self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        dns = dns.deactivate()
        dns = client.wait_success(dns, 120)
        assert dns.state == "inactive"

        dns = dns.activate()
        dns = client.wait_success(dns, 120)
        assert dns.state == "active"

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_dns_deactivate_activate_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsAddRemoveServiceLinksUsingSet:

    testname = "TestDnsAddRemoveServiceLinksUsingSet"
    port = "3117"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_add_remove_servicelinks_using_set_create(self, super_client,
                                                          client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale,
                self.port)

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        # Add another service to environment
        launch_config = {"imageUuid": WEB_IMAGE_UUID}

        random_name = random_str()
        consumed_service_name = random_name.replace("-", "")
        consumed_service1 = client.create_service(name=consumed_service_name,
                                                  environmentId=env.id,
                                                  launchConfig=launch_config,
                                                  scale=2)
        consumed_service1 = client.wait_success(consumed_service1)
        assert consumed_service1.state == "inactive"

        consumed_service1 = consumed_service1.activate()
        consumed_service1 = client.wait_success(consumed_service1, 120)
        assert consumed_service1.state == "active"

        # Add another service link using setservicelinks

        service_link1 = {"serviceId": consumed_service.id}
        service_link2 = {"serviceId": consumed_service1.id}

        dns.setservicelinks(serviceLinks=[service_link1, service_link2])

        validate_add_service_link(super_client, dns, consumed_service1)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_add_remove_servicelinks_using_set_validate(self, super_client,
                                                            client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(super_client, service,
                             [consumed_service, consumed_service1],
                             self.port, dns.name)
        service_link2 = {"serviceId": consumed_service1.id}

        # Remove existing service link to the service using setservicelinks
        dns.setservicelinks(serviceLinks=[service_link2])

        validate_remove_service_link(super_client, dns, consumed_service)

        validate_dns_service(super_client, service, [consumed_service1],
                             self.port,
                             dns.name)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsSvcConsumedServiceHostnetwork:

    testname = "TestDnsSvcConsumedServiceHostnetwork"
    port = "3118"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_dns_svc_consumed_service_hostnetwork_create(self, super_client,
                                                         client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(self.testname, super_client,
                                                 client,
                                                 self.service_scale,
                                                 self.consumed_service_scale,
                                                 self.port)
        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_svc_consumed_service_hostnetwork_validate(self, super_client,
                                                           client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])


@pytest.mark.P1
@pytest.mark.DNS
@pytest.mark.incremental
class TestDnsSvcManagedConsumedServiceHostnetwork:

    testname = "TestDnsSvcManagedConsumedServiceHostnetwork"
    port = "3118"
    service_scale = 1
    consumed_service_scale = 1

    @pytest.mark.create
    def test_dns_svc_managed_cosumed_service_hostnetwork_create(
            self, super_client, client):

        env, service, consumed_service, consumed_service1, dns = \
            create_environment_with_dns_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port,
                isnetworkModeHost_svc=False,
                isnetworkModeHost_consumed_svc=True)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service1.uuid, dns.uuid]
        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_dns_svc_managed_cosumed_service_hostnetwork_validate(
            self, super_client, client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        consumed_service1 = client.list_service(uuid=data[3])[0]
        assert len(consumed_service1) > 0
        logger.info("consumed service1 is: %s", format(consumed_service1))

        dns = client.list_service(uuid=data[4])[0]
        assert len(dns) > 0
        logger.info("dns is: %s", format(dns))

        validate_dns_service(
            super_client, service, [consumed_service, consumed_service1],
            self.port,
            dns.name)

        delete_all(client, [env])



def test_dns_svc_hostnetwork_consumed_service_hostnetwork(super_client, client):

    port = "3119"
    testname = "TestDnsSvcHostnetworkConsumedServiceHostnetwork"
    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            testname, super_client, client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=True, isnetworkModeHost_consumed_svc=True)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], "33",
        dns.name)

    delete_all(client, [env])


def test_dns_svc_hostnetwork_consumed_service_managednetwork(
        super_client, client):

    port = "3119"
    testname = "TestDnsSvcHostnetworkConsumedServiceManagednetwork"
    service_scale = 1
    consumed_service_scale = 1

    env, service, consumed_service, consumed_service1, dns = \
        create_environment_with_dns_services(
            testname, super_client, client, service_scale, consumed_service_scale, port,
            isnetworkModeHost_svc=True, isnetworkModeHost_consumed_svc=False)

    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], "33",
        dns.name)

    delete_all(client, [env])
