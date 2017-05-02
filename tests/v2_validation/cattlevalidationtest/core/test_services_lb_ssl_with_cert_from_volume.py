from common_fixtures import *  # NOQA
from test_storage_nfs_driver import check_for_nfs_driver

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if_certs_available = pytest.mark.skipif(
    not os.path.isdir(SSLCERT_SUBDIR),
    reason='ssl cert file directory not found')

dom_list = readDataFile(SSLCERT_SUBDIR, "certlist.txt").rstrip().split(",")
test_cert_con = {}
cert_change_interval = os.environ.get('CATTLE_CERT_CHANGE_INTERVAL',
                                      '45')
service_names_list = ["lb-withselectorlinks", "s1", "s2"]
shared_vol_name = "mytestcerts" + "-" + random_str()


@pytest.fixture(scope='session')
def test_cert_container(admin_client, client, request):
    assert check_for_nfs_driver(client)
    volume = client.create_volume(driver="rancher-nfs",
                                  name=shared_vol_name)
    volume = wait_for_condition(client,
                                volume,
                                lambda x: x.state == "inactive",
                                lambda x: 'Volume state is ' + x.state)
    assert volume.state == "inactive"
    stack_name = \
        random_str().replace("-", "") + "-lb-vol-client"

    dc_yml = readDataFile(SSLCERT_SUBDIR, "haproxycert_testclient_dc.yml")
    dc_yml = dc_yml.replace("$volname", shared_vol_name)
    with open(os.path.join(SSLCERT_SUBDIR, "m_haproxycert_testclient_dc.yml"),
              "wt") as fout:
        fout.write(dc_yml)
    fout.close()

    stack, services = create_stack_with_multiple_service_using_rancher_cli(
        client, stack_name, ["testclient"],
        SSLCERT_SUBDIR,
        "m_haproxycert_testclient_dc.yml")
    assert services["testclient"].state == "active"

    service_cons = client.list_service(
        uuid=services["testclient"].uuid,
        include="instances",
        )
    assert len(service_cons) == 1
    assert len(service_cons[0].instances) == 1
    con_info = client.list_container(
        uuid=service_cons[0].instances[0].uuid,
        include="hosts")
    assert len(con_info) == 1
    test_cert_con["con"] = con_info[0]
    test_cert_con["host"] = con_info[0].hosts[0].agentIpAddress
    test_cert_con["port"] = "7890"


def create_lb_services_ssl_with_cert(admin_client, client,
                                     stack_name, service_names,
                                     lb_port, label,
                                     dc_yml_file, rc_yml_file,
                                     default_domain=None, domains=None):

    upload_initial_certs(domains, default_domain)
    client_port = lb_port + "0"

    dc_yml = readDataFile(SSLCERT_SUBDIR, dc_yml_file)
    rc_yml = readDataFile(SSLCERT_SUBDIR, rc_yml_file)

    dc_yml = dc_yml.replace("$lbimage", get_lb_image_version(admin_client))
    dc_yml = dc_yml.replace("$label", label)
    dc_yml = dc_yml.replace("$port", lb_port)
    dc_yml = dc_yml.replace("$volname", shared_vol_name)

    rc_yml = rc_yml.replace("$label", label)
    rc_yml = rc_yml.replace("$port", lb_port)

    modified_dc_yml_file = "lb_cert_dc.yml"
    modified_rc_yml_file = "lb_cert_rc.yml"

    with open(os.path.join(SSLCERT_SUBDIR, modified_dc_yml_file),
              "wt") as fout:
        fout.write(dc_yml)
    fout.close()

    with open(os.path.join(SSLCERT_SUBDIR, modified_rc_yml_file),
              "wt") as fout:
        fout.write(rc_yml)
    fout.close()

    stack, services = create_stack_with_multiple_service_using_rancher_cli(
        client, stack_name, service_names,
        SSLCERT_SUBDIR,
        modified_dc_yml_file,
        modified_rc_yml_file)

    lb_service = services[service_names[0]]
    target_services = [services[service_names[1]], services[service_names[2]]]
    test_ssl_client_con = create_client_container_for_ssh(client, client_port)
    validate_lb_services_ssl(admin_client, client, test_ssl_client_con,
                             target_services, lb_service,
                             lb_port, default_domain, domains)
    return stack, target_services, lb_service, test_ssl_client_con


def upload_initial_certs(cert_list, default_cert=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        test_cert_con["host"], username="root",
        password="root", port=int(test_cert_con["port"]))
    cmd = "mkdir -p /certs/mycerts;"
    cmd += "cd /certs/mycerts;rm -rf *;"
    cmd += "mkdir -p /certs/default.com;"
    cmd += "cd /certs/default.com;rm -rf *;"
    for domain_name in cert_list:
        cmd += "cd /certs/mycerts;"
        cmd += cmd_for_cert_creation(domain_name)
    cmd += "cd /certs/default.com;"
    if default_cert is not None:
        cmd += cmd_for_cert_creation(default_cert)
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    logger.info(response)


