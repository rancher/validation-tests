from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_lbservice_host_routing_1(super_client, client):

    port = "901"

    service_scale = 2
    lb_scale = 1
    service_count = 4

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

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

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port,
                        [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2], services[3]],
                        "www.abc3.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2], services[3]],
                        "www.abc4.com", "/service2.html")

    delete_all(client, [env])


def test_lbservice_host_routing_2(super_client, client):

    port = "902"

    service_scale = 2
    lb_scale = 1
    service_count = 3

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

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

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc2.com",
                                      "/service1.html")
    delete_all(client, [env])


def test_lbservice_host_routing_scale_up(super_client, client):

    port = "903"

    service_scale = 2
    lb_scale = 1
    service_count = 3

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

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

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
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

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port, [final_services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port, [final_services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc2.com", "/service1.html")

    delete_all(client, [env])


def test_lbservice_host_routing_scale_down(super_client, client):

    port = "904"

    service_scale = 3
    lb_scale = 1
    service_count = 3

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

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

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
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

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port, [final_services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env, final_services,
                        lb_service, port, [final_services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc2.com",
                                      "/service1.html")

    delete_all(client, [env])


def test_lbservice_host_routing_only_path(super_client, client):

    port = "905"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

    service_link1 = {"serviceId": services[0].id,
                     "ports": ["/service1.html"]}
    service_link2 = {"serviceId": services[1].id,
                     "ports": ["/service2.html"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1, service_link2])

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        None, "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[1]],
                        "www.abc3.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port,  [services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        None, "/service1.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_host_routing_only_host(super_client, client):

    port = "906"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc.com"]}
    service_link2 = {"serviceId": services[1].id,
                     "ports": ["www.abc1.com"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1, service_link2])

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service1.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[1]],
                        "www.abc1.com", "/name.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc2.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_host_routing_3(super_client, client):

    port = "907"

    service_scale = 2
    lb_scale = 1
    service_count = 4

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

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

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[1]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[3]],
                        "www.abc3.com", "/service1.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_3(super_client, client):

    port = "908"

    service_scale = 2
    lb_scale = 1
    service_count = 5

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

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

    env = env.activateservices()
    env = client.wait_success(env, 120)

    service_list = [services[0], services[1], services[2], services[3]]
    validate_lb_service(super_client, client, env, service_list,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")

    validate_lb_service(super_client, client, env, service_list,
                        lb_service, port, [services[1]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env, service_list,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service(super_client, client, env, service_list,
                        lb_service, port, [services[3]],
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

    service_list = [services[0], services[2], services[3], services[4]]

    validate_lb_service(super_client, client, env,  service_list,
                        lb_service, port, [services[0], services[4]],
                        "www.abc.com", "/service1.html")

    validate_lb_service(super_client, client, env,  service_list,
                        lb_service, port, [services[4]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(super_client, client, env,  service_list,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service(super_client, client, env,  service_list,
                        lb_service, port, [services[3]],
                        "www.abc3.com", "/service2.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_add_host(super_client, client):

    port = "909"

    service_scale = 2
    lb_scale = 1
    service_count = 1

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc.com"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1])

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc2.com", "/name.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    # Edit service links
    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc.com", "www.abc2.com"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1])

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_remove_host(super_client, client):

    port = "910"

    service_scale = 2
    lb_scale = 1
    service_count = 1

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc.com", "www.abc2.com"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1])

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    # Edit service links
    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc.com"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1])

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc2.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_edit_existing_host(super_client, client):

    port = "911"

    service_scale = 2
    lb_scale = 1
    service_count = 1

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, port, service_count)

    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc.com"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1])

    env = env.activateservices()
    env = client.wait_success(env, 120)

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc2.com", "/name.html")

    # Edit service links
    service_link1 = {"serviceId": services[0].id,
                     "ports": ["www.abc2.com"]}

    lb_service.setservicelinks(
        serviceLinks=[service_link1])

    validate_lb_service(super_client, client, env, services,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/service2.html")
    validate_lb_service_for_no_access(client, lb_service, port,
                                      "www.abc.com", "/name.html")

    delete_all(client, [env])
