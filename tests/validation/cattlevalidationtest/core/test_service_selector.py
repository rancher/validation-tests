from common_fixtures import *  # NOQA

shared_services = []


@pytest.fixture(scope='session', autouse=True)
def create_services_for_selectors(request, client, super_client):
    labels = [{"c1": "value1"}, {"c1": "value2"}, {"c2": "value1"},
              {"c2": "value2"}, {"c2": "value3"},
              {"c2": "value4", "c1": "value3"},
              {"c2": "value4", "c1": "value4"}]
    env = create_env(client)
    for label in labels:
        launch_config = {"imageUuid": WEB_IMAGE_UUID,
                         "labels": label}
        service = client.create_service(name=random_str(),
                                        environmentId=env.id,
                                        launchConfig=launch_config,
                                        scale=2)
        service = client.wait_success(service, 60)
        shared_services.append(service)

    def fin():
        delete_all(client, shared_services)

    request.addfinalizer(fin)


def env_with_service_selectorContainer(super_client, client, label):
    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}

    # Create Environment
    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")

    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_svc, scale=2,
        selectorContainer=label["name"]+"="+label["value"])

    service = client.wait_success(service)
    assert service.state == "inactive"
    service.activate()
    service = client.wait_success(service)
    assert service.state == "active"

    c = client.create_container(name=random_str(),
                                networkMode=MANAGED_NETWORK,
                                imageUuid=WEB_IMAGE_UUID,
                                labels={label["name"]: label["value"]}
                                )
    c = client.wait_success(c)

    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 1
    assert containers[0].id == c.id
    return env, service, c


def create_env_with_svc_options(client, launch_config_svc,
                                scale_svc, metadata=None,
                                selectorLink=None,
                                selectorContainer=None):

    # Create Environment
    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc,
                                    metadata=metadata,
                                    selectorLink=selectorLink,
                                    selectorContainer=selectorContainer)
    return env, service


def test_selectorLink(super_client, client):
    port = "4000"

    launch_config = {"imageUuid": WEB_IMAGE_UUID,
                     "labels": {"test1": "bar"}}
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    env, service = create_env_with_svc_options(client, launch_config_svc,
                                               2, selectorLink="test1=bar")
    linked_service = client.create_service(name=random_str(),
                                           environmentId=env.id,
                                           launchConfig=launch_config,
                                           scale=2)
    env = env.activateservices()
    service = client.wait_success(service, 300)
    validate_linked_service(super_client, service, [linked_service], port)
    delete_all(client, [env])


def test_selectorLink_lbservice(super_client, client, socat_containers):
    port = "4001"

    launch_config = {"imageUuid": WEB_IMAGE_UUID,
                     "labels": {"test2": "bar"}}
    launch_config_lb = {"ports": port+":80"}

    env = create_env(client)
    lb_service = client.create_loadBalancerService(
        name="lb-1",
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=1, selectorLink="test2=bar")
    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    linked_service1 = client.create_service(name=random_str(),
                                            environmentId=env.id,
                                            launchConfig=launch_config,
                                            scale=2)
    linked_service1 = client.wait_success(linked_service1)
    assert linked_service1.state == "inactive"

    linked_service2 = client.create_service(name=random_str(),
                                            environmentId=env.id,
                                            launchConfig=launch_config,
                                            scale=2)
    linked_service2 = client.wait_success(linked_service2)
    assert linked_service2.state == "inactive"

    linked_service1.activate()
    linked_service2.activate()

    lb_service.activate()
    linked_service1 = client.wait_success(linked_service1, 300)
    assert linked_service1.state == "active"
    linked_service2 = client.wait_success(linked_service2, 300)
    assert linked_service2.state == "active"
    lb_service = client.wait_success(lb_service, 300)
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(super_client, client,
                                         [linked_service1, linked_service2],
                                         lb_service)
    validate_lb_service(super_client, client, lb_service, port,
                        [linked_service1, linked_service2])
    delete_all(client, [env])


