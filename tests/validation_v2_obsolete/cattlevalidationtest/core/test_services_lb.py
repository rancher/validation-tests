from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)


def create_environment_with_lb_services(testname, super_client, client,
                                        service_scale, lb_scale, port,
                                        internal=False):

    env, service, lb_service = create_env_with_svc_and_lb(
        testname, client, service_scale, lb_scale, port, internal)

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


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBserviceActivateLBLinkActivateSvc:

    testname = "TestLBserviceActivateLBLinkActivateSvc"
    port = "8901"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lbservice_activate_lb_link_activate_svc_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_env_with_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            self.port)

        lb_service = activate_svc(client, lb_service)
        link_svc_with_port(super_client, lb_service, [service], "80")
        service = activate_svc(client, service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_activate_lb_link_activate_svc_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServiceActivateSvcLinkActivateLB:

    testname = "TestLBServiceActivateSvcLinkActivateLB"
    port = "8902"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lbservice_activate_svc_link_activate_lb_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_env_with_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            self.port)

        service = activate_svc(client, service)
        link_svc_with_port(super_client, lb_service, [service], "80")
        lb_service = activate_svc(client, lb_service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_activate_svc_link_activate_lb_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServiceLinkActovateLBActivateSvc:

    testname = "TestLBServiceLinkActovateLBActivateSvc"
    port = "8903"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lbservice_link_activate_lb_activate_svc_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_env_with_svc_and_lb(
            self.testname, client, self.service_scale,
            self.lb_scale, self.port)

        link_svc_with_port(super_client, lb_service, [service], "80")
        lb_service = activate_svc(client, lb_service)
        service = activate_svc(client, service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_link_activate_lb_activate_svc_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServiceLinkActivateSvcActivateLB:

    testname = "TestLBServiceLinkActivateSvcActivateLB"
    port = "8904"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lbservice_link_activate_svc_activate_lb_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_env_with_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            self.port)

        link_svc_with_port(super_client, lb_service, [service], "80")
        service = activate_svc(client, service)
        lb_service = activate_svc(client, lb_service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_link_activate_svc_activate_lb_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServiceLinkWhenServicesStillActivating:

    testname = "TestLBServiceLinkWhenServicesStillActivating"
    port = "8905"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lbservice_link_when_services_still_activating_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_env_with_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            self.port)

        service.activate()
        lb_service.activate()
        service_link = {"serviceId": service.id}
        lb_service.addservicelink(serviceLink=service_link)

        service = client.wait_success(service, 120)
        lb_service = client.wait_success(lb_service, 120)

        assert service.state == "active"
        assert lb_service.state == "active"
        validate_add_service_link(super_client, lb_service, service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lbservice_link_when_services_still_activating_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TesLBServicesActivateEnv:

    testname = "TesLBServicesActivateEnv"
    port = "8925"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_activate_env_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_env_with_svc_and_lb(
            self.testname, client, self.service_scale, self.lb_scale,
            self.port)

        service_link = {"serviceId": service.id}
        lb_service.addservicelink(serviceLink=service_link)

        env = env.activateservices()
        env = client.wait_success(env, 120)
        service = client.wait_success(service, 120)
        assert service.state == "active"

        lb_service = client.wait_success(lb_service, 120)
        assert lb_service.state == "active"

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)
        validate_add_service_link(super_client, lb_service, service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_activate_env_vaidate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, self.lb_service, self.port,
                            [service])
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesScaleUpService:

    testname = "TestLBServicesScaleUpService"
    port = "9001"
    service_scale = 2
    lb_scale = 1
    final_service_scale = 3

    @pytest.mark.create
    def test_lb_services_scale_up_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_scale_up_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesScaleDownService:

    testname = "TestLBServicesScaleDownService"
    port = "9002"
    service_scale = 3
    lb_scale = 1
    final_service_scale = 1

    @pytest.mark.create
    def test_lb_services_scale_down_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale,
            self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_scale_down_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesScaleUpLBService:

    testname = "TestLBServicesScaleUpLBService"
    port = "9003"
    service_scale = 2
    lb_scale = 1
    final_lb_scale = 2

    @pytest.mark.create
    def test_lb_services_scale_up_lb_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        lb_service = client.update(lb_service, scale=self.final_lb_scale,
                                   name=lb_service.name)
        lb_service = client.wait_success(lb_service, 120)
        assert lb_service.state == "active"
        assert lb_service.scale == self.final_lb_scale

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_scale_up_lb_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesScaleDownLBService:

    testname = "TestLBServicesScaleDownLBService"
    port = "9004"
    service_scale = 2
    lb_scale = 2
    final_lb_scale = 1

    @pytest.mark.create
    def test_lb_services_scale_down_lb_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale,
            self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        lb_service = client.update(lb_service, scale=self.final_lb_scale,
                                   name=lb_service.name)
        lb_service = client.wait_success(lb_service, 120)
        assert lb_service.state == "active"
        assert lb_service.scale == self.final_lb_scale

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_scale_down_lb_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesStopStartInstance:

    testname = "TestLBServicesStopStartInstance"
    port = "9005"
    service_scale = 3
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_stop_start_instance_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale,
            self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        # Stop instance
        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]
        container = client.wait_success(container.stop(), 120)
        service = client.wait_success(service)
        wait_for_scale_to_adjust(super_client, service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_stop_start_instance_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesDeletePurgeInstance:

    testname = "TestLBServicesDeletePurgeInstance"
    port = "9006"
    service_scale = 3
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_delete_purge_instance_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        # Delete instance
        container_name = env.name + "_" + service.name + "_1"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]
        container = client.wait_success(client.delete(container))
        assert container.state == 'removed'

        wait_for_scale_to_adjust(super_client, service)
        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)
        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_delete_purge_instance_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesDeactivateActivateLBService:

    testname = "TestLBServicesDeactivateActivateLBService"
    port = "9008"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_deactivate_activate_lbservice_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        lb_service = lb_service.deactivate()
        lb_service = client.wait_success(lb_service, 120)
        assert lb_service.state == "inactive"
        wait_until_instances_get_stopped(super_client, lb_service)

        lb_service = lb_service.activate()
        lb_service = client.wait_success(lb_service, 120)
        assert lb_service.state == "active"

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_deactivate_activate_lbservice_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesDeactivateActivateService:

    testname = "TestLBServicesDeactivateActivateService"
    port = "9009"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_deactivate_activate_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        service = service.deactivate()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"
        wait_until_instances_get_stopped(super_client, service)

        service = service.activate()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_deactivate_activate_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesDeactivateActivateEnvironment:

    testname = "TestLBServicesDeactivateActivateEnvironment"
    port = "9010"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_deactivate_activate_environment_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        env = env.deactivateservices()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"

        lb_service = client.wait_success(lb_service, 120)
        assert lb_service.state == "inactive"

        wait_until_instances_get_stopped(super_client, lb_service)

        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        lb_service = client.wait_success(lb_service, 120)
        assert lb_service.state == "active"

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_deactivate_activate_environment_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesAddRemoveServicelinkService:

    testname = "TestLBServicesAddRemoveServicelinkService"
    port = "9011"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_add_remove_servicelinks_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        # Add another service to environment
        launch_config = {"imageUuid": WEB_IMAGE_UUID}

        random_name = random_str()
        service_name = random_name.replace("-", "")
        service1 = client.create_service(name=service_name,
                                         environmentId=env.id,
                                         launchConfig=launch_config,
                                         scale=2)
        service1 = client.wait_success(service1)
        assert service1.state == "inactive"

        service1 = service1.activate()
        service1 = client.wait_success(service1, 120)
        assert service1.state == "active"

        # Add another service link to the LB service
        service_link = {"serviceId": service1.id}
        lb_service.addservicelink(serviceLink=service_link)

        validate_add_service_link(super_client, lb_service, service1)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service, service1], lb_service)
        validate_lb_service(super_client, client, lb_service, self.port,
                            [service, service1])

        # Remove existing service link to the LB service

        service_link = {"serviceId": service.id}
        lb_service.removeservicelink(serviceLink=service_link)

        validate_remove_service_link(super_client, lb_service, service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service1], lb_service)

        data = [env.uuid, service1.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_add_remove_servicelinks_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service1 = client.list_service(uuid=data[1])[0]
        assert len(service1) > 0
        logger.info("service1 is: %s", format(service1))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(
            super_client, client,  lb_service, self.port, [service1])
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesAddRemoveServicelinksLB:

    testname = "TestLBServicesAddRemoveServicelinksLB"
    port = "9011"
    port2 = "9111"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_add_remove_servicelinks_lb_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        # Add another LB service to environment
        launch_config_lb = {"ports": [self.port2+":80"]}
        random_name = random_str()
        service_name = "LB-" + random_name.replace("-", "")

        lb2_service = client.create_loadBalancerService(
            name=service_name, environmentId=env.id,
            launchConfig=launch_config_lb,
            scale=1)

        lb2_service = client.wait_success(lb2_service)
        assert lb2_service.state == "inactive"

        lb2_service = lb2_service.activate()
        service1 = client.wait_success(lb2_service, 120)
        assert service1.state == "active"

        # Link this LB to the existing service

        lb2_service.addservicelink(
            serviceLink={"serviceId": service.id})
        validate_add_service_link(super_client, lb2_service, service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb2_service)
        validate_lb_service(super_client, client,
                            lb2_service, self.port2, [service])

        # Remove existing lB link to service
        lb_service.removeservicelink(
            serviceLink={"serviceId": service.id})
        validate_remove_service_link(super_client, lb_service, service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb2_service)

        data = [env.uuid, service.uuid, lb2_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_add_remove_servicelinks_lb_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        lb2_service = client.list_service(uuid=data[2])[0]
        assert len(lb2_service) > 0
        logger.info("lb2 service is: %s", format(lb2_service))

        validate_lb_service(super_client, client,
                            lb2_service, self.port2, [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesDeleteServiceAddService:

    testname = "TestLBServicesDeleteServiceAddService"
    port = "9012"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_delete_service_add_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale,
            self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        # Delete Service

        service = client.wait_success(client.delete(service))
        assert service.state == "removed"
        validate_remove_service_link(super_client, lb_service, service)

        # Add another service to environment and link to LB
        launch_config = {"imageUuid": WEB_IMAGE_UUID}

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

        # Add another service link to the LB service
        service_link = {"serviceId": service1.id}
        lb_service.addservicelink(serviceLink=service_link)

        validate_add_service_link(super_client, lb_service, service1)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service1], lb_service)

        data = [env.uuid, service1.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_delete_service_add_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service1 = client.list_service(uuid=data[1])[0]
        assert len(service1) > 0
        logger.info("service1 is: %s", format(service1))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(
            super_client, client,  lb_service, self.port, [service1])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesDeleteLBService:

    testname = "TestLBServicesDeleteLBService"
    port = "9013"
    service_scale = 2
    lb_scale = 1

    @pytest.mark.create
    def test_lb_services_delete_lb_service_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)
        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        # Delete LB Service

        lb_service = client.wait_success(client.delete(lb_service))
        assert lb_service.state == "removed"
        validate_remove_service_link(super_client, lb_service, service)

        delete_all(client, [env])

        # Make sure you are able to add another LB service using the same port

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale,
            self.port)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_delete_lb_service_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service1 is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesStopStartLBInstance:

    testname = "TestLBServicesStopStartLBInstance"
    port = "9014"
    service_scale = 2
    lb_scale = 2

    @pytest.mark.create
    def test_lb_services_stop_start_lb_instance_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        lb_instances = get_service_container_list(super_client, lb_service)
        assert len(lb_instances) == self.lb_scale
        lb_instance = lb_instances[0]

        # Stop lb instance
        lb_instance = client.wait_success(lb_instance.stop(), 120)
        lb_service = client.wait_success(lb_service)

        wait_for_scale_to_adjust(super_client, lb_service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_stop_start_lb_instance_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service1 is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
@pytest.mark.incremental
class TestLBServicesLBInstanceRestart:

    testname = "TestLBServicesLBInstanceRestart"
    port = "9015"
    service_scale = 2
    lb_scale = 2

    @pytest.mark.create
    def test_lb_services_lb_instance_restart_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale,
            self.port)
        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        lb_instances = get_service_container_list(super_client, lb_service)
        assert len(lb_instances) == self.lb_scale
        lb_instance = lb_instances[0]

        # Restart lb instance
        lb_instance = client.wait_success(lb_instance.restart(), 120)
        assert lb_instance.state == 'running'

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_lb_services_lb_instance_restart_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service1 is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.skipif(True, reason='Needs QA debugging')
class TestLBServicesLBInstanceDelete:

    testname = "TestLBServicesLBInstanceDelete"
    port = "9016"
    service_scale = 2
    lb_scale = 2

    def test_lb_services_lb_instance_delete_create(
            self, super_client, client, socat_containers):

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, self.service_scale,
            self.lb_scale, self.port)

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        lb_instances = get_service_container_list(super_client, lb_service)
        assert len(lb_instances) == self.lb_scale
        lb_instance = lb_instances[0]

        # delete lb instance
        lb_instance = client.wait_success(client.delete(lb_instance))
        assert lb_instance.state == 'removed'

        wait_for_scale_to_adjust(super_client, lb_service)

        wait_for_lb_service_to_become_active(super_client, client,
                                             [service], lb_service)

        data = [env.uuid, service.uuid, lb_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    def test_lb_services_lb_instance_delete_validate(
            self, super_client, client, socat_containers):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service1 is: %s", format(service))

        lb_service = client.list_service(uuid=data[2])[0]
        assert len(lb_service) > 0
        logger.info("lb service is: %s", format(lb_service))

        validate_lb_service(super_client, client, lb_service, self.port,
                            [service])

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.LB
class TestLBServiceInternal:

    testname = "TestLBServiceInternal"

    def test_lbservice_internal(self, super_client, client, socat_containers):

        port = "9017"
        con_port = "9018"

        hosts = client.list_host(kind='docker', removed_null=True,
                                 state="active")
        assert len(hosts) > 0

        lb_scale = 1
        service_scale = 2
        host = hosts[0]

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, service_scale, lb_scale,
            port,
            internal=True)

        # Deploy container in same network to test accessibility of internal LB
        hosts = client.list_host(kind='docker', removed_null=True,
                                 state="active")
        assert len(hosts) > 0
        host = hosts[0]

        client_con = client.create_container(
            name=random_str(), imageUuid=SSH_IMAGE_UUID,
            ports=[con_port+":22/tcp"], requestedHostId=host.id)
        client_con = client.wait_success(client_con, 120)
        assert client_con.state == "running"
        # Wait for exposed port to be available
        time.sleep(5)
        validate_internal_lb(super_client, lb_service, [service], host,
                             con_port, port)

        # Check that port in the host where LB Agent is running is
        # not accessible
        lb_containers = get_service_container_list(super_client, lb_service)
        assert len(lb_containers) == lb_service.scale
        for lb_con in lb_containers:
            host = super_client.by_id('host', lb_con.hosts[0].id)
            assert check_for_no_access(host, port)
        delete_all(client, [env, client_con])


