from common_fixtures import *  # NOQA
import time
import datetime

wp42 = "docker:wordpress:4.2"
wp43 = "docker:wordpress:4.3"
maria_db_image_uuid = "docker:mariadb"
ssh_image_uuid = "docker:sangeetha/testclient:latest"

"""
This test performs a in-service upgrade of a service with one simple primary
with added label and verifies service is upgraded and new labels exist in
containers after upgrade. Also verifies that during upgrade, new containers are
created first before old containers are deleted.
"""


@pytest.mark.P1
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradePrimaryOnly1:
    testname = "TestInServiceUpgradePrimaryOnly1"

    launch_config = {"imageUuid": ssh_image_uuid,
                     "networkMode": "managed",
                     "restartPolicy": {
                         "name": "always",
                     },
                     "stdinOpen": True,
                     "tty": True,
                     "privileged": False,
                     "publishAllPorts": False,
                     "readOnly": False,
                     "startOnCreate": True,
                     "version": "0",
                     }

    scale_svc = 10
    batchSize = 2
    num_lcs = 1
    upgrade_timeout = ((num_lcs * scale_svc) / batchSize) * 120

    @pytest.mark.create
    def test_inservice_upgrade_primary1_create(self, super_client,
                                               client, socat_containers):

        env = create_env(self.testname, client)

        service_name = "test"
        service = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config,
            scale=self.scale_svc)
        service = client.wait_success(service)
        service = client.wait_success(service.activate(), timeout=120)
        check_container_in_service(super_client, service)

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_upgrade_primary_simple_validate(self,
                                                       super_client,
                                                       client,
                                                       socat_containers,
                                                       **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        service = service.upgrade_action(
            launchConfig={'labels': {'foo': "bar"}}, )
        assert service.state == 'upgrading'
        # This assert is to make sure during upgrade new containers are deleted
        # first before new ones are created
        assert len(get_container_list(super_client, service)) > self.scale_svc
        upgraded_cons = []
        while (len(upgraded_cons) < self.scale_svc):
            container_list = get_container_list(super_client, service)
            for container in container_list:
                labels = {'foo': "bar"}
                for item in labels:
                    if item in container.labels:
                        upgraded_cons.append(container.name)
                logger.info(
                    "upgrade containers length: %s - %s",
                    datetime.datetime.now(), len(list(set(upgraded_cons))))
                time.sleep(5)

        def upgrade_not_null():
            s = client.reload(service)
            if s.upgrade is not None:
                return s

        service = wait_for(upgrade_not_null)
        service = client.wait_success(service, self.upgrade_timeout)
        assert service.state == 'active'
        container_list = get_container_list(super_client, service)
        assert len(container_list) == service.scale

        for container in container_list:
            assert container.state == "running"
            containers = super_client.list_container(
                externalId=container.externalId,
                include="hosts",
                removed_null=True)
            docker_client = get_docker_client(containers[0].hosts[0])
            inspect = docker_client.inspect_container(container.externalId)
            logger.info("Checked for containers running - " + container.name)
            assert inspect["State"]["Running"]
            labels = {'foo': "bar"}
            assert all(item in container.labels for item in labels) is True

            # delete_all(client, [env])


"""
This test performs a in-service upgrade of a service with one simple primary
with added label multiple times consecutively and verifies service is upgraded
and verify every time new labels exist in containers after upgrade.
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradePrimaryOnlyConsecutive1:
    testname = "TestInServiceUpgradePrimaryOnlyConsecutive1"

    launch_config = {"imageUuid": ssh_image_uuid,
                     "networkMode": "managed",
                     "restartPolicy": {
                         "name": "always",
                     },
                     "stdinOpen": True,
                     "tty": True,
                     "privileged": False,
                     "publishAllPorts": False,
                     "readOnly": False,
                     "startOnCreate": True,
                     "version": "0",
                     }

    scale_svc = 4
    batchSize = 2
    num_lcs = 1
    upgrade_timeout = ((num_lcs * scale_svc) / batchSize) * 120
    labels = [{'foo': "bar"+str(x)} for x in range(1, 3)]

    @pytest.mark.create
    def test_inservice_upgrade_primary_only_consecutive_create(
            self, super_client, client, socat_containers):

        env = create_env(self.testname, client)

        service_name = "test"
        service = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config,
            scale=self.scale_svc)
        service = client.wait_success(service)
        service = client.wait_success(service.activate(), timeout=120)
        check_container_in_service(super_client, service)

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    @pytest.mark.timeout(300)
    def test_inservice_upgrade_primary_only_consecutive_validate(
            self, super_client,
            client,
            socat_containers,
            **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        def upgrade(service, label):
                service = service.upgrade_action(
                    launchConfig={'labels': label}, )
                assert service.state == 'upgrading'
                upgraded_cons = []
                while len(upgraded_cons) < self.scale_svc:
                    container_list = get_service_container_list(super_client,
                                                                service)
                    for container in container_list:
                        for item in label:
                            if (item in container.labels):
                                upgraded_cons.append(container.name)
                        logger.info(
                            "upgrade containers length: %s - %s",
                            datetime.datetime.now(),
                            len(list(set(upgraded_cons))))
                        time.sleep(5)

                def upgrade_not_null():
                    s = client.reload(service)
                    if s.upgrade is not None:
                        return s

                service = wait_for(upgrade_not_null, 180)
                service = client.wait_success(service, self.upgrade_timeout)
                assert service.state == 'active'
                container_list = get_service_container_list(super_client,
                                                            service)
                assert len(container_list) == service.scale

                for container in container_list:
                    assert container.state == "running"
                    containers = super_client.list_container(
                        externalId=container.externalId,
                        include="hosts",
                        removed_null=True)
                    docker_client = get_docker_client(containers[0].hosts[0])
                    inspect = docker_client.inspect_container(
                        container.externalId)
                    logger.info(
                        "Checked for containers running - " + container.name)
                    assert inspect["State"]["Running"]
                    assert all(
                        item in container.labels for item in label) is True
                    logger.info("upgraded service with label %s", label)

        for label in self.labels:
            logger.info("Upgrading service with label %s", label)
            upgrade(service, label)

        # delete_all(client, [env])


"""
This test performs a in-service upgrade of a service with one simple primary
with added label multiple times consecutively and verifies service is upgraded
and verify every time new labels exist in containers after upgrade.
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradePrimaryOnlyConsecutive2:
    testname = "TestInServiceUpgradePrimaryOnlyConsecutive2"

    launch_config = {"imageUuid": ssh_image_uuid,
                     "networkMode": "managed",
                     "restartPolicy": {
                         "name": "always",
                     },
                     "stdinOpen": True,
                     "tty": True,
                     "privileged": False,
                     "publishAllPorts": False,
                     "readOnly": False,
                     "startOnCreate": True,
                     "version": "0",
                     }

    scale_svc = 4
    batchSize = 2
    num_lcs = 1
    upgrade_timeout = ((num_lcs * scale_svc) / batchSize) * 120
    labels = [{'foo': "bar"+str(x)} for x in range(1, 10)]

    @pytest.mark.create
    def test_inservice_upgrade_primary_only_consecutive_create(
            self, super_client, client, socat_containers):

        env = create_env(self.testname, client)

        service_name = "test"
        service = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config,
            scale=self.scale_svc)
        service = client.wait_success(service)
        service = client.wait_success(service.activate(), timeout=120)
        check_container_in_service(super_client, service)

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    @pytest.mark.timeout(300)
    def test_inservice_upgrade_primary_only_consecutive_validate(
            self, super_client,
            client,
            socat_containers,
            **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        def upgrade(service, label):
                service = service.upgrade_action(
                    launchConfig={'labels': label}, )
                assert service.state == 'upgrading'
                upgraded_cons = []
                while len(upgraded_cons) < self.scale_svc:
                    container_list = get_service_container_list(super_client,
                                                                service)
                    for container in container_list:
                        for item in label:
                            if (item in container.labels):
                                upgraded_cons.append(container.name)
                        logger.info(
                            "upgrade containers length: %s - %s",
                            datetime.datetime.now(),
                            len(list(set(upgraded_cons))))
                        time.sleep(5)

                def upgrade_not_null():
                    s = client.reload(service)
                    if s.upgrade is not None:
                        return s

                service = wait_for(upgrade_not_null, 180)
                service = client.wait_success(service, self.upgrade_timeout)
                assert service.state == 'active'
                container_list = get_service_container_list(super_client,
                                                            service)
                assert len(container_list) == service.scale

                for container in container_list:
                    assert container.state == "running"
                    containers = super_client.list_container(
                        externalId=container.externalId,
                        include="hosts",
                        removed_null=True)
                    docker_client = get_docker_client(containers[0].hosts[0])
                    inspect = docker_client.inspect_container(
                        container.externalId)
                    logger.info(
                        "Checked for containers running - " + container.name)
                    assert inspect["State"]["Running"]
                    assert all(
                        item in container.labels for item in label) is True
                    logger.info("upgraded service with label %s", label)

        for label in self.labels:
            logger.info("Upgrading service with label %s", label)
            upgrade(service, label)

        # delete_all(client, [env])


"""
This test performs a in-service upgrade of a service with one simple primary
with added label and verifies service is upgraded and new labels exist in
containers after upgrade.
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradePrimaryOnly2:
    testname = "TestInServiceUpgradePrimaryOnly2"

    launch_config = {"imageUuid": ssh_image_uuid,
                     "networkMode": "managed",
                     "restartPolicy": {
                         "name": "always",
                     },
                     "stdinOpen": True,
                     "tty": True,
                     "privileged": False,
                     "publishAllPorts": False,
                     "readOnly": False,
                     "startOnCreate": True,
                     "version": "0",
                     }

    scale_svc = 3

    @pytest.mark.create
    def test_inservice_upgrade_primary2_create(self, super_client,
                                               client, socat_containers):

        env = create_env(self.testname, client)

        service_name = "test"
        service = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config,
            scale=self.scale_svc)
        service = client.wait_success(service)
        service = client.wait_success(service.activate(), timeout=120)
        check_container_in_service(super_client, service)

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_upgrade_primary2_validate(self,
                                                 super_client,
                                                 client,
                                                 socat_containers,
                                                 **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        service = service.upgrade_action(
            launchConfig={'labels': {'foo': "bar"}})
        assert service.state == 'upgrading'

        def upgrade_not_null():
            s = client.reload(service)
            if s.upgrade is not None:
                return s

        service = wait_for(upgrade_not_null)

        service = client.wait_success(service, timeout=120)
        assert service.state == 'active'
        container_list = get_service_container_list(super_client, service)
        assert len(container_list) == service.scale

        for container in container_list:
            assert container.state == "running"
            containers = super_client.list_container(
                externalId=container.externalId,
                include="hosts",
                removed_null=True)
            docker_client = get_docker_client(containers[0].hosts[0])
            inspect = docker_client.inspect_container(container.externalId)
            logger.info("Checked for containers running - " + container.name)
            assert inspect["State"]["Running"]
            labels = {'foo': "bar"}
            assert all(item in container.labels for item in labels) is True

            # delete_all(client, [env])


"""
This test performs a in-service upgrade and while upgrade is in progres,
cancels the upgrade and verifies that cancel worked and verifies all the
containers in the service are active again.
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceCancelUpgrade:
    testname = "TestInServiceCancelUpgrade"

    launch_config = {"imageUuid": ssh_image_uuid,
                     "networkMode": "managed",
                     "restartPolicy": {
                         "name": "always",
                     },
                     "stdinOpen": True,
                     "tty": True,
                     "privileged": False,
                     "publishAllPorts": False,
                     "readOnly": False,
                     "startOnCreate": True,
                     "version": "0",
                     }

    scale_svc = 25

    @pytest.mark.create
    def test_inservice_cancel_upgrade_create(self, super_client,
                                             client, socat_containers):

        env = create_env(self.testname, client)

        service_name = "test"
        service = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config,
            scale=self.scale_svc)
        service = client.wait_success(service)
        service = client.wait_success(service.activate(), timeout=120)
        check_container_in_service(super_client, service)

        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_cancel_upgrade_validate(
            self, super_client, client, socat_containers, **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        service = service.upgrade_action(
            launchConfig={'labels': {'foo': "bar"}}, )
        assert service.state == 'upgrading'
        time.sleep(10)
        logger.info("Canceling upgrade now..")
        out = service.cancelupgrade()
        assert out.state == "canceling-upgrade"
        service = client.wait_success(service, timeout=120)
        assert service.state == 'active'
        container_list = get_service_container_list(super_client, service)
        assert len(container_list) == service.scale

        upgraded_list = []
        for container in container_list:
            assert container.state == "running"
            containers = super_client.list_container(
                externalId=container.externalId,
                include="hosts",
                removed_null=True)
            docker_client = get_docker_client(containers[0].hosts[0])
            inspect = docker_client.inspect_container(container.externalId)
            logger.info("Checked for containers running - " + container.name)
            assert inspect["State"]["Running"]
            labels = {'foo': "bar"}
            for item in labels:
                if (item in container.labels):
                    upgraded_list.append(container.name)
            logger.info("upgrade container list: %s", upgraded_list)
            assert len(list(set(upgraded_list))) < self.scale_svc

            # delete_all(client, [env])


"""
This test performs a in-service upgrade of a wordpress service with newer
image and verifies service is upgraded with target image and there was no
downtime during upgrade.
batchSize=2
intervalMillis=100
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradePrimaryOnlyWithDNS1:
    testname = "TestInServiceUpgradePrimary3"

    restart_policy = {"name": "always"}
    env_var = {"MYSQL_ROOT_PASSWORD": "example"}
    launch_config_db = {"imageUuid": maria_db_image_uuid,
                        "environment": env_var,
                        "stdinOpen": True,
                        "tty": True,
                        "restartPolicy": restart_policy,
                        }

    launch_config_wp42 = {"imageUuid": wp42,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_config_wp43 = {"imageUuid": wp43,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_dns_client_config = {"imageUuid": ssh_image_uuid,
                                "networkMode": "managed",
                                "restartPolicy": {
                                    "name": "always",
                                },
                                "stdinOpen": True,
                                "tty": True,
                                "privileged": False,
                                "publishAllPorts": False,
                                "readOnly": False,
                                "startOnCreate": True,
                                "version": "0",
                                }

    scale_svc_wp42 = 10
    scale_svc_db = 3
    scale_svc_client = 1

    @pytest.mark.create
    def test_inservice_upgrade_primary3_create(self, super_client,
                                               client, socat_containers):
        env = create_env(self.testname, client)

        service_name = "db"
        service1 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config_db,
            scale=self.scale_svc_db)
        service1 = client.wait_success(service1)
        service1 = client.wait_success(service1.activate(), timeout=120)
        check_container_in_service(super_client, service1)

        service_name = "wordpress"
        service2 = client.create_service(name=service_name,
                                         environmentId=env.id,
                                         launchConfig=self.launch_config_wp42,
                                         scale=self.scale_svc_wp42)
        service2 = client.wait_success(service2)
        service2 = client.wait_success(service2.activate(), timeout=300)
        check_container_in_service(super_client, service2)

        # Create DNS service
        dns = client.create_dnsService(name='wpalias',
                                       environmentId=env.id)
        dns = client.wait_success(dns, 300)
        assert dns.state == "inactive"
        dns = client.wait_success(dns.activate(), timeout=120)

        service_name = "dnsclient"
        service3 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_dns_client_config, scale=1)
        service3 = client.wait_success(service3)
        service3 = client.wait_success(service3.activate(), timeout=300)

        service_link = {"serviceId": service1.id}
        service2.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": service1.id}
        dns.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": dns.id}
        service3.addservicelink(serviceLink=service_link)

        data = [env.uuid, service2.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_upgrade_primary3_validate(self,
                                                 super_client,
                                                 client,
                                                 socat_containers, **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        service = service.upgrade_action(launchConfig={"imageUuid": wp43},
                                         batchSize=2,
                                         finalScale=2,
                                         intervalMillis=100)

        assert service.state == 'upgrading'

        def upgrade_not_null():
            s = client.reload(service)
            if s.upgrade is not None:
                return s

        service = wait_for(upgrade_not_null)

        service = client.wait_success(service, timeout=120)
        assert service.state == 'active'

        # delete_all(client, [env])


"""
This test performs a in-service upgrade of a wordpress service with newer
image, modified/new launchConfig params and verifies service is upgraded with
target image and there was no downtime during upgrade.
batchSize=4
intervalMillis=200
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradeSecondaryOnlySidekick:
    testname = "TestInServiceUpgradeSecondaryOnlySidekick"
    scale_svc = 10
    primary_launch_config = {"dataVolumesFromLaunchConfigs": ["test-data", ],
                             "imageUuid": "docker:ubuntu:14.04.2",
                             "labels": {

                                 "io.rancher.sidekicks": "test-data",

                             },
                             "logConfig": {},
                             "networkMode": "managed",
                             "stdinOpen": True,
                             "tty": True,
                             "privileged": False,
                             "publishAllPorts": False,
                             "readOnly": False,
                             "startOnCreate": True,
                             "version": "0",
                             }

    secondary_launch_config = [

        {
            "command": [
                "cat",
            ],
            "imageUuid": "docker:ubuntu:14.04.2",
            "logConfig": {},
            "name": "test-data",
            "networkMode": "managed",
            "stdinOpen": True,
            "tty": True,
            "privileged": True,
            "publishAllPorts": False,
            "readOnly": False,
            "startOnCreate": True,
            "version": "0",
        },

    ]

    @pytest.mark.create
    def test_inservice_upgrade_secondary_create(self, super_client,
                                                client, socat_containers):
        env = create_env(self.testname, client)

        service_name = "test"
        service = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.primary_launch_config,
            secondaryLaunchConfigs=self.secondary_launch_config,
            scale=self.scale_svc)
        service = client.wait_success(service)
        service = client.wait_success(service.activate(), timeout=120)
        data = [env.uuid, service.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_upgrade_secondary_validate(self,
                                                  super_client,
                                                  client,
                                                  socat_containers, **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"
        secondary = [{'name': "test-data", 'labels': {'foo': "bar"}}]

        service = service.upgrade_action(secondaryLaunchConfigs=secondary)
        assert service.state == 'upgrading'

        def upgrade_not_null():
            s = client.reload(service)
            if s.upgrade is not None:
                return s

        service = wait_for(upgrade_not_null)

        service = client.wait_success(service, timeout=300)
        assert service.state == 'active'

        container_list = get_service_container_list(super_client, service)
        assert len(container_list) == service.scale

        upgraded_list = []
        for container in container_list:
            assert container.state == "running"
            containers = super_client.list_container(
                externalId=container.externalId,
                include="hosts",
                removed_null=True)
            docker_client = get_docker_client(containers[0].hosts[0])
            inspect = docker_client.inspect_container(container.externalId)
            logger.info("Checked for containers running - " + container.name)
            assert inspect["State"]["Running"]
            labels = {'foo': "bar"}
            for item in labels:
                if (item in container.labels):
                    upgraded_list.append(container.name)
            logger.info("upgrade container list: %s", upgraded_list)
            assert len(list(set(upgraded_list))) == (self.scale_svc * 2)

            # delete_all(client, [env])


"""
This test performs a in-service upgrade of a wordpress service with newer
image, modified/new launchConfig params and verifies service is upgraded with
target image and there was no downtime during upgrade.
batchSize=4
intervalMillis=200
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradeSecondaryMultipleSidekick:
    testname = "TestInServiceUpgradePrimary3"

    restart_policy = {"name": "always"}
    env_var = {"MYSQL_ROOT_PASSWORD": "example"}
    launch_config_db = {"imageUuid": maria_db_image_uuid,
                        "environment": env_var,
                        "stdinOpen": True,
                        "tty": True,
                        "restartPolicy": restart_policy,
                        }

    launch_config_wp42 = {"imageUuid": wp42,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_config_wp43 = {"imageUuid": wp43,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_dns_client_config = {"imageUuid": ssh_image_uuid,
                                "networkMode": "managed",
                                "restartPolicy": {
                                    "name": "always",
                                },
                                "stdinOpen": True,
                                "tty": True,
                                "privileged": False,
                                "publishAllPorts": False,
                                "readOnly": False,
                                "startOnCreate": True,
                                "version": "0",
                                }

    scale_svc_wp42 = 3
    scale_svc_db = 3
    scale_svc_client = 1

    @pytest.mark.create
    def test_inservice_upgrade_primary3_create(self, super_client,
                                               client, socat_containers):
        env = create_env(self.testname, client)

        service_name = "db"
        service1 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config_db,
            scale=self.scale_svc_db)
        service1 = client.wait_success(service1)
        service1 = client.wait_success(service1.activate(), timeout=120)
        check_container_in_service(super_client, service1)

        service_name = "wordpress"
        service2 = client.create_service(name=service_name,
                                         environmentId=env.id,
                                         launchConfig=self.launch_config_wp42,
                                         scale=self.scale_svc_wp42)
        service2 = client.wait_success(service2)
        service2 = client.wait_success(service2.activate(), timeout=300)
        check_container_in_service(super_client, service2)

        # Create DNS service
        dns = client.create_dnsService(name='wpalias',
                                       environmentId=env.id)
        dns = client.wait_success(dns, 300)
        assert dns.state == "inactive"
        dns = client.wait_success(dns.activate(), timeout=120)

        service_name = "dnsclient"
        service3 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_dns_client_config, scale=1)
        service3 = client.wait_success(service3)
        service3 = client.wait_success(service3.activate(), timeout=300)

        service_link = {"serviceId": service1.id}
        service2.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": service1.id}
        dns.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": dns.id}
        service3.addservicelink(serviceLink=service_link)

        data = [env.uuid, service2.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_upgrade_primary3_validate(self,
                                                 super_client,
                                                 client,
                                                 socat_containers, **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        service = service.upgrade_action(launchConfig={"imageUuid": wp43})
        assert service.state == 'upgrading'

        def upgrade_not_null():
            s = client.reload(service)
            if s.upgrade is not None:
                return s

        service = wait_for(upgrade_not_null)

        service = client.wait_success(service, timeout=120)
        assert service.state == 'active'

        # delete_all(client, [env])


"""
This test performs a in-service upgrade of multiple sidekick services with
newer image, modified/new launchConfig params and verifies all
sidekick services are upgraded with target image and there was no downtime
during upgrade. Also, verify primary service is not upgraded though it is
re-started and re-deployed
batchSize=4
intervalMillis=100
"""


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradeSecondaryMultipleSidekick:
    testname = "TestInServiceUpgradePrimary3"

    restart_policy = {"name": "always"}
    env_var = {"MYSQL_ROOT_PASSWORD": "example"}
    launch_config_db = {"imageUuid": maria_db_image_uuid,
                        "environment": env_var,
                        "stdinOpen": True,
                        "tty": True,
                        "restartPolicy": restart_policy,
                        }

    launch_config_wp42 = {"imageUuid": wp42,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_config_wp43 = {"imageUuid": wp43,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_dns_client_config = {"imageUuid": ssh_image_uuid,
                                "networkMode": "managed",
                                "restartPolicy": {
                                    "name": "always",
                                },
                                "stdinOpen": True,
                                "tty": True,
                                "privileged": False,
                                "publishAllPorts": False,
                                "readOnly": False,
                                "startOnCreate": True,
                                "version": "0",
                                }

    scale_svc_wp42 = 3
    scale_svc_db = 3
    scale_svc_client = 1

    @pytest.mark.create
    def test_inservice_upgrade_primary3_create(self, super_client,
                                               client, socat_containers):
        env = create_env(self.testname, client)

        service_name = "db"
        service1 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config_db,
            scale=self.scale_svc_db)
        service1 = client.wait_success(service1)
        service1 = client.wait_success(service1.activate(), timeout=120)
        check_container_in_service(super_client, service1)

        service_name = "wordpress"
        service2 = client.create_service(name=service_name,
                                         environmentId=env.id,
                                         launchConfig=self.launch_config_wp42,
                                         scale=self.scale_svc_wp42)
        service2 = client.wait_success(service2)
        service2 = client.wait_success(service2.activate(), timeout=300)
        check_container_in_service(super_client, service2)

        # Create DNS service
        dns = client.create_dnsService(name='wpalias',
                                       environmentId=env.id)
        dns = client.wait_success(dns, 300)
        assert dns.state == "inactive"
        dns = client.wait_success(dns.activate(), timeout=120)

        service_name = "dnsclient"
        service3 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_dns_client_config, scale=1)
        service3 = client.wait_success(service3)
        service3 = client.wait_success(service3.activate(), timeout=300)

        service_link = {"serviceId": service1.id}
        service2.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": service1.id}
        dns.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": dns.id}
        service3.addservicelink(serviceLink=service_link)

        data = [env.uuid, service2.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_upgrade_primary3_validate(self,
                                                 super_client,
                                                 client,
                                                 socat_containers, **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        service = service.upgrade_action(launchConfig={"imageUuid": wp43})
        assert service.state == 'upgrading'

        def upgrade_not_null():
            s = client.reload(service)
            if s.upgrade is not None:
                return s

        service = wait_for(upgrade_not_null)

        service = client.wait_success(service, timeout=120)
        assert service.state == 'active'

        # delete_all(client, [env])


@pytest.mark.P0
@pytest.mark.ServiceUpgrade
@pytest.mark.incremental
class TestInServiceUpgradeAll:
    testname = "TestInServiceUpgradeAll"

    restart_policy = {"name": "always"}
    env_var = {"MYSQL_ROOT_PASSWORD": "example"}
    launch_config_db = {"imageUuid": maria_db_image_uuid,
                        "environment": env_var,
                        "stdinOpen": True,
                        "tty": True,
                        "restartPolicy": restart_policy,
                        }

    launch_config_wp42 = {"imageUuid": wp42,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_config_wp43 = {"imageUuid": wp43,
                          "networkMode": "managed",
                          "ports": [
                              "8080:80/tcp",
                          ],
                          "restartPolicy": {
                              "name": "always",
                          },
                          "stdinOpen": True,
                          "tty": True,
                          "privileged": False,
                          "publishAllPorts": False,
                          "readOnly": False,
                          "startOnCreate": True,
                          "version": "0",
                          }

    launch_dns_client_config = {"imageUuid": ssh_image_uuid,
                                "networkMode": "managed",
                                "restartPolicy": {
                                    "name": "always",
                                },
                                "stdinOpen": True,
                                "tty": True,
                                "privileged": False,
                                "publishAllPorts": False,
                                "readOnly": False,
                                "startOnCreate": True,
                                "version": "0",
                                }

    scale_svc_wp42 = 3
    scale_svc_db = 3
    scale_svc_client = 1

    @pytest.mark.create
    def test_inservice_upgrade_all_create(self, super_client,
                                          client, socat_containers):
        env = create_env(self.testname, client)

        service_name = "db"
        service1 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_config_db,
            scale=self.scale_svc_db)
        service1 = client.wait_success(service1)
        service1 = client.wait_success(service1.activate(), timeout=120)
        check_container_in_service(super_client, service1)

        service_name = "wordpress"
        service2 = client.create_service(name=service_name,
                                         environmentId=env.id,
                                         launchConfig=self.launch_config_wp42,
                                         scale=self.scale_svc_wp42)
        service2 = client.wait_success(service2)
        service2 = client.wait_success(service2.activate(), timeout=300)
        check_container_in_service(super_client, service2)

        # Create DNS service
        dns = client.create_dnsService(name='wpalias',
                                       environmentId=env.id)
        dns = client.wait_success(dns, 300)
        assert dns.state == "inactive"
        dns = client.wait_success(dns.activate(), timeout=120)

        service_name = "dnsclient"
        service3 = client.create_service(
            name=service_name, environmentId=env.id,
            launchConfig=self.launch_dns_client_config, scale=1)
        service3 = client.wait_success(service3)
        service3 = client.wait_success(service3.activate(), timeout=300)

        service_link = {"serviceId": service1.id}
        service2.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": service1.id}
        dns.addservicelink(serviceLink=service_link)
        service_link = {"serviceId": dns.id}
        service3.addservicelink(serviceLink=service_link)

        data = [env.uuid, service2.uuid]
        logger.info("data to save: %s", data)
        save(data, self)

    @pytest.mark.validate
    def test_inservice_upgrade_all_validate(self,
                                            super_client,
                                            client,
                                            socat_containers, **kw):
        data = load(self)
        env = client.list_environment(uuid=data[0])[0]
        logger.info("env is: %s", format(env))

        service = client.list_service(uuid=data[1])[0]
        assert len(service) > 0
        logger.info("service is: %s", format(service))
        assert service.state == "active"

        service = service.upgrade_action(launchConfig={"imageUuid": wp43})
        assert service.state == 'upgrading'

        def upgrade_not_null():
            s = client.reload(service)
            if s.upgrade is not None:
                return s

        service = wait_for(upgrade_not_null)

        service = client.wait_success(service, timeout=120)
        assert service.state == 'active'

        # delete_all(client, [env])


def check_container_in_service(super_client, service):
    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == service.scale

    for container in container_list:
        assert container.state == "running"
        containers = super_client.list_container(
            externalId=container.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(container.externalId)
        logger.info("Checked for containers running - " + container.name)
        assert inspect["State"]["Running"]


def get_container_list(super_client, service):

    logger.debug("service is: %s", format(service))
    container = []
    all_instance_maps = \
        super_client.list_serviceExposeMap(serviceId=service.id)
    instance_maps = []
    for instance_map in all_instance_maps:
        if instance_map.state not in ("removed", "removing"):
            instance_maps.append(instance_map)
    logger.info("instance_maps : %s", instance_maps)

    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        logger.info("container state: %s", c.state)
        containers = super_client.list_container(
            externalId=c.externalId,
            include="hosts")
        assert len(containers) == 1
        container.append(containers[0])
        logger.info("container : %s", format(containers[0]))
    return container