def test_selectorLink_dnsservice(super_client, client):
    port = "4002"

    launch_config = {"imageUuid": WEB_IMAGE_UUID,
                     "labels": {"test3": "bar"}}

    client_launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                                "ports": [port+":22/tcp"]}
    env = create_env(client)
    dns = client.create_dnsService(
        name="dns-1",
        environmentId=env.id,
        scale=1, selectorLink="test3=bar")
    dns = client.wait_success(dns)
    assert dns.state == "inactive"

    linked_service1 = client.create_service(name=random_str(),
                                            environmentId=env.id,
                                            launchConfig=launch_config,
                                            scale=2)
    linked_service1 = client.wait_success(linked_service1)
    assert linked_service1.state == "inactive"

    linked_service2 = client.create_service(name=random_str(),
                                            environmentId=env.id,
                                            launchConfig=launch_config,
                                            scale=2)
    linked_service2 = client.wait_success(linked_service2)
    assert linked_service2.state == "inactive"

    service = client.create_service(name=random_str(),
                                    environmentId=env.id,
                                    launchConfig=client_launch_config_svc,
                                    scale=1)
    service = client.wait_success(service)
    link_svc(super_client, service, [dns])

    service.activate()
    linked_service1.activate()
    linked_service2.activate()
    dns.activate()

    linked_service1 = client.wait_success(linked_service1, 300)
    assert linked_service1.state == "active"
    linked_service2 = client.wait_success(linked_service2, 300)
    assert linked_service2.state == "active"
    dns = client.wait_success(dns, 300)
    assert dns.state == "active"

    validate_dns_service(
        super_client, service, [linked_service1, linked_service2], port,
        dns.name)
    delete_all(client, [env])


def test__selectorLink_tolinkto_dnsservice(super_client, client):
    port = "4003"

    launch_config = {"imageUuid": WEB_IMAGE_UUID,
                     "labels": {"test5": "bar"}}

    client_launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                                "ports": [port+":22/tcp"],
                                "labels": {"dns": "mydns"}}

    dns_launch_config = {"labels": {"dns": "mydns"}}

    env = create_env(client)
    dns = client.create_dnsService(
        name="dns-1",
        environmentId=env.id,
        scale=1, selectorLink="test5=bar",
        launchConfig=dns_launch_config)

    dns = client.wait_success(dns)
    assert dns.state == "inactive"

    linked_service1 = client.create_service(name=random_str(),
                                            environmentId=env.id,
                                            launchConfig=launch_config,
                                            scale=2)
    linked_service1 = client.wait_success(linked_service1)
    assert linked_service1.state == "inactive"

    linked_service2 = client.create_service(name=random_str(),
                                            environmentId=env.id,
                                            launchConfig=launch_config,
                                            scale=2)
    linked_service2 = client.wait_success(linked_service2)
    assert linked_service2.state == "inactive"

    service = client.create_service(name=random_str(),
                                    environmentId=env.id,
                                    launchConfig=client_launch_config_svc,
                                    selectorLink="dns=mydns",
                                    scale=1)
    service = client.wait_success(service)
    assert service.state == "inactive"

    service.activate()
    linked_service1.activate()
    linked_service2.activate()
    dns.activate()

    linked_service1 = client.wait_success(linked_service1, 300)
    assert linked_service1.state == "active"
    linked_service2 = client.wait_success(linked_service2, 300)
    assert linked_service2.state == "active"
    dns = client.wait_success(dns, 300)
    assert dns.state == "active"

    validate_dns_service(
        super_client, service, [linked_service1, linked_service2], port,
        dns.name)
    delete_all(client, [env])


def test_selectorContainer_service_link(super_client, client):
    port = "5000"

    labels = {}
    labels["name"] = "testc1"
    labels["value"] = "bar"

    env, consumed_service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=1)

    service = client.wait_success(service)
    assert service.state == "inactive"

    service.activate()
    service.addservicelink(serviceLink={"serviceId": consumed_service.id})
    service = client.wait_success(service, 120)

    consumed_service = client.wait_success(consumed_service, 120)

    assert service.state == "active"
    assert consumed_service.state == "active"
    validate_add_service_link(super_client, service, consumed_service)

    unmanaged_con = {}
    unmanaged_con[consumed_service.id] = [c]
    validate_linked_service(super_client, service, [consumed_service], port,
                            unmanaged_cons=unmanaged_con)
    delete_all(client, [env, c])


