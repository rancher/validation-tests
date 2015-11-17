from common_fixtures import *  # NOQA


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLbserviceHostRouting1:

    testname = "TestLbserviceHostRouting1"
    port = "900"
    service_scale = 2
    lb_scale = 1
    service_count = 4

    @pytest.mark.create
    def test_lbservice_host_routing_1_create(self, super_client, client,
                                             socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
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

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_1_create_validate(self, super_client,
                                                      client,
                                                      socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
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
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLbServiceHostRoutingCrossStack:

    testname = "TestLbServiceHostRoutingCrossStack"
    port = "901"
    service_scale = 2
    lb_scale = 1
    service_count = 4

    @pytest.mark.create
    def test_lbservice_host_routing_cross_stack_create(self,
                                                       super_client, client,
                                                       socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
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
            service = client.wait_success(service, 120)
            assert service.state == "active"

        data = [env.uuid, [svc.uuid for svc in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_cross_stack_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
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


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRouting2:

    testname = "TestLBServiceHostRouting2"
    port = "902"
    service_scale = 2
    lb_scale = 1
    service_count = 3

    @pytest.mark.create
    def test_lbservice_host_routing_2_create(self, super_client, client,
                                             socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
            self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["www.abc1.com/name.html",
                                   "www.abc2.com/name.html"]}
        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3])

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_2_validate(self, super_client, client,
                                               socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc1.com",
                                          "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com",
                                          "/service1.html")
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostrRoutingScaleUp:

    testname = "TestLBServiceHostrRoutingScaleUp"
    port = "903"
    service_scale = 2
    lb_scale = 1
    service_count = 3

    @pytest.mark.create
    def test_lbservice_host_routing_scale_up_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
            self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["www.abc1.com/name.html",
                                   "www.abc2.com/name.html"]}
        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3])

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc1.com",
                                          "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com",
                                          "/service1.html")
        final_service_scale = 3
        final_services = []
        for service in services:
            service = client.update(service, scale=final_service_scale,
                                    name=service.name)
            service = client.wait_success(service, 120)
            assert service.state == "active"
            assert service.scale == final_service_scale
            final_services.append(service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             final_services,
                                             lb_service)

        data = [env.uuid, [svc.uuid for svc in final_services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_scale_up_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        final_services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", final_services)
        assert len(final_services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [final_services[0], final_services[1]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port,
                            [final_services[0], final_services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [final_services[2]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [final_services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc1.com",
                                          "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com", "/service1.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingScaleDown:

    testname = "TestLBServiceHostRoutingScaleDown"
    port = "904"
    service_scale = 3
    lb_scale = 1
    service_count = 3

    @pytest.mark.create
    def test_lbservice_host_routing_scale_down_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
            self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com/service1.html",
                                   "www.abc2.com/service2.html"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["www.abc1.com/name.html",
                                   "www.abc2.com/name.html"]}
        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3])

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_scale_down_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc1.com",
                                          "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com",
                                          "/service1.html")
        final_service_scale = 2
        final_services = []
        for service in services:
            service = client.update(service, scale=final_service_scale,
                                    name=service.name)
            service = client.wait_success(service, 120)
            assert service.state == "active"
            assert service.scale == final_service_scale
            final_services.append(service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             final_services,
                                             lb_service)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [final_services[0], final_services[1]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client, lb_service, self.port,
                            [final_services[0], final_services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client, lb_service,
                            self.port, [final_services[2]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client, lb_service, self.port,
                            [final_services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc1.com",
                                          "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com",
                                          "/service1.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingOnlyPath:

    testname = "TestLBServiceHostRoutingOnlyPath"
    port = "905"
    service_scale = 2
    lb_scale = 1
    service_count = 2

    @pytest.mark.create
    def test_lbservice_host_routing_only_path_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
            self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["/service1.html"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["/service2.html"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2])

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_only_path_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc1.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc2.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            None, "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[1]],
                            "www.abc3.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port,  [services[1]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            None, "/service1.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc3.com", "/name.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingOnlyHost:

    testname = "TestLBServiceHostRoutingOnlyHost"
    port = "906"
    service_scale = 2
    lb_scale = 1
    service_count = 2

    @pytest.mark.create
    def test_lbservice_host_routing_only_host_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
            self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2])

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])

        wait_for_lb_service_to_become_active(super_client, client,
                                             [services[0], services[1]],
                                             lb_service)

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_only_host_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[1]],
                            "www.abc1.com", "/name.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com", "/name.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRouting3:

    testname = "TestLBServiceHostRouting3"
    port = "907"
    service_scale = 2
    lb_scale = 1
    service_count = 4

    @pytest.mark.create
    def test_lbservice_host_routing_3_create(self, super_client, client,
                                             socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com"]}
        service_link3 = {"serviceId": services[2].id}
        service_link4 = {"serviceId": services[3].id,
                         "ports": ["/service1.html"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_3_validate(self, super_client, client,
                                               socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])
        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[1]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[3]],
                            "www.abc3.com", "/service1.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceEditHostRouting3:

    testname = "TestLBServiceEditHostRouting3"
    port = "908"
    service_scale = 2
    lb_scale = 1
    service_count = 5

    @pytest.mark.create
    def test_lbservice_edit_host_routing_3_create(self, super_client, client,
                                                  socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port],
            self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com"]}
        service_link3 = {"serviceId": services[2].id}
        service_link4 = {"serviceId": services[3].id,
                         "ports": ["/service1.html"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_edit_host_routing_3_validate(self, super_client, client,
                                                    socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])

        service_list = [services[0], services[1], services[2], services[3]]
        wait_for_lb_service_to_become_active(super_client, client,
                                             service_list,
                                             lb_service)
        validate_lb_service(super_client, client, lb_service,
                            self.port, [services[0]],
                            "www.abc.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[1]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[3]],
                            "www.abc3.com", "/service1.html")

        # Edit service links
        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com"]}
        service_link2 = {"serviceId": services[2].id}
        service_link3 = {"serviceId": services[3].id,
                         "ports": ["/service2.html"]}
        service_link4 = {"serviceId": services[4].id,
                         "ports": ["www.abc.com", "www.abc1.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[4])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])

        service_list = [services[0], services[2], services[3], services[4]]

        wait_for_lb_service_to_become_active(super_client, client,
                                             service_list,
                                             lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0], services[4]],
                            "www.abc.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[4]],
                            "www.abc1.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[2]],
                            "www.abc2.com", "/name.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[3]],
                            "www.abc3.com", "/service2.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceEditHostRoutingAddHost:

    testname = "TestLBServiceEditHostRoutingAddHost"
    port = "909"
    service_scale = 2
    lb_scale = 1
    service_count = 1

    @pytest.mark.create
    def test_lbservice_edit_host_routing_add_host_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1])

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_edit_host_routing_add_host_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com", "/name.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc3.com", "/name.html")

        # Edit service links
        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com", "www.abc2.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1])

        validate_add_service_link(super_client, lb_service, services[0])
        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc2.com", "/name.html")

        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc3.com", "/name.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceEditHostRoutingRemoveHost:

    testname = "TestLBServiceEditHostRoutingRemoveHost"
    port = "910"
    service_scale = 2
    lb_scale = 1
    service_count = 1

    @pytest.mark.create
    def test_lbservice_edit_host_routing_remove_host_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com", "www.abc2.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1])

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_edit_host_routing_remove_host_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        wait_for_lb_service_to_become_active(super_client, client, services,
                                             lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc2.com", "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc3.com", "/name.html")

        # Edit service links
        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_add_service_link(super_client, lb_service, services[0])

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com", "/name.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceEditHostRoutingEditExistingHost:

    testname = "TestLBServiceEditHostRoutingEditExistingHost"
    port = "911"
    service_scale = 2
    lb_scale = 1
    service_count = 1

    @pytest.mark.create
    def test_lbservice_edit_host_routing_edit_existing_host_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = create_env_with_multiple_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            [self.port], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_edit_host_routing_edit_existing_host_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)

        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])

        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc.com", "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc2.com", "/name.html")

        # Edit service links
        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc2.com"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1])

        validate_add_service_link(super_client, lb_service, services[0])
        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port, [services[0]],
                            "www.abc2.com", "/service2.html")
        validate_lb_service_for_no_access(client, lb_service, self.port,
                                          "www.abc.com", "/name.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingMultiplePort1:

    testname = "TestLBServiceHostRoutingMultiplePort1"
    port1 = "1000"
    port2 = "1001"
    port1_target = "80"
    port2_target = "81"
    service_scale = 2
    lb_scale = 1
    service_count = 4

    @pytest.mark.create
    def test_lbservice_host_routing_multiple_port_1_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = \
            create_env_with_multiple_svc_and_lb(self.testname, client,
                                                self.service_scale,
                                                self.lb_scale,
                                                [self.port1, self.port2],
                                                self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com:"+self.port1+"/service1.html",
                                   "www.abc1.com:"+self.port2+"/service3.html"]
                         }
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc2.com"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["/service1.html="+self.port1_target,
                                   "/service3.html="+self.port2_target]}
        service_link4 = {"serviceId": services[3].id}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_multiple_port_1_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[0]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[3]],
                            "www.abc1.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc2.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc2.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[1]],
                            "www.abc2.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2,
                            [services[0]],
                            "www.abc1.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[2]],
                            "www.abc4.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[3]],
                            "www.abc3.com", "/service4.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingMultiplePort2:

    testname = "TestLBServiceHostRoutingMultiplePort2"
    port1 = "1002"
    port2 = "1003"
    service_scale = 2
    lb_scale = 1
    service_count = 3

    @pytest.mark.create
    def test_lbservice_host_routing_multiple_port_2_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = \
            create_env_with_multiple_svc_and_lb(
                self.testname, client, self.service_scale, self.lb_scale,
                [self.port1, self.port2], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["/81"]}
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["/81/service3.html"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["/service"]}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2, service_link3])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_multiple_port_2_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])

        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[2]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[0]],
                            "www.abc1.com", "/81/service4.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc1.com", "/81/service3.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[2]],
                            "www.abc1.com", "/service3.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[2]],
                            "www.abc1.com", "/service4.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingMultiplePort3:

    testname = "TestLBServiceHostRoutingMultiplePort3"
    port1 = "1004"
    port2 = "1005"
    service_scale = 2
    lb_scale = 1
    service_count = 2

    @pytest.mark.create
    def test_lbservice_host_routing_multiple_port_3_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = \
            create_env_with_multiple_svc_and_lb(
                self.testname, client, self.service_scale, self.lb_scale,
                [self.port1, self.port2],
                self.service_count)

        service_link1 = {"serviceId": services[0].id}
        service_link2 = {"serviceId": services[1].id}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_multiple_port_3_cvalidate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])

        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[0], services[1]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2,
                            [services[0], services[1]],
                            "www.abc1.com", "/service3.html")
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingTargetPortOverride:

    testname = "TestLBServiceHostRoutingTargetPortOverride"
    port1 = "1010"
    service_scale = 2
    lb_scale = 1
    service_count = 2

    @pytest.mark.create
    def test_lbservice_host_routing_target_port_override_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = \
            create_env_with_multiple_svc_and_lb(
                self.testname, client, self.service_scale, self.lb_scale,
                [self.port1], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["/service3.html=81"]}
        service_link2 = {"serviceId": services[1].id}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_target_port_override_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])

        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[1]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[0]],
                            "www.abc1.com", "/service3.html")
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLbServiceHostRoutingMultiplePort1EditAdd:

    testname = "TestLbServiceHostRoutingMultiplePort1EditAdd"
    port1 = "1006"
    port2 = "1007"
    port1_target = "80"
    port2_target = "81"
    service_scale = 2
    lb_scale = 1
    service_count = 5

    @pytest.mark.create
    def test_lbservice_host_routing_multiple_port_1_edit_add_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = \
            create_env_with_multiple_svc_and_lb(
                self.testname, client, self.service_scale, self.lb_scale,
                [self.port1, self.port2], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com:"+self.port1+"/service1.html",
                                   "www.abc1.com:"+self.port2+"/service3.html"]
                         }
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["/service1.html="+self.port1_target,
                                   "/service3.html="+self.port2_target]}
        service_link4 = {"serviceId": services[3].id}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])
        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_multiple_port_1_edit_add_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])

        service_list = [services[0], services[1], services[2], services[3]]
        wait_for_lb_service_to_become_active(super_client, client,
                                             service_list, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[0]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc1.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[2]],
                            "www.abc2.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[3]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port2,
                            [services[0]],
                            "www.abc1.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[1]],
                            "www.abc1.com", "/service4.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[2]],
                            "www.abc2.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[3]],
                            "www.abc2.com", "/service4.html")

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com:"+self.port1+"/service1.html",
                                   "www.abc1.com:"+self.port2+"/service3.html",
                                   "www.abc2.com:"+self.port1+"/service1.html",
                                   "www.abc2.com:"+self.port2+"/service3.html"]
                         }
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com", "www.abc2.com"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["/service1.html="+self.port1_target,
                                   "/service3.html="+self.port2_target]}
        service_link4 = {"serviceId": services[3].id}
        service_link5 = {"serviceId": services[4].id}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4, service_link5])

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])
        validate_add_service_link(super_client, lb_service, services[4])
        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[0]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc1.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[0]],
                            "www.abc2.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc2.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[3], services[4]],
                            "www.abc3.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port2,
                            [services[0]],
                            "www.abc1.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[1]],
                            "www.abc1.com", "/service4.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[0]],
                            "www.abc2.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[1]],
                            "www.abc2.com", "/service4.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[3], services[4]],
                            "www.abc3.com", "/service4.html")

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LBHostRouting
@pytest.mark.incremental
class TestLBServiceHostRoutingMultiplePort1EditEdit:

    testname = "TestLBServiceHostRoutingMultiplePort1EditEdit"
    port1 = "1008"
    port2 = "1009"
    port1_target = "80"
    port2_target = "81"
    service_scale = 2
    lb_scale = 1
    service_count = 5

    @pytest.mark.create
    def test_lbservice_host_routing_multiple_port_1_edit_edit_create(
            self, super_client, client, socat_containers):

        env, services, lb_service = \
            create_env_with_multiple_svc_and_lb(
                self.testname, client, self.service_scale, self.lb_scale,
                [self.port1, self.port2], self.service_count)

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc1.com:"+self.port1+"/service1.html",
                                   "www.abc1.com:"+self.port2+"/service3.html"]
                         }
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc1.com"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["/service1.html="+self.port1_target,
                                   "/service3.html="+self.port2_target]}
        service_link4 = {"serviceId": services[3].id}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4])

        data = [env.uuid, [service.uuid for service in services],
                lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_host_routing_multiple_port_1_edit_edit_validate(
            self, super_client, client, socat_containers):

        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        services = \
            [client.list_service(uuid=i)[0] for i in data[1]]
        logger.info("services: %s", services)
        assert len(services) == self.service_count

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)

        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[0]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc1.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[2]],
                            "www.abc2.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[3]],
                            "www.abc2.com", "/service2.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port2,
                            [services[0]],
                            "www.abc1.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[1]],
                            "www.abc1.com", "/service4.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[2]],
                            "www.abc2.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[3]],
                            "www.abc2.com", "/service4.html")

        service_link1 = {"serviceId": services[0].id,
                         "ports": ["www.abc2.com:"+self.port1+"/service1.html",
                                   "www.abc2.com:"+self.port2+"/service3.html"]
                         }
        service_link2 = {"serviceId": services[1].id,
                         "ports": ["www.abc3.com"]}
        service_link3 = {"serviceId": services[2].id,
                         "ports": ["/service2.html="+self.port1_target,
                                   "/service4.html="+self.port2_target]}
        service_link4 = {"serviceId": services[3].id}
        service_link5 = {"serviceId": services[4].id}

        lb_service.setservicelinks(
            serviceLinks=[service_link1, service_link2,
                          service_link3, service_link4, service_link5])

        validate_add_service_link(super_client, lb_service, services[0])
        validate_add_service_link(super_client, lb_service, services[1])
        validate_add_service_link(super_client, lb_service, services[2])
        validate_add_service_link(super_client, lb_service, services[3])
        validate_add_service_link(super_client, lb_service, services[4])

        wait_for_lb_service_to_become_active(super_client, client,
                                             services, lb_service)
        validate_lb_service(super_client, client,
                            lb_service, self.port1,
                            [services[0]],
                            "www.abc2.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[2]],
                            "www.abc2.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[3], services[4]],
                            "www.abc1.com", "/service1.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[2]],
                            "www.abc1.com", "/service2.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port1, [services[1]],
                            "www.abc3.com", "/service1.html")

        validate_lb_service(super_client, client,
                            lb_service, self.port2,
                            [services[0]],
                            "www.abc2.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[2]],
                            "www.abc2.com", "/service4.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[3], services[4]],
                            "www.abc1.com", "/service3.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[2]],
                            "www.abc1.com", "/service4.html")
        validate_lb_service(super_client, client,
                            lb_service, self.port2, [services[1]],
                            "www.abc3.com", "/service3.html")

        delete_all(client, [env])


