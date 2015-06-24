from common_fixtures import *  # NOQA

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"

logger = logging.getLogger(__name__)


def create_env_with_ext_svc(client, scale_svc, port):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    # Create 2 containers which would be the applications that need to be
    # serviced by the external service

    c1 = client.create_container(name=random_str(), imageUuid=WEB_IMAGE_UUID)
    c2 = client.create_container(name=random_str(), imageUuid=WEB_IMAGE_UUID)

    c1 = client.wait_success(c1, 120)
    assert c1.state == "running"
    c2 = client.wait_success(c2, 120)
    assert c2.state == "running"

    con_list = [c1, c2]
    ips = [c1.primaryIpAddress, c2.primaryIpAddress]
    # Create external Service
    random_name = random_str()
    ext_service_name = random_name.replace("-", "")

    ext_service = client.create_externalService(
        name=ext_service_name, environmentId=env.id, externalIpAddresses=ips)

    ext_service = client.wait_success(ext_service)
    assert ext_service.state == "inactive"

    return env, service, ext_service, con_list


def activate_environment_with_external_services(
        super_client, client, service_scale, port):

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    service.activate()
    ext_service.activate()
    service.addservicelink(serviceId=ext_service.id)
    service = client.wait_success(service, 120)
    ext_service = client.wait_success(ext_service, 120)
    assert service.state == "active"
    assert ext_service.state == "active"
    validate_add_service_link(super_client, service, ext_service)

    return env, service, ext_service, con_list


def test_extservice_activate_svc_activate_external_svc_link(
        super_client, client):

    port = "3001"

    service_scale = 2

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    delete_all(client, [env])


def test_extservice_activate_external_svc_link_activate_svc(
        super_client, client):

    port = "3002"

    service_scale = 2

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    ext_service = activate_svc(client, ext_service)
    link_svc(super_client, service, [ext_service])
    service = activate_svc(client, service)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)
    delete_all(client, [env])


def test_extservice_activate_svc_link_activate_external_svc(
        super_client, client):

    port = "3003"

    service_scale = 1

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    service = activate_svc(client, service)
    link_svc(super_client, service, [ext_service])
    ext_service = activate_svc(client, ext_service)
    validate_add_service_link(super_client, service, ext_service)
    validate_external_service(
        super_client, service, [ext_service], port, con_list)
    delete_all(client, [env])


def test_extservice_link_activate_external_svc_activate_svc(
        super_client, client):

    port = "3004"

    service_scale = 1

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    link_svc(super_client, service, [ext_service])
    ext_service = activate_svc(client, ext_service)
    service = activate_svc(client, service)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)
    delete_all(client, [env])


def test_extservice_link_activate_svc_activate_external_svc(
        super_client, client):

    port = "3005"

    service_scale = 1

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    link_svc(super_client, service, [ext_service])
    service = activate_svc(client, service)
    ext_service = activate_svc(client, ext_service)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)
    delete_all(client, [env])


def test_extservice_link_when_services_still_activating(super_client, client):

    port = "3006"

    service_scale = 1

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, service_scale, port)

    service.activate()
    ext_service.activate()

    service.addservicelink(serviceId=ext_service.id)
    service = client.wait_success(service, 120)

    ext_service = client.wait_success(ext_service, 120)

    assert service.state == "active"
    assert ext_service.state == "active"
    validate_add_service_link(super_client, service, ext_service)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    delete_all(client, [env])


def test_extservice_service_scale_up(super_client, client):

    port = "3007"

    service_scale = 1
    final_service_scale = 3

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(super_client, service,
                              [ext_service], port, con_list)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_external_service(
        super_client, service, [ext_service], port, con_list)
    delete_all(client, [env])


def test_extservice_services_scale_down(super_client, client):

    port = "3008"

    service_scale = 3
    final_service_scale = 1

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(super_client, service,
                              [ext_service], port, con_list)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_external_service(
        super_client, service, [ext_service], port, con_list)
    delete_all(client, [env])


def test_extservice_ext_services_deactivate_activate(super_client, client):

    port = "3014"

    service_scale = 1

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    ext_service = ext_service.deactivate()
    ext_service = client.wait_success(ext_service, 120)
    assert ext_service.state == "inactive"
    time.sleep(60)

    ext_service = ext_service.activate()
    ext_service = client.wait_success(ext_service, 120)
    assert ext_service.state == "active"

    validate_external_service(
        super_client, service, [ext_service], port, con_list)
    delete_all(client, [env])


def test_extservice_service_deactivate_activate(super_client, client):

    port = "3015"

    service_scale = 1

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(super_client, service, [ext_service],
                              port, con_list)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"
    time.sleep(60)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_external_service(super_client, service, [ext_service],
                              port, con_list)
    delete_all(client, [env])


def test_extservice_deactivate_activate_environment(super_client, client):

    port = "3016"

    service_scale = 1

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    ext_service = client.wait_success(ext_service, 120)
    assert ext_service.state == "inactive"

    time.sleep(60)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    ext_service = client.wait_success(ext_service, 120)
    assert ext_service.state == "active"

    validate_external_service(super_client, service, [ext_service],
                              port, con_list)
    delete_all(client, [env])


