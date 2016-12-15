from common_fixtures import *  # NOQA

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_lbservice_host_routing_1(admin_client, client, socat_containers):

    port = "900"

    service_scale = 2
    lb_scale = 1
    service_count = 4

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc3.com",
                 "path": "/service1.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc4.com",
                 "path": "/service2.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc3.com",
                 "path": "/service1.html",
                 "serviceId": 3,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc4.com",
                 "path": "/service2.html",
                 "serviceId": 3,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2], services[3]],
                        "www.abc3.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2], services[3]],
                        "www.abc4.com", "/service2.html")
    delete_all(client, [env])


def test_lbservice_host_routing_cross_stack(
        admin_client, client, socat_containers):

    port = "901"

    service_scale = 2
    lb_scale = 1
    service_count = 4

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc3.com",
                 "path": "/service1.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc4.com",
                 "path": "/service2.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc3.com",
                 "path": "/service1.html",
                 "serviceId": 3,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc4.com",
                 "path": "/service2.html",
                 "serviceId": 3,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count,
        port_rules, crosslinking=True)

    for service in services:
        service = service.activate()
    for service in services:
        service = client.wait_success(service, 120)
        assert service.state == "active"

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2], services[3]],
                        "www.abc3.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2], services[3]],
                        "www.abc4.com", "/service2.html")
    to_delete = [env]
    for service in services:
        to_delete.append(get_env(admin_client, service))
    delete_all(client, to_delete)


def test_lbservice_host_routing_2(admin_client, client, socat_containers):

    port = "902"

    service_scale = 2
    lb_scale = 1
    service_count = 3

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc2.com",
                                      "/service1.html")
    delete_all(client, [env])


def test_lbservice_host_routing_scale_up(
        admin_client, client, socat_containers):

    port = "903"

    service_scale = 2
    lb_scale = 1
    service_count = 3

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
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

    wait_for_lb_service_to_become_active(admin_client, client,
                                         final_services, lb_service)

    validate_lb_service(admin_client, client, lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [final_services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [final_services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc2.com", "/service1.html")

    delete_all(client, [env])


def test_lbservice_host_routing_scale_down(
        admin_client, client, socat_containers):

    port = "904"

    service_scale = 3
    lb_scale = 1
    service_count = 3

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/name.html",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
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

    wait_for_lb_service_to_become_active(admin_client, client,
                                         final_services, lb_service)

    validate_lb_service(admin_client, client, lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client, lb_service, port,
                        [final_services[0], final_services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client, lb_service,
                        port, [final_services[2]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client, lb_service, port,
                        [final_services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc1.com",
                                      "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc2.com",
                                      "/service1.html")

    delete_all(client, [env])


def test_lbservice_host_routing_only_path(
        admin_client, client, socat_containers):

    port = "905"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc1.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        None, "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[1]],
                        "www.abc3.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,  [services[1]],
                        "www.abc2.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        None, "/service1.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_host_routing_only_host(
        admin_client, client, socat_containers):

    port = "906"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         [services[0], services[1]],
                                         lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[1]],
                        "www.abc1.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc2.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_host_routing_3(admin_client, client, socat_containers):

    port = "907"

    service_scale = 2
    lb_scale = 1
    service_count = 4

    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"path": "/service1.html",
                 "serviceId": 3,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[1]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[3]],
                        "www.abc3.com", "/service1.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_3(admin_client, client, socat_containers):

    port = "908"

    service_scale = 2
    lb_scale = 1
    service_count = 5

    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"path": "/service1.html",
                 "serviceId": 3,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    service_list = [services[0], services[1], services[2], services[3]]
    wait_for_lb_service_to_become_active(admin_client, client,
                                         service_list, lb_service)
    validate_lb_service(admin_client, client, lb_service,
                        port, [services[0]],
                        "www.abc.com", "/service2.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[1]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[3]],
                        "www.abc3.com", "/service1.html")
    # Edit port_rules

    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": services[0].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"serviceId": services[2].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"

                 }
    port_rules.append(port_rule)

    port_rule = {"path": "/service2.html",
                 "serviceId": services[3].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc.com",
                 "serviceId": services[4].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "www.abc1.com",
                 "serviceId": services[4].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    service_list = [services[0], services[2], services[3], services[4]]

    wait_for_lb_service_to_become_active(admin_client, client,
                                         service_list, lb_service)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0], services[4]],
                        "www.abc.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[4]],
                        "www.abc1.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[2]],
                        "www.abc2.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[3]],
                        "www.abc3.com", "/service2.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_add_host(
        admin_client, client, socat_containers):

    port = "909"

    service_scale = 2
    lb_scale = 1
    service_count = 1

    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc2.com", "/name.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    port_rule = {"hostname": "www.abc2.com",
                 "serviceId": services[0].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/name.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_remove_host(
        admin_client, client, socat_containers):

    port = "910"

    service_scale = 2
    lb_scale = 1
    service_count = 1

    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client, services,
                                         lb_service)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc3.com", "/name.html")

    # Edit port rules
    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": services[0].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc2.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_edit_host_routing_edit_existing_host(
        admin_client, client, socat_containers):

    port = "911"

    service_scale = 2
    lb_scale = 1
    service_count = 1

    port_rules = []
    port_rule = {"hostname": "www.abc.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc.com", "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc2.com", "/name.html")

    # Edit port rules
    port_rules = []
    port_rule = {"hostname": "www.abc2.com",
                 "serviceId": services[0].id,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "www.abc2.com", "/service2.html")
    validate_lb_service_for_no_access(admin_client, lb_service, port,
                                      "www.abc.com", "/name.html")

    delete_all(client, [env])