def test_lbservice_external_service(super_client, client, socat_containers):
    port = "1010"

    lb_scale = 2

    env, lb_service, ext_service, con_list = \
        create_env_with_ext_svc_and_lb(client, lb_scale, port)

    ext_service = activate_svc(client, ext_service)
    lb_service = activate_svc(client, lb_service)

    lb_service.setservicelinks(serviceLinks=[{"serviceId": ext_service.id}])

    validate_add_service_link(super_client, lb_service, ext_service)

    # Wait for host maps to be created
    lbs = client.list_loadBalancer(serviceId=lb_service.id)
    assert len(lbs) == 1
    lb = lbs[0]
    host_maps = wait_until_host_map_created(client, lb, lb_service.scale, 60)
    assert len(host_maps) == lb_service.scale

    validate_lb_service_for_external_services(super_client, client,
                                              lb_service, port, con_list)

    delete_all(client, [env])


def test_lbservice_host_routing_tcp_only(super_client, client,
                                         socat_containers):

    port = "1011/tcp"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count)

    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc1.com/service1.html",
                               "www.abc2.com/service2.html"]}
    service_link2 = {"serviceId": services[1].id,
                     "ports": ["www.abc1.com/service1.html",
                               "www.abc2.com/service2.html"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1, service_link2])

    validate_add_service_link(super_client, lb_service, services[0])
    validate_add_service_link(super_client, lb_service, services[1])

    wait_for_lb_service_to_become_active(super_client, client,
                                         services, lb_service)

    port = "1011"
    validate_lb_service(super_client, client,
                        lb_service, port,
                        [services[0], services[1]])

    validate_lb_service(super_client, client,
                        lb_service, port, [services[0], services[1]])

    delete_all(client, [env])


def test_lbservice_host_routing_tcp_and_http(super_client, client,
                                             socat_containers):

    port1 = "1012/tcp"
    port2 = "1013"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port1, port2], service_count)

    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc1.com/service3.html"]}
    service_link2 = {"serviceId": services[1].id,
                     "ports": ["www.abc1.com/service4.html"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1, service_link2])

    validate_add_service_link(super_client, lb_service, services[0])
    validate_add_service_link(super_client, lb_service, services[1])

    wait_for_lb_service_to_become_active(super_client, client,
                                         services, lb_service)

    port1 = "1012"
    validate_lb_service(super_client, client,
                        lb_service, port1,
                        [services[0], services[1]])

    validate_lb_service(super_client, client,
                        lb_service, port1,
                        [services[0], services[1]])

    validate_lb_service(super_client, client,
                        lb_service, port2,
                        [services[0]],
                        "www.abc1.com", "/service3.html")

    validate_lb_service(super_client, client,
                        lb_service, port2, [services[1]],
                        "www.abc1.com", "/service4.html")

    validate_lb_service_for_no_access(client, lb_service, port2,
                                      "www.abc2.com",
                                      "/service3.html")
    delete_all(client, [env])
