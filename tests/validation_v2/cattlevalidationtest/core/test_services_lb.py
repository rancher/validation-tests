from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)


def create_environment_with_lb_services(super_client, client,
                                        service_scale, lb_scale, port,
                                        testname, internal=False):

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, testname, internal)

    service.activate()
    lb_service.activate()

    service_link = {"serviceId": service.id}
    lb_service.addservicelink(serviceLink=service_link)

    service = client.wait_success(service, 180)
    lb_service = client.wait_success(lb_service, 180)

    assert service.state == "active"
    assert lb_service.state == "active"
    wait_for_lb_service_to_become_active(super_client, client,
                                         [service], lb_service)
    return env, service, lb_service


class TestLbserviceActivateLbActivateSvcLink1:

    testname = "TestLbserviceActivateLbActivateSvcLink1"
    port = "8900"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    @pytest.mark.run(order=1)
    def test_lbservice_activate_lb_activate_svc_link1_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            super_client, client, self.service_scale, self.lb_scale, self.port,
            self.testname)
        data = [env.uuid, service.uuid, lb_service.uuid]

        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    @pytest.mark.run(order=2)
    def test_lbservice_activate_lb_activate_svc_link1_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])
        logger.info("env is: %s", format(env))

        services = client.list_service(uuid=data[1])
        assert len(services) > 0
        service = services[0]
        logger.info("service is: %s", format(service))

        lb_services = client.list_service(uuid=data[2])
        assert len(lb_services) > 0
        lb_service = lb_services[0]
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(
            super_client, client, lb_service, self.port, [service])
        # delete_all(client, [env])


class TestLbserviceActivateLbActivateSvcLink2:

    testname = "TestLbserviceActivateLbActivateSvcLink2"
    port = "8901"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    @pytest.mark.run(order=1)
    def test_lbservice_activate_lb_activate_svc_link2_create(
            self, super_client, client, socat_containers):

        # env, service, lb_service = create_env_with_svc_and_lb(
        #     super_client, client, self.service_scale, self.lb_scale,
        # self.port, self.testname)
        env, service, lb_service = create_environment_with_lb_services(
            super_client, client, self.service_scale, self.lb_scale, self.port,
            self.testname)
        # lb_service = activate_svc(client, lb_service)
        link_svc_with_port(super_client, lb_service, [service], "80")
        # service = activate_svc(client, service)

        wait_for_lb_service_to_become_active(super_client, client, [service],
                                             lb_service)
        data = [env.uuid, service.uuid, lb_service.uuid]

        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    @pytest.mark.run(order=2)
    def test_lbservice_activate_lb_activate_svc_link2_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])
        logger.info("env is: %s", format(env))

        services = client.list_service(uuid=data[1])
        assert len(services) > 0
        service = services[0]
        logger.info("service is: %s", format(service))

        lb_services = client.list_service(uuid=data[2])
        assert len(lb_services) > 0
        lb_service = lb_services[0]
        logger.info("consumed service is: %s", format(service))

        validate_lb_service(
            super_client, client, lb_service, self.port, [service])
        # delete_all(client, [env])
