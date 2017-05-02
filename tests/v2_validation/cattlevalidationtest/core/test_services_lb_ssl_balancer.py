from common_fixtures import *  # NOQA
from cattle import ApiError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if_certs_available = pytest.mark.skipif(
    not os.path.isdir(SSLCERT_SUBDIR),
    reason='ssl cert file directory not found')

dom_list = readDataFile(SSLCERT_SUBDIR, "certlist.txt").rstrip().split(",")


def create_lb_services_ssl(admin_client, client,
                           service_scale, lb_scale,
                           port, ssl_port,
                           default_domain, domains=None):
    service_count = 2
    certs = []
    if domains:
        for domain in domains:
            certs.append(get_cert(domain))

    port_rules = []
    port_rule = {"hostname": "www.abc1.com",
                 "path": "/service1.html",
                 "serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "https"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "www.abc2.com",
                 "path": "/service2.html",
                 "serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "https"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = \
        create_env_with_multiple_svc_and_ssl_lb(
            client, service_scale, lb_scale, [port], port_rules, service_count,
            ssl_port, default_cert=get_cert(default_domain), certs=certs)

    client_port = port + "0"
    test_ssl_client_con = create_client_container_for_ssh(client, client_port)
    validate_lb_services_ssl(admin_client, client, test_ssl_client_con,
                             env, services, lb_service,
                             port, ssl_port, default_domain, domains)
    return env, services, lb_service, test_ssl_client_con


def validate_lb_services_ssl(admin_client, client, test_ssl_client_con,
                             env, services, lb_service,
                             port, ssl_port,
                             default_domain, domains=None):

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)
    supported_domains = [default_domain]
    if domains:
        supported_domains.extend(domains)

    for domain in supported_domains:
        start_time = time.time()
        logger.info("Validate Domain Start time  " + str(start_time))
        validate_lb_service(admin_client, client,
                            lb_service, ssl_port,
                            [services[0]],
                            "www.abc1.com", "/service1.html", domain,
                            test_ssl_client_con)
        validate_lb_service(admin_client, client,
                            lb_service, ssl_port, [services[1]],
                            "www.abc2.com", "/service2.html", domain,
                            test_ssl_client_con)