def upload_additional_certs(cert_list=None, default_cert=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        test_cert_con["host"], username="root",
        password="root", port=int(test_cert_con["port"]))
    if cert_list is not None:
        for domain_name in cert_list:
            cmd = "cd /certs/mycerts;"
            cmd += cmd_for_cert_creation(domain_name)
    if default_cert is not None:
        cmd = "cd /certs/default.com;"
        cmd += cmd_for_cert_creation(default_cert)
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    logger.info(response)


def edit_existing_certs(existing_cert, modified_cert, is_default_cert=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        test_cert_con["host"], username="root",
        password="root", port=int(test_cert_con["port"]))
    cert, key, certChain = get_cert_for_domain(modified_cert)
    cert_file = existing_cert + ".crt"
    key_file = existing_cert + ".key"

    if is_default_cert:
        cmd = "cd /certs/default.com/" + existing_cert + ";"
    else:
        cmd = "cd /certs/mycerts/" + existing_cert + ";"
    cmd += 'echo "' + cert + '" > ' + cert_file + ";"
    cmd += 'echo "' + key + '" > ' + key_file + ";"
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    logger.info(response)


def delete_existing_certs(cert_list=None, default_cert=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        test_cert_con["host"], username="root",
        password="root", port=int(test_cert_con["port"]))
    if cert_list is not None:
        for domain_name in cert_list:
            cmd = "cd /certs/mycerts;"
            cmd += "rm -rf " + domain_name + ";"
    if default_cert is not None:
        cmd = "cd /certs/default.com;"
        cmd += "rm -rf " + default_cert + ";"
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    logger.info(response)


def cmd_for_cert_creation(domain_name):
    cert, key, certChain = get_cert_for_domain(domain_name)
    cmd = "mkdir " + domain_name + ";"
    cmd += "cd " + domain_name + ";"
    cert_file = domain_name + ".crt"
    key_file = domain_name + ".key"
    cmd += 'echo "' + cert + '" > ' + cert_file + ";"
    cmd += 'echo "' + key + '" > ' + key_file + ";"
    cmd += "ln -s " + key_file + " fullchain.pem;"
    cmd += "ln -s " + cert_file + " privkey.pem;"
    return cmd


def validate_lb_services_ssl(admin_client, client, test_ssl_client_con,
                             services, lb_service, ssl_port,
                             default_domain=None, domains=None):

    wait_for_lb_service_to_become_active(admin_client, client,
                                         services, lb_service)
    supported_domains = []
    if default_domain is not None:
        supported_domains.append(default_domain)
    if domains:
        supported_domains.extend(domains)

    for domain in supported_domains:
        validate_lb_service(admin_client, client,
                            lb_service, ssl_port,
                            [services[0]],
                            "test1.com", "/service1.html", domain,
                            test_ssl_client_con)
        validate_lb_service(admin_client, client,
                            lb_service, ssl_port, [services[1]],
                            "test2.com", "/service2.html", domain,
                            test_ssl_client_con)