def test_extservice_services_delete_service_add_service(super_client, client):

    port = "3018"

    service_scale = 2

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    # Delete Service

    service = client.wait_success(client.delete(service))
    assert service.state == "removed"
    validate_remove_service_link(super_client, service, ext_service)

    port1 = "30180"

    # Add another service and link to external service
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

    service1.addservicelink(serviceId=ext_service.id)
    validate_add_service_link(super_client, service1, ext_service)

    validate_external_service(super_client, service1,
                              [ext_service], port1, con_list)

    delete_all(client, [env])


def test_extservice_delete_and_add_ext_service(super_client, client):

    port = "3019"

    service_scale = 2

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    # Delete external service

    ext_service = client.wait_success(client.delete(ext_service))
    assert ext_service.state == "removed"
    validate_remove_service_link(super_client, service, ext_service)

    # Add another external service and link the service to this newly created
    # external service

    c1 = client.create_container(name=random_str(), imageUuid=WEB_IMAGE_UUID)
    c2 = client.create_container(name=random_str(), imageUuid=WEB_IMAGE_UUID)

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
        name=ext_service_name, environmentId=env.id, externalIpAddresses=ips)
    ext_service1 = client.wait_success(ext_service1)
    ext_service1 = activate_svc(client, ext_service1)

    service.addservicelink(serviceId=ext_service1.id)
    validate_add_service_link(super_client, service, ext_service1)

    validate_external_service(super_client, service, [ext_service1], port,
                              con_list)

    delete_all(client, [env])


def test_extservice_services_stop_start_instance(super_client, client):

    port = "3020"

    service_scale = 2

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(super_client, service,
                              [ext_service], port, con_list)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Stop service instance
    service_instance = client.wait_success(service_instance.stop(), 120)
    service = client.wait_success(service)
    wait_for_scale_to_adjust(super_client, service)

    validate_external_service(super_client, service, [ext_service],
                              port, con_list)

    delete_all(client, [env])


def test_extservice_services_restart_instance(super_client, client):

    port = "3021"

    service_scale = 2

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(
            super_client, client, service_scale, port)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    service_instance = containers[0]

    # Restart external instance
    service_instance = client.wait_success(service_instance.restart(), 120)
    assert service_instance.state == 'running'

    validate_external_service(super_client, service,
                              [ext_service], port, con_list)

    delete_all(client, [env])


def test_extservice_add_and_delete_ips(super_client, client):

    port = "3023"

    service_scale = 2

    env, service, ext_service, con_list = \
        activate_environment_with_external_services(super_client, client,
                                                    service_scale, port)

    validate_external_service(
        super_client, service, [ext_service], port, con_list)

    # Update external Service to add one more ip

    c1 = client.create_container(name=random_str(), imageUuid=WEB_IMAGE_UUID)
    c1 = client.wait_success(c1, 120)
    assert c1.state == "running"

    ips = [con_list[0].primaryIpAddress, con_list[1].primaryIpAddress,
           c1.primaryIpAddress]
    con_list.append(c1)
    ext_service = client.update(
        ext_service, name=ext_service.name, externalIpAddresses=ips)
    ext_service = client.wait_success(ext_service, 120)

    validate_external_service(super_client, service, [ext_service], port,
                              con_list)

    # Update external Service to remove one of the existing ips

    ips = [con_list[1].primaryIpAddress, c1.primaryIpAddress]
    con_list.pop(0)
    ext_service = client.update(
        ext_service, name=ext_service.name, externalIpAddresses=ips)
    ext_service = client.wait_success(ext_service, 120)

    validate_external_service(super_client, service, [ext_service], port,
                              con_list)

    delete_all(client, [env])


def validate_external_service(super_client, service, ext_services,
                              exposed_port, container_list,
                              exclude_instance=None,
                              exclude_instance_purged=False):
    time.sleep(5)

    containers = get_service_container_list(super_client, service)
    assert len(containers) == service.scale
    for container in containers:
        print "Validation for container -" + str(container.name)
        host = super_client.by_id('host', container.hosts[0].id)
        for ext_service in ext_services:
            expected_dns_list = []
            expected_link_response = []
            dns_response = []
            for con in container_list:
                if (exclude_instance is not None) \
                        and (con.id == exclude_instance.id):
                    print "Excluded from DNS and wget list:" + con.name
                else:
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
            cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + \
                  ext_service.name + ":80/name.html;cat result.txt"
            print cmd
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            assert len(response) == 1
            resp = response[0].strip("\n")
            print "Actual wget Response" + str(resp)
            assert resp in (expected_link_response)

            # Validate DNS resolution using dig
            cmd = "dig " + ext_service.name + " +short"
            print cmd
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            print "Actual dig Response" + str(response)

            expected_entries_dig = len(container_list)
            if exclude_instance is not None:
                expected_entries_dig = expected_entries_dig - 1

            assert len(response) == expected_entries_dig

            for resp in response:
                dns_response.append(resp.strip("\n"))

            for address in expected_dns_list:
                assert address in dns_response
