from common_fixtures import *  # NOQA

if_test_k8s = pytest.mark.skipif(
    not os.environ.get('TEST_K8S'),
    reason='TEST_K8S is not set')


@if_test_k8s
def test_k8s_ingress_1(client, kube_hosts):
    # This method tests an ingress with host, paths specified and two services

    # Create namespace
    namespace = "testingress1"
    create_ns(namespace)

    ingress_file_name = "ingress_1.yml"
    ingress_name = "ingress1"

    # Initial set up
    port = "83"
    services = []
    service1 = {}
    service1["name"] = "k8test1"
    service1["selector"] = "k8s-app=k8test1-service"
    service1["rc_name"] = "k8testrc1"
    service1["filename"] = "service1_ingress.yml"
    services.append(service1)
    service2 = {}
    service2["name"] = "k8test2"
    service2["selector"] = "k8s-app=k8test2-service"
    service2["rc_name"] = "k8testrc2"
    service2["filename"] = "service2_ingress.yml"
    services.append(service2)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    print podnames
    print lbips
    print lbips[0]

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")

    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")

    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_2(client, kube_hosts):

    # This method tests a simple ingress with just backend
    # specified and one service

    # Create namespace
    namespace = "testingress2"
    create_ns(namespace)

    # Initial set up
    ingress_file_name = "ingress_2.yml"
    ingress_name = "ingress2"

    port = "84"
    services = []
    service1 = {}
    service1["name"] = "k8test2-new"
    service1["selector"] = "k8s-app=k8test2-new-service"
    service1["rc_name"] = "k8testrc2-new"
    service1["filename"] = "service2_new_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    print podnames
    print lbips[0]
    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_3(client, kube_hosts):

    # This method tests an ingress with just backend,
    # one service and http.port specified

    # Create namespace
    namespace = "testingress3"
    create_ns(namespace)

    # Initial set up
    ingress_file_name = "ingress_3.yml"
    ingress_name = "ingress3"

    port = "85"
    services = []
    service1 = {}
    service1["name"] = "k8test3"
    service1["selector"] = "k8s-app=k8test3-service"
    service1["rc_name"] = "k8testrc3"
    service1["filename"] = "service3_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_4(client, kube_hosts):

    # This method tests multiple ingresses

    # Create namespace
    namespace = "testingress4"
    create_ns(namespace)

    # Initial set up
    ingress_file_name1 = "ingress_4_new.yml"
    ingress_name1 = "ingress4-new"

    ingress_file_name2 = "ingress_4.yml"
    ingress_name2 = "ingress4"

    port1 = "85"
    port2 = "87"
    services1 = []
    service1 = {}
    service1["name"] = "k8test4-new"
    service1["selector"] = "k8s-app=k8test4-new-service"
    service1["rc_name"] = "k8testrc4-new"
    service1["filename"] = "service4_new_ingress.yml"
    services1.append(service1)

    services2 = []
    service2 = {}
    service2["name"] = "k8test4"
    service2["selector"] = "k8s-app=k8test4-service"
    service2["rc_name"] = "k8testrc4"
    service2["filename"] = "service4_ingress.yml"
    services2.append(service2)

    ingresses1 = []
    ingress1 = {}
    ingress1["name"] = ingress_name1
    ingress1["filename"] = ingress_file_name1
    ingresses1.append(ingress1)

    ingresses2 = []
    ingress2 = {}
    ingress2["name"] = ingress_name2
    ingress2["filename"] = ingress_file_name2
    ingresses2.append(ingress2)

    # Create services, ingress and validate
    podnames1, lbips1 = create_service_ingress(ingresses1, services1,
                                               port1, namespace)
    podnames2, lbips2 = create_service_ingress(ingresses2, services2,
                                               port2, namespace)

    print podnames1
    print podnames2

    check_round_robin_access_lb_ip(podnames1[0], lbips1[0], port1,
                                   path="/name.html")

    check_round_robin_access_lb_ip(podnames2[0], lbips2[0], port2,
                                   hostheader="foo.bar.com",
                                   path="/name.html")

    # Delete ingress1
    delete_ingress(ingress_name1, namespace)

    # Delete ingress2
    delete_ingress(ingress_name2, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_5(client, kube_hosts):

    # This method case tests deletion of an ingress with just backend,
    # one service and http.port specified

    # Create namespace
    namespace = "testingress5"
    create_ns(namespace)

    # Initial set up
    ingress_file_name = "ingress_5.yml"
    ingress_name = "ingress5"

    port = "88"
    services = []
    service1 = {}
    service1["name"] = "k8test5"
    service1["selector"] = "k8s-app=k8test5-service"
    service1["rc_name"] = "k8testrc5"
    service1["filename"] = "service5_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)
    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_6(client, kube_hosts):

    # This method tests an ingress creation before the
    # creation of its associated service

    # Create namespace
    namespace = "testingress6"
    create_ns(namespace)

    port = "81"

    # Create Ingress
    ingress_file_name = "ingress_6.yml"
    ingress_name = "ingress6"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    # Create service1
    selector1 = "k8s-app=k8test6-service"
    service_name1 = "k8test6"
    rc_name1 = "k8testrc6"
    file_name1 = "service6_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    wait_until_lb_ip_is_active(lb_ip[0], port)

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)

    print lb_ip[0]
    print pod1_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], port,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_7(client, kube_hosts):

    # This method tests an ingress with two paths
    # specified[no host] and two services

    # Create namespace
    namespace = "testingress7"
    create_ns(namespace)

    # Initial set up
    ingress_file_name = "ingress_7.yml"
    ingress_name = "ingress7"

    port = "90"
    services = []
    service1 = {}
    service1["name"] = "k8test7-one"
    service1["selector"] = "k8s-app=k8test7-one-service"
    service1["rc_name"] = "k8testrc7-one"
    service1["filename"] = "service7_one_ingress.yml"
    services.append(service1)
    service2 = {}
    service2["name"] = "k8test7-two"
    service2["selector"] = "k8s-app=k8test7-two-service"
    service2["rc_name"] = "k8testrc7-two"
    service2["filename"] = "service7_two_ingress.yml"
    services.append(service2)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    print lbips[0]

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/service3.html")

    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   path="/name.html")

    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_8(client, kube_hosts):

    # This method tests an ingress with two hosts/paths
    # specified and two services

    # Create namespace
    namespace = "testingress8"
    create_ns(namespace)

    ingress_file_name = "ingress_8.yml"
    ingress_name = "ingress8"

    # Initial set up
    port = "91"
    services = []
    service1 = {}
    service1["name"] = "k8test8-one"
    service1["selector"] = "k8s-app=k8test8-one-service"
    service1["rc_name"] = "k8testrc8-one"
    service1["filename"] = "service8_one_ingress.yml"
    services.append(service1)
    service2 = {}
    service2["name"] = "k8test8-two"
    service2["selector"] = "k8s-app=k8test8-two-service"
    service2["rc_name"] = "k8testrc8-two"
    service2["filename"] = "service8_two_ingress.yml"
    services.append(service2)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")

    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   hostheader="bar.foo.com", path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_9(client, kube_hosts):

    # This method tests an ingress with rule of one host/path
    # for one service and just path specified for another service

    # Create namespace
    namespace = "testingress9"
    create_ns(namespace)

    ingress_file_name = "ingress_9.yml"
    ingress_name = "ingress9"

    # Initial set up
    port = "92"
    services = []
    service1 = {}
    service1["name"] = "k8test9-one"
    service1["selector"] = "k8s-app=k8test9-one-service"
    service1["rc_name"] = "k8testrc9-one"
    service1["filename"] = "service9_one_ingress.yml"
    services.append(service1)
    service2 = {}
    service2["name"] = "k8test9-two"
    service2["selector"] = "k8s-app=k8test9-two-service"
    service2["rc_name"] = "k8testrc9-two"
    service2["filename"] = "service9_two_ingress.yml"
    services.append(service2)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")
    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_10(client, kube_hosts):

    # This method tests ingress scaling

    # Create namespace
    namespace = "testingress10"
    create_ns(namespace)

    # Initial set up
    port = "93"

    ingress_file_name = "ingress_10.yml"
    ingress_name = "ingress10"

    services = []
    service1 = {}
    service1["name"] = "k8test10"
    service1["selector"] = "k8s-app=k8test10-service"
    service1["rc_name"] = "k8testrc10"
    service1["filename"] = "service10_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace, ing_scale=2)
    print lbips
    print lbips[0]
    print lbips[1]
    time.sleep(15)
    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/name.html")
    check_round_robin_access_lb_ip(podnames[0], lbips[1], port,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_11(client, kube_hosts):

    # This method tests updating an ingress with just backend,
    # one service and http.port specified

    # Create namespace
    namespace = "testingress11"
    create_ns(namespace)

    # Initial set up
    port = "94"

    ingress_file_name = "ingress_11.yml"
    ingress_name = "ingress11"

    # Create service1
    selector1 = "k8s-app=k8test11-service"
    service_name1 = "k8test11"
    rc_name1 = "k8testrc11"
    file_name1 = "service11_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create Ingress
    # The ingress has http.port = 94 specified
    ingress_file_name = "ingress_11.yml"
    ingress_name = "ingress11"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], port, 55)

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)
    print "The ips are:\n"
    print lb_ip[0]
    print pod1_names

    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], port,
                                   path="/name.html")

    # Replace the ingress with http.port=98
    port_new = "98"
    ingress_file_name_new = "ingress_11_replace.yml"
    expected_result = ['ingress "' + ingress_name + '" replaced']
    execute_kubectl_cmds(
        "replace ing --namespace="+namespace,
        expected_result, file_name=ingress_file_name_new)
    # The same IP could be used or a new a new IP could be assigned
    # for the Ingress. We are getting the updated IP if the old IP doesn't
    # become active with the new port number within 90s
    lb_ip_updated = lb_ip
    print lb_ip_updated[0]
    try:
        wait_until_lb_ip_is_active(lb_ip_updated[0], port_new, timeout=90)
        print "Same IP"
    except:
        lb_ip_updated = wait_for_ingress_to_become_active(ingress_name,
                                                          namespace,
                                                          ing_scale=1)
        print "New IP"
        print lb_ip_updated[0]
        wait_until_lb_ip_is_active(lb_ip_updated[0], port_new, timeout=90)

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)

    print lb_ip_updated[0]
    print pod1_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip_updated[0], port_new,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_12(client, kube_hosts, certs):

    # This method tests updating an ingress with just backend,
    # one service and http.port specified

    # Create namespace
    namespace = "testingress12"
    create_ns(namespace)

    # Initial set up
    port = "95"
    dom_list = ["test1.com"]
    domain = dom_list[0]
    certname = "certificate"

    # Create Certificate
    cert = create_cert(client, domain, certname)

    ingress_file_name = "ingress_12.yml"
    ingress_name = "ingress12"

    services = []
    service1 = {}
    service1["name"] = "k8test12"
    service1["selector"] = "k8s-app=k8test12-service"
    service1["rc_name"] = "k8testrc12"
    service1["filename"] = "service12_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/name.html")
    client_port = port + "0"
    test_ssl_client_con = create_client_container_for_ssh(client, client_port)

    check_round_robin_access_for_ssl_lb_ip(podnames[0], lbips[0], "443",
                                           domain, test_ssl_client_con,
                                           hostheader=None,
                                           path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)

    # Delete Certificate
    cert1 = client.wait_success(cert.remove(), timeout=60)
    assert cert1.state == "removed"