@if_certs_available
def test_lb_ssl_with_certs_and_default_cert(admin_client, client,
                                            socat_containers,
                                            rancher_cli_container,
                                            test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5656"
    label = "test1"
    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert"
    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)

    # Attempting to access LB rules with cert other supported default
    # cert/cert list should return certificate error

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_with_certs_and_default_cert_scaleup_lb(admin_client, client,
                                                       socat_containers,
                                                       rancher_cli_container,
                                                       test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5655"
    label = "test2"

    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert"
    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)

    # Attempting to access LB rules with cert other supported default
    # cert/cert list should return certificate error

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    final_lb_scale = 2
    lb_service = client.update(lb_service, scale=final_lb_scale,
                               name=lb_service.name)

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    assert lb_service.scale == final_lb_scale
    validate_lb_services_ssl(admin_client, client, test_ssl_client_con,
                             services, lb_service,
                             port, default_domain, domain_list)

    # Attempting to access LB rules with cert other supported default
    # cert/cert list should return certificate error

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_with_certs_and_default_cert_scaleup_target(
        admin_client, client, socat_containers,
        rancher_cli_container,
        test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5654"
    label = "test3"

    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert"
    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)

    # Attempting to access LB rules with cert other supported default
    # cert/cert list should return certificate error

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    # Scale up target service
    final_service_scale = 3
    services[0] = client.update(services[0], scale=final_service_scale,
                                name=services[0].name)
    services[0] = client.wait_success(services[0], 120)

    assert services[0].state == "active"
    assert services[0].scale == final_service_scale

    validate_lb_services_ssl(admin_client, client, test_ssl_client_con,
                             services, lb_service,
                             port, default_domain, domain_list)

    # Attempting to access LB rules with cert other supported default
    # cert/cert list should return certificate error

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_with_default_cert_add(admin_client, client,
                                      socat_containers,
                                      rancher_cli_container,
                                      test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5657"
    label = "test3"

    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert-addcert"

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)
    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    # add cert
    upload_additional_certs(cert_list=[cert], default_cert=None)
    time.sleep(int(cert_change_interval))

    # Should be able to access LB using the newly added cert
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", cert,
                        test_ssl_client_con)
    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_with_default_cert_delete(admin_client, client,
                                         socat_containers,
                                         rancher_cli_container,
                                         test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5658"
    label = "test5"

    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert-deletecert"

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)

    # Delete cert
    cert = dom_list[2]
    delete_existing_certs(cert_list=[cert], default_cert=None)
    time.sleep(int(cert_change_interval))

    # Existing certs should continue to work
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[0],
                        test_ssl_client_con)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[1],
                        test_ssl_client_con)

    # Attempting to access LB rules using the delete cert should return
    # certificate error

    cert = dom_list[2]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_with_default_cert_edit(admin_client, client,
                                       socat_containers,
                                       rancher_cli_container,
                                       test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5659"
    label = "test6"

    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert-editcert"

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)

    # Edit cert contents to point to a different domain
    existing_cert = dom_list[2]
    modified_cert = dom_list[3]
    edit_existing_certs(existing_cert, modified_cert, is_default_cert=False)
    time.sleep(int(cert_change_interval))

    # Existing certs should continue to work
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[0],
                        test_ssl_client_con)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[1],
                        test_ssl_client_con)

    # Attempting to access LB rules using the new value for the modified cert
    # should succeed

    cert = dom_list[3]
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", cert,
                        test_ssl_client_con)

    # Attempting to access LB rules using the older value of the modified cert
    # should fail

    cert = dom_list[2]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_delete_default_cert(admin_client, client,
                                    socat_containers,
                                    rancher_cli_container,
                                    test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5660"
    label = "test7"

    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert-deletecert"

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)

    # Delete default cert
    cert = dom_list[0]
    delete_existing_certs(cert_list=None, default_cert=cert)
    time.sleep(int(cert_change_interval))

    # Existing certs should continue to work
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[1],
                        test_ssl_client_con)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[2],
                        test_ssl_client_con)

    # Attempting to access LB rules using the deleted cert should return
    # certificate error (strict sni check)

    cert = dom_list[0]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        None, cert,
                        test_ssl_client_con=test_ssl_client_con,
                        strict_sni_check=True)

    # Attempting to access LB rules using certs other than any certs in the
    # cert list should return certificate error (strict sni check)

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        None, cert,
                        test_ssl_client_con=test_ssl_client_con,
                        strict_sni_check=True)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_edit_default_cert(admin_client, client,
                                  socat_containers,
                                  rancher_cli_container,
                                  test_cert_container):
    default_domain = dom_list[0]
    domain_list = [dom_list[1], dom_list[2]]

    port = "5661"
    label = "test8"

    stack_name = \
        random_str().replace("-", "") + "-withcertanddefaultcert-editcert"

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         default_domain, domain_list)

    # Edit cert contents to point to a different domain
    existing_cert = dom_list[0]
    modified_cert = dom_list[3]
    edit_existing_certs(existing_cert, modified_cert, is_default_cert=True)
    time.sleep(int(cert_change_interval))

    # Existing certs should continue to work
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[1],
                        test_ssl_client_con)
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", dom_list[2],
                        test_ssl_client_con)

    # Attempting to access LB rules using the new value for the modified cert
    # should succeed

    cert = dom_list[3]
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", cert,
                        test_ssl_client_con)

    # Attempting to access LB rules using the older value of the modified cert
    # should fail and new default cert should be presented to the user

    default_domain = dom_list[3]

    cert = dom_list[0]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    cert = dom_list[4]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)

    delete_all(client, [env, test_ssl_client_con["container"]])


@if_certs_available
def test_lb_ssl_add_default_cert(admin_client, client,
                                 socat_containers,
                                 rancher_cli_container,
                                 test_cert_container):
    domain_list = [dom_list[1], dom_list[2]]

    port = "5662"
    label = "test9"

    stack_name = \
        random_str().replace("-", "") + "-withcert-add-defaultcert"

    env, services, lb_service, test_ssl_client_con = \
        create_lb_services_ssl_with_cert(admin_client, client,
                                         stack_name,
                                         service_names_list,
                                         port, label,
                                         "haproxycert_dc.yml",
                                         "haproxycert_rc.yml",
                                         None, domain_list)

    # Attempting to access LB rules using any cert other than certs from
    # cert list should result in certificate error (strict sni check)

    cert = dom_list[0]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        None, cert,
                        test_ssl_client_con=test_ssl_client_con,
                        strict_sni_check=True)

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        None, cert,
                        test_ssl_client_con=test_ssl_client_con,
                        strict_sni_check=True)

    default_domain = dom_list[0]
    # add default cert
    upload_additional_certs(cert_list=[], default_cert=default_domain)
    time.sleep(int(cert_change_interval))

    # Attempting to access LB rules using the newly added default cert
    # should succeed
    validate_lb_service(admin_client, client,
                        lb_service, port, [services[0]],
                        "test1.com", "/service1.html", default_domain,
                        test_ssl_client_con)

    # Attempting to access LB rules using any cert other than certs from
    # cert list should result in certificate error with default cert
    # being presented to the user

    cert = dom_list[3]
    validate_cert_error(admin_client, client, lb_service, port, cert,
                        default_domain, cert,
                        test_ssl_client_con=test_ssl_client_con)
    delete_all(client, [env, test_ssl_client_con["container"]])