def test_lbservice_host_routing_multiple_port_1(
        admin_client, client, socat_containers):

    port1 = "1000"
    port2 = "1001"

    port1_target = "80"
    port2_target = "81"

    service_scale = 2
    lb_scale = 1
    service_count = 4

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service3.html",
                 "serviceId": 0,
                 "sourcePort": port2,
                 "targetPort": port2_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "serviceId": 1,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "serviceId": 1,
                 "sourcePort": port2,
                 "targetPort": port2_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"path": "/service1.html",
                 "serviceId": 2,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"path": "/service3.html",
                 "serviceId": 2,
                 "sourcePort": port2,
                 "targetPort": port2_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"serviceId": 3,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"}
    port_rules.append(port_rule)

    port_rule = {"serviceId": 3,
                 "sourcePort": port2,
                 "targetPort": port2_target,
                 "protocol": "http"}
    port_rules.append(port_rule)

    env, services, lb_service = \
        create_env_with_multiple_svc_and_lb(
            client, service_scale, lb_scale, [port1, port2], service_count,
            port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)
    validate_lb_service(admin_client, client,
                        lb_service, port1,
                        [services[0]],
                        "www.abc1.com", "/service1.html")
    validate_lb_service(admin_client, client,
                        lb_service, port1, [services[3]],
                        "www.abc1.com", "/service2.html")
    validate_lb_service(admin_client, client,
                        lb_service, port1, [services[1]],
                        "www.abc2.com", "/service1.html")
    validate_lb_service(admin_client, client,
                        lb_service, port1, [services[1]],
                        "www.abc2.com", "/service2.html")
    validate_lb_service(admin_client, client,
                        lb_service, port2, [services[1]],
                        "www.abc2.com", "/service3.html")
    validate_lb_service(admin_client, client,
                        lb_service, port2,
                        [services[0]],
                        "www.abc1.com", "/service3.html")
    validate_lb_service(admin_client, client,
                        lb_service, port2, [services[2]],
                        "www.abc4.com", "/service3.html")
    validate_lb_service(admin_client, client,
                        lb_service, port2, [services[3]],
                        "www.abc3.com", "/service4.html")

    delete_all(client, [env])


