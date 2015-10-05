from common_fixtures import *  # NOQA


def activate_environment_with_external_services(
        testname, super_client, client, service_scale, port):

    env, service, ext_service, con_list = create_env_with_ext_svc(
        testname, client, service_scale, port)

    service.activate()
    ext_service.activate()
    service.addservicelink(serviceLink={"serviceId": ext_service.id})
    service = client.wait_success(service, 120)
    ext_service = client.wait_success(ext_service, 120)
    assert service.state == "active"
    assert ext_service.state == "active"
    validate_add_service_link(super_client, service, ext_service)

    return env, service, ext_service, con_list


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceActivateSvcActivateExternalSvcLink:

    testname = "TestExtServiceActivateSvcActivateExternalSvcLink"
    port = "3001"
    service_scale = 2

    @pytest.mark.create
    def test_extservice_activate_svc_activate_external_svc_link_create(
            self, super_client, client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]

        logger.info("data to save: %s", data)

        save(data, self)

    @pytest.mark.validate
    def test_extservice_activate_svc_activate_external_svc_link_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceActivateExternalSvcLinkActivateSvc:

    testname = "TestExtServiceActivateExternalSvcLinkActivateSvc"
    port = "3002"
    service_scale = 2

    @pytest.mark.create
    def test_extservice_activate_external_svc_link_activate_svc_create(
            self, super_client, client):

        env, service, ext_service, con_list = create_env_with_ext_svc(
            self.testname, client, self.service_scale, self.port)

        ext_service = activate_svc(client, ext_service)
        link_svc(super_client, service, [ext_service])
        service = activate_svc(client, service)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_activate_external_svc_link_activate_svc_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceActivateSvcLinkActivateExternalSvc:

    testname = "TestExtServiceActivateSvcLinkActivateExternalSvc"
    port = "3003"
    service_scale = 1

    @pytest.mark.create
    def test_extservice_activate_svc_link_activate_external_svc_create(
            self, super_client, client):

        env, service, ext_service, con_list = create_env_with_ext_svc(
            self.testname, client, self.service_scale, self.port)

        service = activate_svc(client, service)
        link_svc(super_client, service, [ext_service])
        ext_service = activate_svc(client, ext_service)
        validate_add_service_link(super_client, service, ext_service)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_activate_svc_link_activate_external_svc_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceLinkActivateExternalSvcActivateSvc:

    testname = "TestExtServiceLinkActivateExternalSvcActivateSvc"
    port = "3004"
    service_scale = 1

    @pytest.mark.create
    def test_extservice_link_activate_external_svc_activate_svc_create(
            self, super_client, client):

        env, service, ext_service, con_list = create_env_with_ext_svc(
            self.testname, client, self.service_scale, self.port)

        link_svc(super_client, service, [ext_service])
        ext_service = activate_svc(client, ext_service)
        service = activate_svc(client, service)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_link_activate_external_svc_activate_svc_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceLinkActivateSvcActivateExternalSvc:

    testname = "TestExtServiceLinkActivateSvcActivateExternalSvc"
    port = "3005"
    service_scale = 1

    @pytest.mark.create
    def test_extservice_link_activate_svc_activate_external_svc_create(
            self, super_client, client):

        env, service, ext_service, con_list = create_env_with_ext_svc(
            self.testname, client, self.service_scale, self.port)

        link_svc(super_client, service, [ext_service])
        service = activate_svc(client, service)
        ext_service = activate_svc(client, ext_service)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_link_activate_svc_activate_external_svc_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceLinkWhenServicesStillActivating:

    testname = "TestExtServiceLinkWhenServicesStillActivating"
    port = "3006"
    service_scale = 1

    @pytest.mark.create
    def test_extservice_link_when_services_still_activating_create(
            self, super_client, client):

        env, service, ext_service, con_list = create_env_with_ext_svc(
            self.testname, client, self.service_scale, self.port)

        service.activate()
        ext_service.activate()

        service.addservicelink(serviceLink={"serviceId": ext_service.id})
        service = client.wait_success(service, 120)
        ext_service = client.wait_success(ext_service, 120)

        assert service.state == "active"
        assert ext_service.state == "active"
        validate_add_service_link(super_client, service, ext_service)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_link_when_services_still_activating_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceScaleUp:

    testname = "TestExtServiceScaleUp"
    port = "3007"
    service_scale = 1
    final_service_scale = 3

    @pytest.mark.create
    def test_extservice_service_scale_up_create(self, super_client, client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(super_client, service,
                                  [ext_service], self.port, con_list)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_service_scale_up_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceServicesScaleDown:

    testname = "TestExtServiceServicesScaleDown"
    port = "3008"
    service_scale = 3
    final_service_scale = 1

    @pytest.mark.create
    def test_extservice_services_scale_down_create(self, super_client, client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(super_client, service,
                                  [ext_service], self.port, con_list)

        service = client.update(service, scale=self.final_service_scale,
                                name=service.name)
        service = client.wait_success(service, 120)
        assert service.state == "active"
        assert service.scale == self.final_service_scale

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_services_scale_down_validate(self, super_client,
                                                     client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceExtServicesDeactivateActivate:

    testname = "TestExtServiceExtServicesDeactivateActivate"
    port = "3014"
    service_scale = 1

    @pytest.mark.create
    def test_extservice_ext_services_deactivate_activate_create(self,
                                                                super_client,
                                                                client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)

        ext_service = ext_service.deactivate()
        ext_service = client.wait_success(ext_service, 120)
        assert ext_service.state == "inactive"

        ext_service = ext_service.activate()
        ext_service = client.wait_success(ext_service, 120)
        assert ext_service.state == "active"

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_ext_services_deactivate_activate_validate(self,
                                                                  super_client,
                                                                  client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceServiceDeactivateActivate:

    testname = "TestExtServiceServiceDeactivateActivate"
    port = "3015"
    service_scale = 1

    @pytest.mark.create
    def test_extservice_service_deactivate_activate_create(self, super_client,
                                                           client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(super_client, service, [ext_service],
                                  self.port, con_list)

        service = service.deactivate()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"
        wait_until_instances_get_stopped(super_client, service)

        service = service.activate()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_service_deactivate_activate_validate(self,
                                                             super_client,
                                                             client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)
        validate_external_service(super_client, service, [ext_service],
                                  self.port, con_list)

        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceDeactivateActivateEnvironment:

    testname = "TestExtServiceDeactivateActivateEnvironment"
    port = "3016"
    service_scale = 1

    @pytest.mark.create
    def test_extservice_deactivate_activate_environment_create(
            self, super_client, client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)

        env = env.deactivateservices()
        service = client.wait_success(service, 120)
        assert service.state == "inactive"

        ext_service = client.wait_success(ext_service, 120)
        assert ext_service.state == "inactive"

        wait_until_instances_get_stopped(super_client, service)

        env = env.activateservices()
        service = client.wait_success(service, 120)
        assert service.state == "active"

        ext_service = client.wait_success(ext_service, 120)
        assert ext_service.state == "active"

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_deactivate_activate_environment_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)
        validate_external_service(super_client, service, [ext_service],
                                  self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceServicesDeleteServiceAddService:

    testname = "TestExtServiceServicesDeleteServiceAddService"
    port = "3018"
    service_scale = 2
    port1 = "30180"

    @pytest.mark.create
    def test_extservice_services_delete_service_add_service_create(
            self, super_client, client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)

        # Delete Service

        service = client.wait_success(client.delete(service))
        assert service.state == "removed"
        validate_remove_service_link(super_client, service, ext_service)

        # Add another service and link to external service
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

        service1.addservicelink(serviceLink={"serviceId": ext_service.id})
        validate_add_service_link(super_client, service1, ext_service)

        data = [env.uuid, service1.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_services_delete_service_add_service_validate(
            self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service1 = client.list_service(uuid=data[1])[0]
        assert len(service1) > 0
        logger.info("service is: %s", format(service1))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)
        validate_external_service(super_client, service1,
                                  [ext_service], self.port1, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceDeleteAndAddExtService:

    testname = "TestExtServiceDeleteAndAddExtService"
    port = "3019"
    service_scale = 2

    @pytest.mark.create
    def test_extservice_delete_and_add_ext_service_create(self, super_client,
                                                          client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)

        # Delete external service

        ext_service = client.wait_success(client.delete(ext_service))
        assert ext_service.state == "removed"
        validate_remove_service_link(super_client, service, ext_service)

        # Add another external service and link the service to this newly
        # created external service

        c1 = client.create_container(name=random_str(),
                                     imageUuid=WEB_IMAGE_UUID)
        c2 = client.create_container(name=random_str(),
                                     imageUuid=WEB_IMAGE_UUID)

        c1 = client.wait_success(c1, 120)
        assert c1.state == "running"
        c2 = client.wait_success(c2, 120)
        assert c2.state == "running"

        con_list = [c1, c2]
        ips = [c1.primaryIpAddress, c2.primaryIpAddress]

        # Create external Service
        random_name = random_str()
        ext_service_name = random_name.replace("-", "")

        ext_service1 = client.create_externalService(
            name=ext_service_name, environmentId=env.id,
            externalIpAddresses=ips)
        ext_service1 = client.wait_success(ext_service1)
        ext_service1 = activate_svc(client, ext_service1)

        service.addservicelink(serviceLink={"serviceId": ext_service1.id})

        validate_add_service_link(super_client, service, ext_service1)

        data = [env.uuid, service.uuid, ext_service1.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_delete_and_add_ext_service_validate(self,
                                                            super_client,
                                                            client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service1 = client.list_service(uuid=data[2])[0]
        assert len(ext_service1) > 0
        logger.info("ext_service is: %s", format(ext_service1))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(super_client, service, [ext_service1],
                                  self.port,
                                  con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceServicesStopStartInstance:

    testname = "TestExtServiceServicesStopStartInstance"
    port = "3020"
    service_scale = 2

    @pytest.mark.create
    def test_extservice_services_stop_start_instance_create(self,
                                                            super_client,
                                                            client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(super_client, service,
                                  [ext_service], self.port, con_list)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # Stop service instance
        service_instance = client.wait_success(service_instance.stop(), 120)
        service = client.wait_success(service)
        wait_for_scale_to_adjust(super_client, service)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_services_stop_start_instance_validate(self,
                                                              super_client,
                                                              client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(super_client, service, [ext_service],
                                  self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceServicesRestartInstance:

    testname = "TestExtServiceServicesRestartInstance"
    port = "3021"
    service_scale = 2

    @pytest.mark.create
    def test_extservice_services_restart_instance_create(self, super_client,
                                                         client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(
                self.testname, super_client, client, self.service_scale,
                self.port)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)

        container_name = env.name + "_" + service.name + "_2"
        containers = client.list_container(name=container_name)
        assert len(containers) == 1
        service_instance = containers[0]

        # Restart external instance
        service_instance = client.wait_success(service_instance.restart(), 120)
        assert service_instance.state == 'running'

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_services_restart_instance_validate(self, super_client,
                                                           client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(super_client, service,
                                  [ext_service], self.port, con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceAddAndDeleteIps:

    testname = "TestExtServiceAddAndDeleteIps"
    port = "3023"
    service_scale = 2

    @pytest.mark.create
    def test_extservice_add_and_delete_ips_create(self, super_client, client):

        env, service, ext_service, con_list = \
            activate_environment_with_external_services(self.testname,
                                                        super_client,
                                                        client,
                                                        self.service_scale,
                                                        self.port)

        validate_external_service(
            super_client, service, [ext_service], self.port, con_list)

        # Update external Service to add one more ip

        c1 = client.create_container(name=random_str(),
                                     imageUuid=WEB_IMAGE_UUID)
        c1 = client.wait_success(c1, 120)
        assert c1.state == "running"

        ips = [con_list[0].primaryIpAddress, con_list[1].primaryIpAddress,
               c1.primaryIpAddress]
        con_list.append(c1)
        ext_service = client.update(
            ext_service, name=ext_service.name, externalIpAddresses=ips)
        ext_service = client.wait_success(ext_service, 120)

        validate_external_service(super_client, service, [ext_service],
                                  self.port,
                                  con_list)

        # Update external Service to remove one of the existing ips

        ips = [con_list[1].primaryIpAddress, c1.primaryIpAddress]
        con_list.pop(0)
        ext_service = client.update(
            ext_service, name=ext_service.name, externalIpAddresses=ips)
        ext_service = client.wait_success(ext_service, 120)

        data = [env.uuid, service.uuid, ext_service.uuid,
                [con.uuid for con in con_list]]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_add_and_delete_ips_validate(self, super_client,
                                                    client):
        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        con_list = \
            [client.list_container(uuid=con_uuid)[0] for con_uuid in data[3]]
        logger.info("con_list: %s", con_list)

        validate_external_service(super_client, service, [ext_service],
                                  self.port,
                                  con_list)
        con_list.append(env)
        delete_all(client, con_list)


@pytest.mark.P0
@pytest.mark.ExtServiceLinks
@pytest.mark.incremental
class TestExtServiceWithCname:

    testname = "TestExtServiceWithCname"
    port = "3024"
    service_scale = 2

    @pytest.mark.create
    def test_extservice_with_cname_create(self, super_client, client):

        env, service, ext_service, con_list = create_env_with_ext_svc(
            self.testname, client, self.service_scale, self.port, True)

        ext_service = activate_svc(client, ext_service)
        link_svc(super_client, service, [ext_service])
        service = activate_svc(client, service)

        data = [env.uuid, service.uuid, ext_service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_extservice_with_cname_validate(self, super_client, client):

        data = load(self)

        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))

        ext_service = client.list_service(uuid=data[2])[0]
        assert len(ext_service) > 0
        logger.info("ext_service is: %s", format(ext_service))

        validate_external_service_for_hostname(
            super_client, service, [ext_service], self.port)

        delete_all(client, [env])
