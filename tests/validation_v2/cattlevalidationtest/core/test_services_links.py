from common_fixtures import *  # NOQA


def create_environment_with_linked_services(
        testname, super_client, client, service_scale, consumed_service_scale,
        port,
        ssh_port="22", isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=False):

    if not isnetworkModeHost_svc and not isnetworkModeHost_consumed_svc:
        env, service, consumed_service = create_env_with_2_svc(
            testname, client, service_scale, consumed_service_scale, port)
    else:
        env, service, consumed_service = create_env_with_2_svc_hostnetwork(
            testname, client, service_scale, consumed_service_scale, port,
            ssh_port,
            isnetworkModeHost_svc, isnetworkModeHost_consumed_svc)
    service.activate()
    consumed_service.activate()

    service.addservicelink(serviceLink={"serviceId": consumed_service.id})
    service = client.wait_success(service, 120)

    consumed_service = client.wait_success(consumed_service, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    validate_add_service_link(super_client, service, consumed_service)

    return env, service, consumed_service


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkActivateSvcActivateConsumedSvcLink:

    testname = "TestLinkActivateSvcActivateConsumedSvcLink"
    port = "301"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_link_activate_svc_activate_consumed_svc_link_create(self,
                                                                 super_client,
                                                                 client):

        env, service, consumed_service = \
            create_environment_with_linked_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_activate_svc_activate_consumed_svc_link_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service : %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service : %s", format(consumed_service))

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkActivateConsumedSvcLinkActivate:

    testname = "TestLinkActivateConsumedSvcLinkActivate"
    port = "302"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_link_activate_consumed_svc_link_activate_svc_create(
            self, super_client, client):

        env, service, consumed_service = create_env_with_2_svc(
            self.testname, client, self.service_scale,
            self.consumed_service_scale,
            self.port)

        consumed_service = activate_svc(client, consumed_service)
        link_svc(super_client, service, [consumed_service])
        service = activate_svc(client, service)
        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_activate_consumed_svc_link_activate_svc(self, super_client,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkActivateSvcLinkActivateConsumedSvc:

    testname = "TestLinkActivateSvcLinkActivateConsumedSvc"
    port = "303"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_link_activate_svc_link_activate_consumed_svc_create(self,
                                                                 super_client,
                                                                 client):

        env, service, consumed_service = create_env_with_2_svc(
            self.testname, client, self.service_scale,
            self.consumed_service_scale,
            self.port)

        service = activate_svc(client, service)
        link_svc(super_client, service, [consumed_service])
        consumed_service = activate_svc(client, consumed_service)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_activate_svc_link_activate_consumed_svc_validate(
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkLinkActivateConsumedSvcActivateSvc:

    testname = "TestLinkLinkActivateConsumedSvcActivateSvc"
    port = "304"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_link_activate_consumed_svc_activate_svc_create(self,
                                                            super_client,
                                                            client):

        env, service, consumed_service = create_env_with_2_svc(
            self.testname, client, self.service_scale,
            self.consumed_service_scale,
            self.port)

        link_svc(super_client, service, [consumed_service])
        consumed_service = activate_svc(client, consumed_service)
        service = activate_svc(client, service)
        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_activate_consumed_svc_activate_svc_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkLinkActivateSvcActivateConsumedSvc:

    testname = "TestLinkLinkActivateSvcActivateConsumedSvc"
    port = "305"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_link_activate_svc_activate_consumed_svc_create(self,
                                                            super_client,
                                                            client):

        env, service, consumed_service = create_env_with_2_svc(
            self.testname, client, self.service_scale,
            self.consumed_service_scale,
            self.port)

        link_svc(super_client, service, [consumed_service])
        service = activate_svc(client, service)
        consumed_service = activate_svc(client, consumed_service)
        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_activate_svc_activate_consumed_svc_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkLinkWhenServicesStillActivating:

    testname = "TestLinkLinkWhenServicesStillActivating"
    port = "306"
    service_scale = 1
    consumed_service_scale = 2

    @pytest.mark.create
    def test_link_link_when_services_still_activating_create(self,
                                                             super_client,
                                                             client):

        env, service, consumed_service = create_env_with_2_svc(
            self.testname, client, self.service_scale,
            self.consumed_service_scale,
            self.port)

        service.activate()
        consumed_service.activate()

        service.addservicelink(serviceLink={"serviceId": consumed_service.id})
        service = client.wait_success(service, 120)

        consumed_service = client.wait_success(consumed_service, 120)

        assert service.state == "active"
        assert consumed_service.state == "active"
        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_link_when_services_still_activating_validate(self,
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

        validate_add_service_link(super_client, service, consumed_service)

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServiceUp:

    testname = "TestLinkServiceUp"
    port = "307"
    service_scale = 1
    consumed_service_scale = 2
    final_service_scale = 3

    @pytest.mark.create
    def test_link_service_scale_up_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_service_scale_up_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServicesScaleDown:

    testname = "TestLinkServicesScaleDown"
    port = "308"
    service_scale = 3
    consumed_svc_scale = 2
    final_service_scale = 1

    @pytest.mark.create
    def test_link_services_scale_down_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_services_scale_down_validate(self, super_client, client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkConsumedServicesScaleUp:

    testname = "TestLinkConsumedServicesScaleUp"
    port = "309"
    service_scale = 1
    consumed_svc_scale = 2
    final_consumed_svc_scale = 4

    @pytest.mark.create
    def test_link_consumed_services_scale_up_create(self, super_client,
                                                    client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_consumed_services_scale_up_validate(self, super_client,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        consumed_service = client.update(consumed_service,
                                         scale=self.final_consumed_svc_scale,
                                         name=consumed_service.name)
        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"
        assert consumed_service.scale == self.final_consumed_svc_scale

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkConsumedServicesScaleDown:

    testname = "TestLinkConsumedServicesScaleDown"
    port = "310"
    service_scale = 2
    consumed_svc_scale = 3
    final_consumed_svc_scale = 1

    @pytest.mark.create
    def test_link_consumed_services_scale_down_create(self, super_client,
                                                      client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_consumed_services_scale_down_validate(self, super_client,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        consumed_service = client.update(consumed_service,
                                         scale=self.final_consumed_svc_scale,
                                         name=consumed_service.name)
        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"
        assert consumed_service.scale == self.final_consumed_svc_scale

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TesLinkConsumedServicesStopStartInstance:

    testname = "TesLinkConsumedServicesStopStartInstance"
    port = "311"
    service_scale = 1
    consumed_svc_scale = 3

    @pytest.mark.create
    def test_link_consumed_services_stop_start_instance_create(self,
                                                               super_client,
                                                               client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_consumed_services_stop_start_instance_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        container_name = env.name + "_" + consumed_service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Stop instance
        container = client.wait_success(container.stop(), 120)
        service = client.wait_success(service)

        wait_for_scale_to_adjust(super_client, consumed_service)

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkConsumedServicesRestartInstance:

    testname = "TestLinkConsumedServicesRestartInstance"
    port = "312"
    service_scale = 1
    consumed_svc_scale = 3

    @pytest.mark.create
    def test_link_consumed_services_restart_instance_create(self, super_client,
                                                            client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_consumed_services_restart_instance_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        container_name = env.name + "_" + consumed_service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Restart instance
        container = client.wait_success(container.restart(), 120)
        assert container.state == 'running'

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkConsumedServicesDeleteInstance:

    testname = "TestLinkConsumedServicesDeleteInstance"
    port = "313"
    service_scale = 1
    consumed_svc_scale = 3

    @pytest.mark.create
    def test_link_consumed_services_delete_instance_create(self, super_client,
                                                           client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client,
                                                    client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_consumed_services_delete_instance_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        container_name = env.name + "_" + consumed_service.name + "_1"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        container = containers[0]

        # Delete instance
        container = client.wait_success(client.delete(container))
        assert container.state == 'removed'

        wait_for_scale_to_adjust(super_client, consumed_service)

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkConsumedServicesDeactivateActivate:

    testname = "TestLinkConsumedServicesDeactivateActivate"
    port = "314"
    service_scale = 1
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_consumed_services_deactivate_activate_create(self,
                                                               super_client,
                                                               client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client,
                                                    client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_consumed_services_deactivate_activate_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        consumed_service = consumed_service.deactivate()
        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "inactive"
        wait_until_instances_get_stopped(super_client, consumed_service)

        consumed_service = consumed_service.activate()
        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServiceDeactivateActivate:

    testname = "TestLinkServiceDeactivateActivate"
    port = "315"
    service_scale = 1
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_service_deactivate_activate_create(self, super_client,
                                                     client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client,
                                                    client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_service_deactivate_activate_validate(self, super_client,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        service = service.deactivate()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"
        wait_until_instances_get_stopped(super_client, service)

        service = service.activate()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkDeactivateActivateEnvironment:

    testname = "TestLinkDeactivateActivateEnvironment"
    port = "316"
    service_scale = 1
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_deactivate_activate_environment_self_create(self,
                                                              super_client,
                                                              client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_deactivate_activate_environment_self_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        env = env.deactivateservices()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"

        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "inactive"

        wait_until_instances_get_stopped(super_client, consumed_service)

        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        consumed_service = client.wait_success(consumed_service, 120)
        assert consumed_service.state == "active"

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkAddRemoveServicelinks:

    testname = "TestLinkAddRemoveServicelinks"
    port = "317"
    service_scale = 1
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_add_remove_servicelinks_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client,
                                                    client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid,
                consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_add_remove_servicelinks_validate(self, super_client, client):

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
        logger.info("consumed service is: %s", format(consumed_service1))

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

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

        # Add another service link
        service.addservicelink(serviceLink={"serviceId": consumed_service1.id})
        validate_add_service_link(super_client, service, consumed_service1)

        validate_linked_service(super_client, service,
                                [consumed_service, consumed_service1],
                                self.port)

        # Remove existing service link to the service
        service.removeservicelink(
            serviceLink={"serviceId": consumed_service.id})
        validate_remove_service_link(super_client, service, consumed_service)

        validate_linked_service(super_client, service, [consumed_service1],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServicesDeleteServiceAddService:

    testname = "TestLinkServicesDeleteServiceAddService"
    port = "318"
    service_scale = 2
    consumed_svc_scale = 2
    port1 = "3180"

    @pytest.mark.create
    def test_link_services_delete_service_add_service_create(self,
                                                             super_client,
                                                             client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client,
                                                    client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_services_delete_service_add_service_validate(self,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        # Delete Service

        service = client.wait_success(client.delete(service))
        assert service.state == "removed"
        validate_remove_service_link(super_client, service, consumed_service)

        # Add another service and link to consumed service

        launch_config = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [self.port1+":22/tcp"]}

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

        service1.addservicelink(serviceLink={"serviceId": consumed_service.id})
        validate_add_service_link(super_client, service1, consumed_service)

        validate_linked_service(super_client, service1, [consumed_service],
                                self.port1)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServicesDeleteAndAddConsumedService:

    testname = "TestLinkServicesDeleteAndAddConsumedService"
    port = "319"
    service_scale = 2
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_services_delete_and_add_consumed_service_create(self,
                                                                  super_client,
                                                                  client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_services_delete_and_add_consumed_service_validate(
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        # Delete consume service

        consumed_service = client.wait_success(client.delete(consumed_service))
        assert consumed_service.state == "removed"
        validate_remove_service_link(super_client, service, consumed_service)

        # Add another consume service and link the service to this
        # newly created service

        launch_config = {"imageUuid": WEB_IMAGE_UUID}

        random_name = random_str()
        service_name = random_name.replace("-", "")
        consumed_service1 = client.create_service(name=service_name,
                                                  environmentId=env.id,
                                                  launchConfig=launch_config,
                                                  scale=1)
        consumed_service1 = client.wait_success(consumed_service1)
        assert consumed_service1.state == "inactive"

        consumed_service1 = consumed_service1.activate()
        consumed_service1 = client.wait_success(consumed_service1, 120)
        assert consumed_service1.state == "active"

        service.addservicelink(serviceLink={"serviceId": consumed_service1.id})
        validate_add_service_link(super_client, service, consumed_service1)

        validate_linked_service(super_client, service, [consumed_service1],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServicesStopStartInstance:

    testname = "TestLinkServicesStopStartInstance"
    port = "320"
    service_scale = 2
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_services_stop_start_instance_create(self, super_client,
                                                      client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client,
                                                    client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_services_stop_start_instance_validate(self, super_client,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # Stop service instance
        service_instance = client.wait_success(service_instance.stop(), 120)
        service = client.wait_success(service)
        wait_for_scale_to_adjust(super_client, service)

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServicesRestartInstance:

    testname = "TestLinkServicesRestartInstance"
    port = "321"
    service_scale = 2
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_services_restart_instance_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client,
                                                    client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_services_restart_instance_validate(self, super_client,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # Restart consumed instance
        service_instance = client.wait_success(service_instance.restart(), 120)
        assert service_instance.state == 'running'

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinkServicesDeleteInstance:

    testname = "TestLinkServicesDeleteInstance"
    port = "322"
    service_scale = 2
    consumed_svc_scale = 2

    @pytest.mark.create
    def test_link_services_delete_instance_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(self.testname,
                                                    super_client, client,
                                                    self.service_scale,
                                                    self.consumed_svc_scale,
                                                    self.port)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_link_services_delete_instance_validate(self, super_client,
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

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # Delete instance
        container = client.wait_success(client.delete(service_instance))
        assert container.state == 'removed'

        wait_for_scale_to_adjust(super_client, service)
        validate_linked_service(super_client, service, [consumed_service],
                                self.port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinksWithHostnetwork_1:

    testname = "TestLinksWithHostnetwork1"
    port = "323"
    service_scale = 1
    consumed_svc_scale = 2
    ssh_port = "33"

    @pytest.mark.create
    def test_links_with_hostnetwork_1_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_svc_scale, self.port, self.ssh_port,
                isnetworkModeHost_svc=False,
                isnetworkModeHost_consumed_svc=True)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_links_with_hostnetwork_1_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        validate_linked_service(super_client, service, [consumed_service],
                                self.port)
        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinksWithHostnetwork_2:

    testname = "TestLinksWithHostnetwork2"
    port = "324"
    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"

    @pytest.mark.create
    def test_links_with_hostnetwork_2_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port,
                self.ssh_port, isnetworkModeHost_svc=True,
                isnetworkModeHost_consumed_svc=True)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_links_with_hostnetwork_2_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        validate_linked_service(
            super_client, service, [consumed_service], self.ssh_port)

        delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServicesLinks
@pytest.mark.incremental
class TestLinksWithHostnetwork_3:

    testname = "TestLinksWithHostnetwork3"
    port = "325"
    service_scale = 1
    consumed_service_scale = 2
    ssh_port = "33"

    @pytest.mark.create
    def test_links_with_hostnetwork_3_create(self, super_client, client):

        env, service, consumed_service = \
            create_environment_with_linked_services(
                self.testname, super_client, client, self.service_scale,
                self.consumed_service_scale, self.port,
                self.ssh_port, isnetworkModeHost_svc=True,
                isnetworkModeHost_consumed_svc=False)

        data = [env.uuid, service.uuid, consumed_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_links_with_hostnetwork_3_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        consumed_service = client.list_service(uuid=data[2])[0]
        assert len(consumed_service) > 0
        logger.info("consumed service is: %s", format(consumed_service))

        validate_linked_service(
            super_client, service, [consumed_service], self.ssh_port)

        delete_all(client, [env])