@if_test_k8s
def test_k8s_ingress_13(client, kube_hosts, certs):

    # This method tests incrementing pod scale and
    # testing an ingress with just backend,

    # Create namespace
    namespace = "testingress13"
    create_ns(namespace)

    # Initial set up
    port = "96"
    ingress_file_name = "ingress_13.yml"
    ingress_name = "ingress13"

    services = []
    service1 = {}
    service1["name"] = "k8test13"
    service1["selector"] = "k8s-app=k8test13-service"
    service1["rc_name"] = "k8testrc13"
    service1["filename"] = "service13_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace,
                                             scale=1)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/name.html")

    # Replace the rc with replica=3
    selector1 = "k8s-app=k8test13-service"
    rc_name1 = "k8testrc13"
    file_name_new = "rc13_new_ingress.yml"
    expected_result = ['replicationcontroller "' + rc_name1 + '" replaced']
    execute_kubectl_cmds(
        "replace rc --namespace=" + namespace,
        expected_result, file_name=file_name_new)
    waitfor_pods(selector=selector1, namespace=namespace, number=3)

    # Validate Ingress rules
    pod_new_names = get_pod_names_for_selector(selector1, namespace, scale=3)

    print lbips[0][0]
    print pod_new_names
    check_round_robin_access_lb_ip(pod_new_names, lbips[0], port,
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_14(client, kube_hosts, certs):

    # This method tests decrementing pod scale and
    # testing an ingress with just backend

    # Create namespace
    namespace = "testingress14"
    create_ns(namespace)

    # Initial set up
    port = "97"
    ingress_file_name = "ingress_14.yml"
    ingress_name = "ingress14"

    services = []
    service1 = {}
    service1["name"] = "k8test14"
    service1["selector"] = "k8s-app=k8test14-service"
    service1["rc_name"] = "k8testrc14"
    service1["filename"] = "service14_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace,
                                             scale=3)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")

    # Replace the rc with replica=1
    file_name_new = "rc14_new_ingress.yml"
    expected_result = ['replicationcontroller "' + service1["rc_name"] +
                       '" replaced']
    execute_kubectl_cmds(
        "replace rc --namespace=" + namespace,
        expected_result, file_name=file_name_new)
    waitfor_pods(selector=service1["selector"], namespace=namespace, number=1)

    # Validate Ingress rules
    pod_new_names = get_pod_names_for_selector(service1["selector"],
                                               namespace, scale=1)

    print lbips[0][0]
    print pod_new_names
    check_round_robin_access_lb_ip(pod_new_names, lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_15(client, kube_hosts):

    # This method tests updating an ingress with hostheader, path
    # specified to an ingress pointing to a different service

    # Create namespace
    namespace = "testingress15"
    create_ns(namespace)

    # Initial set up
    port = "99"
    ingress_file_name = "ingress_15.yml"
    ingress_name = "ingress15"

    services = []
    service1 = {}
    service1["name"] = "k8test15-one"
    service1["selector"] = "k8s-app=k8test15-one-service"
    service1["rc_name"] = "k8testrc15-one"
    service1["filename"] = "service15_one_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")

    # Create service2
    selector2 = "k8s-app=k8test15-two-service"
    service_name2 = "k8test15-two"
    rc_name2 = "k8testrc15-two"
    file_name2 = "service15_two_ingress.yml"
    create_k8_service(file_name2, namespace, service_name2, rc_name2,
                      selector2, scale=2, wait_for_service=True)

    # Replace the ingress with to point to a
    # different target service k8test15-two
    ingress_file_name_new = "ingress_15_new.yml"
    expected_result = ['ingress "' + ingress_name + '" replaced']
    execute_kubectl_cmds(
        "replace ing --namespace="+namespace,
        expected_result, file_name=ingress_file_name_new)
    wait_until_lb_ip_is_active(lbips[0], port, timeout=120)

    # Validate Ingress rules
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print lbips[0]
    print pod2_names
    check_round_robin_access_lb_ip(pod2_names, lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_16(client, kube_hosts):

    # This method tests updating an ingress with just backend,
    # to an ingress with different http.port, hostheader,
    # path and different service

    # Create namespace
    namespace = "testingress16"
    create_ns(namespace)

    # Initial set up
    port = "100"
    ingress_file_name = "ingress_16.yml"
    ingress_name = "ingress16"

    services = []
    service1 = {}
    service1["name"] = "k8test16-one"
    service1["selector"] = "k8s-app=k8test16-one-service"
    service1["rc_name"] = "k8testrc16-one"
    service1["filename"] = "service16_one_ingress.yml"
    services.append(service1)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   path="/service3.html")

    # Create service2
    selector2 = "k8s-app=k8test16-two-service"
    service_name2 = "k8test16-two"
    rc_name2 = "k8testrc16-two"
    file_name2 = "service16_two_ingress.yml"
    create_k8_service(file_name2, namespace, service_name2, rc_name2,
                      selector2, scale=2, wait_for_service=True)

    # Replace the ingress with with a different
    # port number, host-header and service
    port_new = "101"
    ingress_file_name_new = "ingress_16_new.yml"
    expected_result = ['ingress "' + ingress_name + '" replaced']
    execute_kubectl_cmds(
        "replace ing --namespace="+namespace,
        expected_result, file_name=ingress_file_name_new)
    lb_ip_updated = lbips
    print "Lb IP"
    print lb_ip_updated
    try:
        wait_until_lb_ip_is_active(lb_ip_updated[0], port_new, timeout=90)
        print "Same IP"
    except:
        lb_ip_updated = wait_for_ingress_to_become_active(ingress_name,
                                                          namespace,
                                                          ing_scale=1)
        print "New IP"
        print lb_ip_updated[0]
        wait_until_lb_ip_is_active(lb_ip_updated[0], port_new, timeout=90)

    # Validate Ingress rules
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print pod2_names
    check_round_robin_access_lb_ip(pod2_names, lb_ip_updated[0], port_new,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_17(client, kube_hosts):

    # This method tests an ingress with http.port pointing to two services
    # with different hostheaders and same serviceport

    # Create namespace
    namespace = "testingress17"
    create_ns(namespace)

    ingress_file_name = "ingress_17.yml"
    ingress_name = "ingress17"

    # Initial set up
    port = "101"
    services = []
    service1 = {}
    service1["name"] = "k8test17-one"
    service1["selector"] = "k8s-app=k8test17-one-service"
    service1["rc_name"] = "k8testrc17-one"
    service1["filename"] = "service17_one_ingress.yml"
    services.append(service1)
    service2 = {}
    service2["name"] = "k8test17-two"
    service2["selector"] = "k8s-app=k8test17-two-service"
    service2["rc_name"] = "k8testrc17-two"
    service2["filename"] = "service17_two_ingress.yml"
    services.append(service2)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate

    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)
    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")
    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   hostheader="bar.foo.com",
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_18(client, kube_hosts):
    # This method tests an ingress with a "-" in the namespace
    # Creating a namespace with "-" in Kubernetes 1.2 fails
    # to inject IP for the ingress. It works in Kubernetes 1.3
    # Bug #5213

    # Create namespace with "-"
    namespace = "testingress-18"
    create_ns(namespace)

    ingress_file_name = "ingress_18.yml"
    ingress_name = "ingress18"

    # Initial set up
    port = "102"
    services = []
    service1 = {}
    service1["name"] = "k8test1"
    service1["selector"] = "k8s-app=k8test1-service"
    service1["rc_name"] = "k8testrc1"
    service1["filename"] = "service1_ingress.yml"
    services.append(service1)
    service2 = {}
    service2["name"] = "k8test2"
    service2["selector"] = "k8s-app=k8test2-service"
    service2["rc_name"] = "k8testrc2"
    service2["filename"] = "service2_ingress.yml"
    services.append(service2)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace)

    print podnames
    print lbips
    print lbips[0]

    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")

    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")

    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_19(client, kube_hosts):
    # This method is to test that for an ingress, the lb traffic
    # is not directed to pods with the same selector
    # in different namespaces (Bug #5215)

    # Create namespace
    namespace1 = "testingress19"
    create_ns(namespace1)

    namespace2 = "testingress-new"
    create_ns(namespace2)

    ingress_file_name = "ingress_19.yml"
    ingress_name = "ingress19"

    # Initial set up
    port = "103"
    services1 = []
    service1 = {}
    service1["name"] = "k8test1"
    service1["selector"] = "k8s-app=k8test1-service"
    service1["rc_name"] = "k8testrc1"
    service1["filename"] = "service1_ingress.yml"
    services1.append(service1)

    service2 = {}
    service2["name"] = "k8test2"
    service2["selector"] = "k8s-app=k8test2-service"
    service2["rc_name"] = "k8testrc2"
    service2["filename"] = "service2_ingress.yml"
    services1.append(service2)

    # Create another service k8test1 in the second namespace
    service3 = {}
    service3["name"] = "k8test1"
    service3["selector"] = "k8s-app=k8test1-service"
    service3["rc_name"] = "k8testrc1"
    service3["filename"] = "service1_ingress.yml"

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services in both the namespaces and ingress

    create_k8_service(service3["filename"], namespace2,
                      service3["name"], service3["rc_name"],
                      service3["selector"], scale=2,
                      wait_for_service=True)
    # Pods for service3
    podnameslist = get_pod_names_for_selector(service3["selector"],
                                              namespace2, scale=2)
    print podnameslist
    # Pods for service1 and service2
    podnames, lbips = create_service_ingress(ingresses, services1,
                                             port, namespace1)
    print podnames
    print lbips
    print lbips[0][0]

    # Validate the ingress
    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")

    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace1)
    teardown_ns(namespace1)
    teardown_ns(namespace2)