def test_selectorContainer_dns(super_client, client):

    port = "4010"
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    # Create Environment for dns service and client service
    env = create_env(client)

    c1 = client.create_container(name=random_str(),
                                 networkMode=MANAGED_NETWORK,
                                 imageUuid=WEB_IMAGE_UUID,
                                 labels={"dns1": "value1"}
                                 )
    c1 = client.wait_success(c1)

    c2 = client.create_container(name=random_str(),
                                 networkMode=MANAGED_NETWORK,
                                 imageUuid=WEB_IMAGE_UUID,
                                 labels={"dns2": "value2"}
                                 )
    c2 = client.wait_success(c2)

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=1)

    service = client.wait_success(service)
    assert service.state == "inactive"

    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_consumed_svc, scale=2,
        selectorContainer="dns1=value1")

    consumed_service = client.wait_success(consumed_service)
    assert consumed_service.state == "inactive"

    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service1 = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_consumed_svc, scale=2,
        selectorContainer="dns2=value2")

    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "inactive"

    # Create DNS service

    dns = client.create_dnsService(name='WEB1',
                                   environmentId=env.id)
    dns = client.wait_success(dns)

    env.activateservices()

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
    unmanaged_con = {}
    unmanaged_con[consumed_service.id] = [c1]
    unmanaged_con[consumed_service1.id] = [c2]
    validate_dns_service(
        super_client, service, [consumed_service, consumed_service1], port,
        dns.name,  unmanaged_cons=unmanaged_con)
    delete_all(client, [env, c1, c2])


def test_selectorContainer_lb(super_client, client, socat_containers):
    port = "9011"

    service_scale = 2
    lb_scale = 1

    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}

    launch_config_lb = {"ports": [port+":80"]}

    c1 = client.create_container(name=random_str(),
                                 networkMode=MANAGED_NETWORK,
                                 imageUuid=WEB_IMAGE_UUID,
                                 labels={"web1": "lb"}
                                 )
    c1 = client.wait_success(c1)

    c2 = client.create_container(name=random_str(),
                                 networkMode=MANAGED_NETWORK,
                                 imageUuid=WEB_IMAGE_UUID,
                                 labels={"web2": "lb"}
                                 )
    c2 = client.wait_success(c2)

    # Create Environment
    env = create_env(client)

    # Create Service1
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     environmentId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=service_scale,
                                     selectorContainer="web1=lb"
                                     )

    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    # Create Service2
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service2 = client.create_service(name=service_name,
                                     environmentId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=service_scale,
                                     selectorContainer="web2=lb"
                                     )

    service2 = client.wait_success(service2)
    assert service2.state == "inactive"

    # Create LB Service
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=lb_scale)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    service1.activate()
    service2.activate()
    lb_service.activate()

    service_link = {"serviceId": service1.id}
    lb_service.addservicelink(serviceLink=service_link)

    service_link = {"serviceId": service2.id}
    lb_service.addservicelink(serviceLink=service_link)

    service1 = client.wait_success(service1, 180)
    service2 = client.wait_success(service2, 180)
    lb_service = client.wait_success(lb_service, 180)

    assert service1.state == "active"
    assert service2.state == "active"
    assert lb_service.state == "active"

    unmanaged_con = {}
    unmanaged_con[service1.id] = [c1.externalId[:12]]
    unmanaged_con[service2.id] = [c2.externalId[:12]]

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service1, service2], lb_service,
                                         unmanaged_con_count=2)
    validate_lb_service(super_client, client, lb_service, port,
                        [service1, service2], unmanaged_cons=unmanaged_con)

    delete_all(client, [env, c1, c2])


