from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TestLbserviceHostRouting1:

    testname = "TestLbserviceHostRouting1"
    port = "900"
    service_scale = 2
    lb_scale = 1
    service_count = 4

    @pytest.mark.create
    @pytest.mark.run(order=1)
    def test_lbservice_host_routing_1_create(self, super_client, client,
                                             socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            client, self.service_scale, self.lb_scale, [self.port],
            self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["www.abc3.com/service1.html",
                                   "www.abc4.com/service2.html"]}
        service_link4 = {"serviceId": services[3].id,
                         "ports": ["www.abc3.com/service1.html",
                                   "www.abc4.com/service2.html"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])

        data = [env.uuid, services[0].uuid, services[1].uuid, services[2].uuid,
                services[3].uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    @pytest.mark.run(order=2)
    def test_lbservice_host_routing_1_create_validate(self, super_client,
                                                      client,
                                                      socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])
        logger.info("env is: %s", format(env))

        services = client.list_service(uuid=data[1])
        assert len(services) > 0
        service = services[0]
        logger.info("service1 is: %s", format(service))

        services = client.list_service(uuid=data[2])
        assert len(services) > 0
        service = services[0]
        logger.info("service2 is: %s", format(service))

        services = client.list_service(uuid=data[3])
        assert len(services) > 0
        service = services[0]
        logger.info("service3 is: %s", format(service))

        services = client.list_service(uuid=data[4])
        assert len(services) > 0
        service = services[0]
        logger.info("service4 is: %s", format(service))

        services = client.list_service(uuid=data[5])
        assert len(services) > 0
        service = services[0]
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[6])
        assert len(lb_service) > 0
        lb_service = services[0]
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        validate_lb_service(super_client, client,
                            lb_service, self.port,
                            [services[0], services[1]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2], services[3]],
                            "www.abc3.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2], services[3]],
                            "www.abc4.com", "/service2.html")


class TestLbServiceHostRoutingCrossStack:

    port = "901"
    service_scale = 2
    lb_scale = 1
    service_count = 4

    @pytest.mark.validate
    @pytest.mark.run(order=1)
    def test_lbservice_host_routing_cross_stack_create(self,
                                                       super_client, client,
                                                       socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            client, self.service_scale, self.lb_scale, [self.port],
            self.service_count, True)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["www.abc3.com/service1.html",
                                   "www.abc4.com/service2.html"]}
        service_link4 = {"serviceId": services[3].id,
                         "ports": ["www.abc3.com/service1.html",
                                   "www.abc4.com/service2.html"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])

        for service in services:
            service = service.activate()
        for service in services:
            service = client.wait_success(service, 120)
            assert service.state == "active"
        data = [env.uuid, services[0].uuid, services[1].uuid,
                services[2].uuid, services[3].uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    @pytest.mark.run(order=1)
    def test_lbservice_host_routing_cross_stack_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])
        logger.info("env is: %s", format(env))

        services = client.list_service(uuid=data[1])
        assert len(services) > 0
        service = services[0]
        logger.info("service1 is: %s", format(service))

        services = client.list_service(uuid=data[2])
        assert len(services) > 0
        service = services[0]
        logger.info("service2 is: %s", format(service))

        services = client.list_service(uuid=data[3])
        assert len(services) > 0
        service = services[0]
        logger.info("service3 is: %s", format(service))

        services = client.list_service(uuid=data[4])
        assert len(services) > 0
        service = services[0]
        logger.info("service4 is: %s", format(service))

        services = client.list_service(uuid=data[5])
        assert len(services) > 0
        service = services[0]
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[6])
        assert len(lb_service) > 0
        lb_service = services[0]
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        validate_lb_service(super_client, client,
                            lb_service, self.port,
                            [services[0], services[1]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2], services[3]],
                            "www.abc3.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2], services[3]],
                            "www.abc4.com", "/service2.html")
        to_delete = [env]
        for service in services:
            to_delete.append(get_env(super_client, service))
        delete_all(client, to_delete)