def test_lbservice_host_routing_multiple_port_2(
        admin_client, client, socat_containers):

    port1 = "1002"
    port2 = "1003"

    port1_target = "80"
    port2_target = "81"

    service_scale = 2
    lb_scale = 1
    service_count = 3

    port_rules = []
    port_rule = {"path": "/81",
                 "serviceId": 0,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"path": "/81/service3.html",
                 "serviceId": 1,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"path": "/service",
                 "serviceId": 2,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"path": "/service",
                 "serviceId": 2,
                 "sourcePort": port2,
                 "targetPort": port2_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    env, services, lb_service = \
        create_env_with_multiple_svc_and_lb(
            client, service_scale, lb_scale, [port1, port2], service_count,
            port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port1,
                        [services[2]],
                        "www.abc1.com", "/service1.html")
    validate_lb_service(admin_client, client,
                        lb_service, port1, [services[0]],
                        "www.abc1.com", "/81/service4.html")
    validate_lb_service(admin_client, client,
                        lb_service, port1, [services[1]],
                        "www.abc1.com", "/81/service3.html")

    validate_lb_service(admin_client, client,
                        lb_service, port2, [services[2]],
                        "www.abc1.com", "/service3.html")

    validate_lb_service(admin_client, client,
                        lb_service, port2, [services[2]],
                        "www.abc1.com", "/service4.html")

    delete_all(client, [env])


def test_lbservice_host_routing_multiple_port_3(
        admin_client, client, socat_containers):

    port1 = "1004"
    port2 = "1005"

    port1_target = "80"
    port2_target = "81"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"serviceId": 0,
                 "sourcePort": port1,
                 "targetPort": port1_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"serviceId": 1,
                 "sourcePort": port2,
                 "targetPort": port2_target,
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = \
        create_env_with_multiple_svc_and_lb(
            client, service_scale, lb_scale, [port1, port2], service_count,
            port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port1,
                        [services[0]],
                        "www.abc1.com", "/service1.html")
    validate_lb_service(admin_client, client,
                        lb_service, port2,
                        [services[1]],
                        "www.abc1.com", "/service3.html")
    delete_all(client, [env])


def test_lbservice_external_service(admin_client, client, socat_containers):
    port = "1010"

    lb_scale = 2

    env, lb_service, ext_service, con_list = \
        create_env_with_ext_svc_and_lb(client, lb_scale, port)

    ext_service = activate_svc(client, ext_service)
    lb_service = activate_svc(client, lb_service)

    validate_lb_service_for_external_services(admin_client, client,
                                              lb_service, port, con_list)

    delete_all(client, [env])


def test_lbservice_host_routing_tcp_only(admin_client, client,
                                         socat_containers):

    port = "1011"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "tcp"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "tcp"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "tcp"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[0], services[1]])

    delete_all(client, [env])


def test_lbservice_host_routing_tcp_and_http(admin_client, client,
                                             socat_containers):

    port1 = "1012"
    port2 = "1013"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service3.html",
                 "serviceId": 0,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "tcp"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service3.html",
                 "serviceId": 0,
                 "sourcePort": port2,
                 "targetPort": "81",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service4.html",
                 "serviceId": 1,
                 "sourcePort": port1,
                 "targetPort": "80",
                 "protocol": "tcp"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service4.html",
                 "serviceId": 1,
                 "sourcePort": port2,
                 "targetPort": "81",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port1, port2], service_count,
        port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    port1 = "1012"
    """
    validate_lb_service(admin_client, client,
                        lb_service, port1,
                        [services[0], services[1]])

    validate_lb_service(admin_client, client,
                        lb_service, port1,
                        [services[0], services[1]])
    """
    validate_lb_service(admin_client, client,
                        lb_service, port2,
                        [services[0]],
                        "www.abc1.com", "/service3.html")

    validate_lb_service(admin_client, client,
                        lb_service, port2, [services[1]],
                        "www.abc1.com", "/service4.html")

    validate_lb_service_for_no_access(admin_client, lb_service, port2,
                                      "www.abc2.com",
                                      "/service3.html")
    delete_all(client, [env])