def test_selectorContainer_no_image_with_lb(
        super_client, client, socat_containers):
    port = "9012"

    lb_scale = 1

    launch_config_svc = {"imageUuid": "docker:rancher/none"}

    launch_config_lb = {"ports": [port+":80"]}

    # Create Environment
    env = create_env(client)

    # Create Service1
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     environmentId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=0,
                                     selectorContainer="web1=lbn"
                                     )

    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    # Create Service2
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service2 = client.create_service(name=service_name,
                                     environmentId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=0,
                                     selectorContainer="web2=lbn"
                                     )

    service2 = client.wait_success(service2)
    assert service2.state == "inactive"

    # Create LB Service
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=lb_scale)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    service1.activate()
    service2.activate()
    lb_service.activate()

    service_link = {"serviceId": service1.id}
    lb_service.addservicelink(serviceLink=service_link)

    service_link = {"serviceId": service2.id}
    lb_service.addservicelink(serviceLink=service_link)

    service1 = client.wait_success(service1, 180)
    service2 = client.wait_success(service2, 180)
    lb_service = client.wait_success(lb_service, 180)

    assert service1.state == "active"
    assert service2.state == "active"
    assert lb_service.state == "active"

    wait_for_lb_service_to_become_active(super_client, client,
                                         [service1, service2], lb_service)

    service3 = client.create_service(name=random_str(),
                                     environmentId=env.id,
                                     launchConfig={"imageUuid": WEB_IMAGE_UUID,
                                                   "labels": {"web1": "lbn"}},
                                     scale=1)
    service3 = client.wait_success(service3)
    assert service3.state == "inactive"
    service3 = client.wait_success(service3.activate(), 60)

    service4 = client.create_service(name=random_str(),
                                     environmentId=env.id,
                                     launchConfig={"imageUuid": WEB_IMAGE_UUID,
                                                   "labels": {"web2": "lbn"}},
                                     scale=1)
    service4 = client.wait_success(service4)
    assert service4.state == "inactive"
    service4 = client.wait_success(service4.activate(), 60)

    unmanaged_con = {}
    unmanaged_con[service1.id] = get_container_names_list(
        super_client, [service3])
    unmanaged_con[service2.id] = get_container_names_list(
        super_client, [service4])
    wait_for_lb_service_to_become_active(super_client, client,
                                         [service1, service2], lb_service,
                                         unmanaged_con_count=2)

    validate_lb_service(super_client, client, lb_service, port,
                        [service1, service2], unmanaged_cons=unmanaged_con)
    delete_all(client, [env])


def test_selectorContainer_for_service_reconciliation_on_stop(
        super_client, client, socat_containers):

    labels = {}
    labels["name"] = "testc2"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    # Stop 2 containers of the service
    assert service.scale > 1
    containers = get_service_container_list(super_client, service, managed=1)
    assert len(containers) == service.scale
    assert service.scale > 1
    container1 = containers[0]
    container1 = client.wait_success(container1.stop())
    container2 = containers[1]
    container2 = client.wait_success(container2.stop())

    service = client.wait_success(service)

    wait_for_scale_to_adjust(super_client, service)

    check_container_in_service(super_client, service)
    container1 = client.reload(container1)
    container2 = client.reload(container2)
    assert container1.state == 'running'
    assert container2.state == 'running'
    delete_all(client, [env, c])


def test_selectorContainer_for_service_reconciliation_on_delete(
        super_client, client, socat_containers):
    labels = {}
    labels["name"] = "testc3"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    # Delete 2 containers of the service
    containers = get_service_container_list(super_client, service, managed=1)
    container1 = containers[0]
    container1 = client.wait_success(client.delete(container1))
    container2 = containers[1]
    container2 = client.wait_success(client.delete(container2))

    assert container1.state == 'removed'
    assert container2.state == 'removed'

    wait_for_scale_to_adjust(super_client, service)
    check_container_in_service(super_client, service)
    delete_all(client, [env, c])


def test_selectorContainer_for_container_stop(
        super_client, client, socat_containers):
    labels = {}
    labels["name"] = "testc4"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    # Delete the joined container
    c = client.wait_success(c.stop())
    assert c.state == 'stopped'

    wait_for_scale_to_adjust(super_client, service)
    check_container_in_service(super_client, service)
    assert c.state == 'stopped'
    delete_all(client, [env, c])


def test_selectorContainer_for_container_delete(super_client, client,
                                                socat_containers):
    labels = {}
    labels["name"] = "testc5"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    # Delete the joined container
    c1 = client.wait_success(client.delete(c))
    assert c1.state == 'removed'

    wait_for_scale_to_adjust(super_client, service)
    check_container_in_service(super_client, service)
    assert c1.state == 'removed'
    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 0
    delete_all(client, [env, c])


def test_selectorContainer_for_container_restore(super_client, client,
                                                 socat_containers):
    labels = {}
    labels["name"] = "testc6"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    # Delete the joined container
    c = client.wait_success(client.delete(c))
    assert c.state == 'removed'
    c = client.wait_success(c.restore())
    assert c.state == 'stopped'

    wait_for_scale_to_adjust(super_client, service)
    check_container_in_service(super_client, service)
    assert c.state == 'stopped'

    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 1
    delete_all(client, [env, c])