@if_certs_available
def test_lb_ssl_with_default_cert(admin_client, client, certs,
                                  socat_containers):
    domain = dom_list[0]
    service_scale = 2
    lb_scale = 2
    port = "400"
    ssl_port = "400"
    start_time = time.time()
    logger.info("Start time " + str(start_time))
    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               domain)
    end_time = time.time()
    logger.info("End time " + str(end_time))
    logger.info("Total time taken " + str(end_time - start_time))

    # Attempting to access LB rules with cert other supported default
    # cert should return certificate error
    cert = dom_list[1]
    validate_cert_error(admin_client, client, lb_service, port, cert, domain,
                        cert, test_ssl_client_con=test_ssl_client_con)
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_scale_up_service(
        admin_client, client, certs, socat_containers):

    domain = dom_list[0]
    port = "401"
    ssl_port = "401"

    service_scale = 2
    lb_scale = 1
    final_service_scale = 3

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               domain)
    services[0] = client.update(services[0], scale=final_service_scale,
                                name=services[0].name)

    services[0] = client.wait_success(services[0], 120)
    assert services[0].state == "active"
    assert services[0].scale == final_service_scale

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, domain)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_scale_down_service(
        admin_client, client, certs, socat_containers):

    domain = dom_list[0]
    port = "402"
    ssl_port = "402"

    service_scale = 2
    lb_scale = 1
    final_service_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               domain)
    services[0] = client.update(services[0], scale=final_service_scale,
                                name=services[0].name)

    services[0] = client.wait_success(services[0], 120)
    assert services[0].state == "active"
    assert services[0].scale == final_service_scale

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, domain)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_scale_up_lb_service(
        admin_client, client, certs, socat_containers):

    domain = dom_list[0]
    port = "403"
    ssl_port = "403"

    service_scale = 2
    lb_scale = 1
    final_lb_scale = 2

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               domain)
    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, domain)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_scale_up_lb_service_passing_cert(
        admin_client, client, certs, socat_containers):

    domain = dom_list[0]
    port = "4031"
    ssl_port = "4031"

    service_scale = 2
    lb_scale = 1
    final_lb_scale = 2

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               domain)
    lb_config = lb_service.lbConfig
    lb_config["defaultCertificateId"] = get_cert(domain).id
    lb_service = client.update(lb_service, scale=final_lb_scale,
                               lbConfig=lb_config)

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, domain)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_scale_down_lb_service(
        admin_client, client, certs, socat_containers):

    domain = dom_list[0]
    port = "404"
    ssl_port = "404"

    service_scale = 2
    lb_scale = 2
    final_lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               domain)
    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, domain)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_edit_add_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[0]
    port = "405"
    ssl_port = "405"

    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain)

    cert = dom_list[1]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    # Update Lb and add new cert
    new_domain = dom_list[1]
    new_cert = get_cert(new_domain)
    default_domain_cert_id = get_cert(default_domain).id

    lb_config = lb_service.lbConfig
    lb_config["defaultCertificateId"] = default_domain_cert_id
    lb_config["certificateIds"] = [new_cert.id]
    lb_service = client.update(lb_service, lbConfig=lb_config)

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, default_domain, [new_domain])

    # Attempting to access LB rules with cert other supported default
    # cert should return certificate error
    cert = dom_list[2]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_edit_edit_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[0]
    domain = dom_list[1]

    port = "406"
    ssl_port = "406"

    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain, [domain])

    # Update Lb and replace the existing cert
    new_domain = dom_list[2]
    new_cert = get_cert(new_domain)
    default_domain_cert_id = get_cert(default_domain).id

    lb_config = lb_service.lbConfig
    lb_config["defaultCertificateId"] = default_domain_cert_id
    lb_config["certificateIds"] = [new_cert.id]
    lb_service = client.update(lb_service, lbConfig=lb_config)

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, default_domain, [new_domain])
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_swap_default_and_alternate_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[0]
    domain = dom_list[1]

    port = "4061"
    ssl_port = "4061"

    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain, [domain])

    # Update Lb and replace the existing cert
    default_domain_cert_id = get_cert(default_domain).id
    alternate_domain_cert_id = get_cert(domain).id

    lb_config = lb_service.lbConfig
    lb_config["defaultCertificateId"] = alternate_domain_cert_id
    lb_config["certificateIds"] = [default_domain_cert_id]
    lb_service = client.update(lb_service, lbConfig=lb_config)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, default_domain, [domain])
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_edit_add_more_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[0]
    domain = dom_list[1]

    port = "407"
    ssl_port = "407"

    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain, [domain])

    # Update Lb and add another cert

    existing_cert = get_cert(domain)
    new_domain = dom_list[2]
    new_cert = get_cert(new_domain)
    default_domain_cert_id = get_cert(default_domain).id

    lb_config = lb_service.lbConfig
    lb_config["defaultCertificateId"] = default_domain_cert_id
    lb_config["certificateIds"] = [existing_cert.id, new_cert.id]
    lb_service = client.update(lb_service, lbConfig=lb_config)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, default_domain,
                             [domain, new_domain])
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_edit_remove_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[0]
    domain1 = dom_list[1]
    domain2 = dom_list[2]

    port = "408"
    ssl_port = "408"

    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain, [domain1, domain2])

    # Update Lb and add remove existing cert

    existing_cert1 = get_cert(domain1)
    default_domain_cert_id = get_cert(default_domain).id

    lb_config = lb_service.lbConfig
    lb_config["defaultCertificateId"] = default_domain_cert_id
    lb_config["certificateIds"] = [existing_cert1.id]
    lb_service = client.update(lb_service, lbConfig=lb_config)

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, default_domain, [domain1])
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_edit_add_cert_without_setting_default_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[0]
    port = "409"
    ssl_port = "409"

    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain)

    # Update Lb and add new cert
    new_domain = dom_list[1]
    new_cert = get_cert(new_domain)

    lb_config = lb_service.lbConfig
    lb_config["certificateIds"] = [new_cert.id]
    lb_service = client.update(lb_service, lbConfig=lb_config)
    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con, env,
                             services, lb_service,
                             port, ssl_port, default_domain, [new_domain])

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_delete_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[3]
    port = "410"
    ssl_port = "410"
    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain)

    default_cert = get_cert(default_domain)
    with pytest.raises(ApiError) as e:
        cert1 = client.wait_success(client.delete(default_cert))
    assert e.value.error.status == 405
    assert e.value.error.code == 'InvalidAction'
    assert 'Certificate is in use' in e.value.error.message

    default_cert = client.reload(default_cert)
    assert default_cert.state == 'active'

    default_cert = client.reload(default_cert)
    lb_service = client.wait_success(client.delete(lb_service))
    assert lb_service.state == 'removed'
    time.sleep(5)
    cert1 = client.wait_success(client.delete(default_cert))
    assert cert1.state == 'removed'

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_multiple_certs(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[0]

    port = "406"
    ssl_port = "406"

    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain, [dom_list[1], dom_list[2]])
    lb_containers = get_service_container_list(admin_client, lb_service)
    for lb_con in lb_containers:
        host = client.by_id('host', lb_con.hosts[0].id)
        check_cert_using_openssl(
            host, port, default_domain, test_ssl_client_con)
        check_cert_using_openssl(
            host, port, dom_list[1], test_ssl_client_con)
        check_cert_using_openssl(
            host, port, dom_list[2], test_ssl_client_con)
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_sni(
        admin_client, client, socat_containers):

    port = "20001"
    client_port = "20002"
    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, includePortRule=False,
        target_with_certs=True)

    lb_service = activate_svc(client, lb_service)
    service = activate_svc(client, service)

    # Create Service1
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(
        name=service_name, stackId=env.id,
        launchConfig={"imageUuid": WEB_SSL_IMAGE2_UUID}, scale=2)

    service1 = client.wait_success(service1)
    assert service1.state == "inactive"
    service1 = activate_svc(client, service1)

    port_rules = lb_service.lbConfig["portRules"]
    port_rule = {"hostname": "test1.com",
                 "serviceId": service.id,
                 "sourcePort": port,
                 "targetPort": "443",
                 "protocol": "sni"
                 }
    port_rules.append(port_rule)
    port_rule = {"hostname": "test2.com",
                 "serviceId": service1.id,
                 "sourcePort": port,
                 "targetPort": "443",
                 "protocol": "sni"
                 }
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    wait_for_lb_service_to_become_active(admin_client, client,
                                         [service], lb_service)

    test_ssl_client_con = create_client_container_for_ssh(client, client_port)
    validate_lb_service(admin_client, client,
                        lb_service, port, [service],
                        "test1.com", "/name.html", dom_list[0],
                        test_ssl_client_con)
    validate_lb_service(admin_client, client,
                        lb_service, port, [service1],
                        "test2.com", "/name.html", dom_list[1],
                        test_ssl_client_con)
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_tcp_ssl_pass_through(
        admin_client, client, socat_containers):

    port = "20003"
    client_port = "20004"
    service_scale = 2
    lb_scale = 1

    env, service, lb_service = create_env_with_svc_and_lb(
        client, service_scale, lb_scale, port, includePortRule=False,
        target_with_certs=True)

    lb_service = activate_svc(client, lb_service)
    service = activate_svc(client, service)

    # Create Service1
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service1 = client.create_service(
        name=service_name, stackId=env.id,
        launchConfig={"imageUuid": WEB_SSL_IMAGE1_UUID}, scale=2)

    service1 = client.wait_success(service1)
    assert service1.state == "inactive"
    service1 = activate_svc(client, service1)

    port_rules = lb_service.lbConfig["portRules"]
    port_rule = {"serviceId": service.id,
                 "sourcePort": port,
                 "targetPort": "443",
                 "protocol": "tcp"
                 }
    port_rules.append(port_rule)
    port_rule = {"serviceId": service1.id,
                 "sourcePort": port,
                 "targetPort": "443",
                 "protocol": "tcp"
                 }
    port_rules.append(port_rule)

    lb_service = client.update(lb_service,
                               lbConfig=create_lb_config(port_rules))
    wait_for_lb_service_to_become_active(admin_client, client,
                                         [service], lb_service)

    test_ssl_client_con = create_client_container_for_ssh(client, client_port)
    validate_lb_service(admin_client, client,
                        lb_service, port, [service, service1],
                        None, "/name.html", dom_list[0],
                        test_ssl_client_con)
    delete_all(client, [env])