@if_test_k8s
def test_k8s_ingress_20(client, kube_hosts):
    # This method is to test an ingress in which
    # lb traffic is routed to the same service from
    # different domains/same paths

    # Create namespace
    namespace = "testingress20"
    create_ns(namespace)

    ingress_file_name = "ingress_20.yml"
    ingress_name = "ingress20"

    # Initial set up
    port = "104"
    services = []
    service1 = {}
    service1["name"] = "k8test20-one"
    service1["selector"] = "k8s-app=k8test20-one-service"
    service1["rc_name"] = "k8testrc20-one"
    service1["filename"] = "service20_one_ingress.yml"
    services.append(service1)

    service2 = {}
    service2["name"] = "k8test20-two"
    service2["selector"] = "k8s-app=k8test20-two-service"
    service2["rc_name"] = "k8testrc20-two"
    service2["filename"] = "service20_two_ingress.yml"
    services.append(service2)

    service3 = {}
    service3["name"] = "k8test20-three"
    service3["selector"] = "k8s-app=k8test20-three-service"
    service3["rc_name"] = "k8testrc20-three"
    service3["filename"] = "service20_three_ingress.yml"
    services.append(service3)

    ingresses = []
    ingress = {}
    ingress["name"] = ingress_name
    ingress["filename"] = ingress_file_name
    ingresses.append(ingress)

    # Create services, ingress and validate
    podnames, lbips = create_service_ingress(ingresses, services,
                                             port, namespace, scale=2)
    print "The list of pods:"
    print podnames[0]
    print podnames[1]
    print podnames[2]

    # Validate the ingress
    check_round_robin_access_lb_ip(podnames[0], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")

    check_round_robin_access_lb_ip(podnames[2], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")

    check_round_robin_access_lb_ip(podnames[1], lbips[0], port,
                                   hostheader="bar.foo.com",
                                   path="/service3.html")

    check_round_robin_access_lb_ip(podnames[2], lbips[0], port,
                                   hostheader="bar.foo.com",
                                   path="/name.html")
    # Delete ingress
    delete_ingress(ingress_name, namespace)
    teardown_ns(namespace)