@pytest.mark.P0
@pytest.mark.LB
class TestMultipleLBServiceInternalSameHostPort:

    testname = "TestMultipleLBServiceInternalSameHostPort"
    env2_name = "TestMultipleLBServiceInternalSameHostPort-env2"
    port = "9019"
    con_port = "9020"

    def test_multiple_lbservice_internal_same_host_port_create(
            self, super_client, client, socat_containers):

        hosts = client.list_host(kind='docker', removed_null=True,
                                 state="active")
        assert len(hosts) > 0

        lb_scale = len(hosts)
        service_scale = 2
        host = hosts[0]

        env, service, lb_service = create_environment_with_lb_services(
            self.testname, super_client, client, service_scale, lb_scale,
            self.port,
            internal=True)

        # Deploy container in same network to test accessibility of internal LB
        hosts = client.list_host(kind='docker', removed_null=True,
                                 state="active")
        assert len(hosts) > 0
        host = hosts[0]

        client_con = client.create_container(
            name=random_str(), imageUuid=SSH_IMAGE_UUID,
            ports=[self.con_port+":22/tcp"], requestedHostId=host.id)
        client_con = client.wait_success(client_con, 120)
        assert client_con.state == "running"
        # Wait for exposed port to be available
        time.sleep(5)
        validate_internal_lb(super_client, lb_service, [service],
                             host, self.con_port, self.port)

        env2, service2, lb_service2 = create_environment_with_lb_services(
            self.env2_name, super_client, client, service_scale, lb_scale,
            self.port,
            internal=True)
        validate_internal_lb(super_client, lb_service2, [service2], host,
                             self.con_port, self.port)

        delete_all(client, [env, env2, client_con])