@if_certs_available
def test_lb_tls(
        admin_client, client, certs, socat_containers):

    service_count = 2
    certs = []
    port = "2005"
    port_rules = []
    port_rule = {"serviceId": 0,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "tls"
                 }
    port_rules.append(port_rule)
    port_rule = {"serviceId": 1,
                 "sourcePort": port,
                 "targetPort": "80",
                 "protocol": "tls"
                 }
    port_rules.append(port_rule)

    env, services, lb_service = \
        create_env_with_multiple_svc_and_ssl_lb(
            client, 2, 1, [port], port_rules, service_count,
            port, default_cert=get_cert(dom_list[0]), certs=certs)

    client_port = port + "0"
    test_ssl_client_con = create_client_container_for_ssh(client, client_port)
    validate_lb_service(admin_client, client,
                        lb_service, port,
                        [services[0], services[1]],
                        None, "/name.html", dom_list[0],
                        test_ssl_client_con)
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_remove_cert(
        admin_client, client, certs, socat_containers):

    default_domain = dom_list[4]
    port = "410"
    ssl_port = "410"
    service_scale = 2
    lb_scale = 1

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl(admin_client, client,
                               service_scale, lb_scale,
                               port, ssl_port,
                               default_domain)

    default_cert = get_cert(default_domain)
    with pytest.raises(ApiError) as e:
        cert1 = client.wait_success(default_cert.remove())
    assert e.value.error.status == 405
    assert e.value.error.code == 'InvalidAction'
    assert 'Certificate is in use' in e.value.error.message

    default_cert = client.reload(default_cert)
    assert default_cert.state == 'active'

    lb_service = client.wait_success(client.delete(lb_service))
    assert lb_service.state == 'removed'
    time.sleep(5)
    cert1 = client.wait_success(default_cert.remove())
    assert cert1.state == 'removed'

    delete_all(client, [env, test_ssl_client_con["container"]])