def test_lbservice_host_routing_wildcard(
        admin_client, client, socat_containers):

    port = "1014"

    service_scale = 2
    lb_scale = 1
    service_count = 3

    port_rules = []
    port_rule = {"hostname": "*.domain.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "domain.*",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "abc.domain.com",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[2]],
                        "abc.domain.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[0]],
                        "abc.def.domain.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[1]],
                        "domain.abc.def.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[1]],
                        "domain.abc.com", "/name.html")
    delete_all(client, [env])


def test_lbservice_host_routing_wildcard_order(
        admin_client, client, socat_containers):

    port = "1014"

    service_scale = 2
    lb_scale = 1
    service_count = 5

    port_rules = []
    port_rule = {"hostname": "*.domain.com",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "domain.*",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "abc.domain.com",
                 "serviceId": 2,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "abc.domain.com",
                 "path": "/service1.html",
                 "serviceId": 3,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "*.domain.com",
                 "path": "/service1.html",
                 "serviceId": 4,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http"
                 }
    port_rules.append(port_rule)
    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[4]],
                        "abc.def.domain.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[0]],
                        "abc.def.domain.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[1]],
                        "domain.abc.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[1]],
                        "domain.def.com", "/service1.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[2]],
                        "abc.domain.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[3]],
                        "abc.domain.com", "/service1.html")

    delete_all(client, [env])


def test_lbservice_host_routing_priority_override_1(
        admin_client, client, socat_containers):

    port = "1015"

    service_scale = 2
    lb_scale = 1
    service_count = 2

    port_rules = []
    port_rule = {"hostname": "*.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http",
                 "priority": 1
                 }
    port_rules.append(port_rule)

    port_rule = {"hostname": "abc.domain.com",
                 "path": "/service1.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "http",
                 "priority": 2
                 }
    port_rules.append(port_rule)
    env, services, lb_service = create_env_with_multiple_svc_and_lb(
        client, service_scale, lb_scale, [port], service_count, port_rules)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[0]],
                        "abc.domain.com", "/service1.html")

    delete_all(client, [env])


def test_lb_with_selector_link_target_portrules(admin_client, client,
                                                socat_containers):

    port = "20001"
    # Create Environment
    env = create_env(client)

    launch_config_svc = {"imageUuid": LB_HOST_ROUTING_IMAGE_UUID,
                         "labels": {"test1": "value1"}}
    port_rule1 = {
        "targetPort": "80",
        "hostname": "www.abc.com",
        "path": "/name.html"}

    port_rule2 = {
        "targetPort": "80",
        "hostname": "www.abc1.com",
        "path": "/service1.html"}

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(name=service_name,
                                     stackId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=1,
                                     lbConfig=create_lb_config([port_rule1]))

    service1 = client.wait_success(service1)
    assert service1.state == "inactive"

    random_name = random_str()
    service2_name = random_name.replace("-", "")

    service2 = client.create_service(name=service2_name,
                                     stackId=env.id,
                                     launchConfig=launch_config_svc,
                                     scale=1,
                                     lbConfig=create_lb_config([port_rule2]))

    service2 = client.wait_success(service2)
    assert service2.state == "inactive"

    launch_config_lb = {"ports": [port],
                        "imageUuid": get_haproxy_image()}

    port_rule1 = {
        "sourcePort": port,
        "selector": "test1=value1"}

    lb_env = create_env(client)
    lb_service = client.create_loadBalancerService(
        name="lb-withselectorlinks",
        stackId=lb_env.id,
        launchConfig=launch_config_lb,
        scale=1,
        lbConfig=create_lb_config([port_rule1]))
    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    service1 = activate_svc(client, service1)
    service2 = activate_svc(client, service2)
    lb_service = activate_svc(client, lb_service)

    wait_for_lb_service_to_become_active(admin_client, client,
                                         [service1, service2], lb_service)

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [service1],
                        "www.abc.com", "/name.html")

    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [service2],
                        "www.abc1.com", "/service1.html")

    delete_all(client, [env])