def test_selectorContainer_scale_up(super_client, client, socat_containers):

    labels = {}
    labels["name"] = "testc7"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    # Scale service
    service = client.update(service, name=service.name, scale=3)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == 3

    check_container_in_service(super_client, service)

    # Make sure joined containers continue to be in "up" state
    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 1
    assert containers[0].state == "running"
    delete_all(client, [env, c])


def test_selectorContainer_scale_down(super_client, client, socat_containers):
    labels = {}
    labels["name"] = "testc8"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    # Scale service
    service = client.update(service, name=service.name, scale=1)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == 1

    check_container_in_service(super_client, service)

    # Make sure joined containers continue to be in "up" state
    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 1
    assert containers[0].state == "running"
    delete_all(client, [env, c])


def test_selectorContainer_deactivate_activate(
        super_client, client, socat_containers):
    labels = {}
    labels["name"] = "testc9"
    labels["value"] = "bar"

    env, service, c = env_with_service_selectorContainer(
        super_client, client, labels)

    service = client.wait_success(service.deactivate())
    wait_until_instances_get_stopped(super_client, service)

    # Make sure joined containers continue to be in "up" state
    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 1
    assert containers[0].state == "running"

    service = client.wait_success(service.activate())
    check_container_in_service(super_client, service)

    # Make sure joined containers continue to be in "up" state
    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 1
    assert containers[0].state == "running"
    delete_all(client, [env, c])


def test_selectorLink_in(super_client, client):
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID}

    env, service = \
        create_env_with_svc_options(
            client, launch_config_svc, 1, selectorLink="c1 in (value1,value2)")
    time.sleep(1)
    validate_add_service_link(super_client, service, shared_services[0])
    validate_add_service_link(super_client, service, shared_services[1])
    delete_all(client, [env])


def test_selectorLink_notin(super_client, client):
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID}

    env, service = \
        create_env_with_svc_options(
            client, launch_config_svc, 1, selectorLink="c1 notin (value1)")
    time.sleep(1)
    validate_add_service_link(super_client, service, shared_services[1])
    delete_all(client, [env])


def test_selectorLink_noteq(super_client, client):
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID}

    env, service = \
        create_env_with_svc_options(
            client, launch_config_svc, 1, selectorLink="c2 != value1")
    time.sleep(1)
    validate_add_service_link(super_client, service, shared_services[3])
    validate_add_service_link(super_client, service, shared_services[4])
    delete_all(client, [env])


def test_selectorLink_name_no_value(super_client, client):
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID}

    env, service = \
        create_env_with_svc_options(
            client, launch_config_svc, 1, selectorLink="c2")
    time.sleep(1)
    validate_add_service_link(super_client, service, shared_services[2])
    validate_add_service_link(super_client, service, shared_services[3])
    validate_add_service_link(super_client, service, shared_services[4])
    delete_all(client, [env])


def test_selectorLink_multiple(super_client, client):
    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID}

    env, service = \
        create_env_with_svc_options(
            client, launch_config_svc, 1, selectorLink="c2,c1 notin (value2)")
    time.sleep(1)
    validate_add_service_link(super_client, service, shared_services[5])
    validate_add_service_link(super_client, service, shared_services[6])
    delete_all(client, [env])


def test_service_with_no_image(super_client, client):
    launch_config_svc = {"imageUuid": "docker:rancher/none"}

    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")

    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_svc, scale=0,
        selectorContainer="test=none")

    service = client.wait_success(service)
    assert service.state == "inactive"
    service.activate()
    service = client.wait_success(service)
    assert service.state == "active"

    containers = get_service_container_list(super_client, service)
    assert len(containers) == 0

    c = client.create_container(name=random_str(),
                                networkMode=MANAGED_NETWORK,
                                imageUuid=WEB_IMAGE_UUID,
                                labels={"test": "none"}
                                )
    c = client.wait_success(c)

    containers = get_service_container_list(super_client, service, managed=0)
    assert len(containers) == 1
    assert containers[0].id == c.id
    delete_all(client, [env, c])
