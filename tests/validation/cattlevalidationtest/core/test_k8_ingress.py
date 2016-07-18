from common_fixtures import *  # NOQA


if_test_k8s = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY') or
    not os.environ.get('TEST_K8S'),
    reason='DIGITALOCEAN_KEY/TEST_K8S is not set')


@if_test_k8s
def test_k8s_ingress_1(client, kube_hosts):
    # This method tests an ingress with host, paths specified and two services

    # Create namespace
    namespace = "testingress1"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service1_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create service2
    selector2 = "k8s-app=k8test2-service"
    service_name2 = "k8test2"
    rc_name2 = "k8testrc2"
    file_name2 = "service2_ingress.yml"
    create_k8_service(file_name2, namespace, service_name2, rc_name2,
                      selector2, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_1.yml"
    ingress_name = "ingress1"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], "80")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print lb_ip[0]
    print pod1_names
    print pod2_names
    check_round_robin_access_lb_ip(pod2_names, lb_ip[0], "80",
                                   hostheader="foo.bar.com", path="/name.html")
    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "80",
                                   hostheader="foo.bar.com",
                                   path="/service3.html")
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_2(client, kube_hosts):

    # This method tests a simple ingress with just backend
    # specified and one service

    # Create namespace
    namespace = "testingress2"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service3_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_2.yml"
    ingress_name = "ingress2"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], "80")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)

    print lb_ip
    print pod1_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "80",
                                   path="/name.html")
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_3(client, kube_hosts):

    # This method tests an ingress with just backend,
    # one service and http.port specified

    # Create namespace
    namespace = "testingress3"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service3_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_3.yml"
    ingress_name = "ingress3"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], "99")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)

    print lb_ip
    print pod1_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "99",
                                   path="/name.html")
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_4(client, kube_hosts):

    # This method tests multiple ingresses

    # Create namespace
    namespace = "testingress4"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service3_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)
    # Create service2
    selector2 = "k8s-app=k8test-service"
    service_name2 = "k8test"
    rc_name2 = "k8testrc"
    file_name2 = "service4_ingress.yml"
    create_k8_service(file_name2, namespace, service_name2, rc_name2,
                      selector2, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name1 = "ingress_3.yml"
    ingress_name1 = "ingress3"

    lb_ip1 = create_ingress(ingress_file_name1, ingress_name1, namespace,
                            wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip1[0], "99")

    ingress_file_name2 = "ingress_4.yml"
    ingress_name2 = "ingress4"

    lb_ip2 = create_ingress(ingress_file_name2, ingress_name2, namespace,
                            wait_for_ingress=True)

    wait_until_lb_ip_is_active(lb_ip2[0], "80")
    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print lb_ip1
    print lb_ip2
    print pod1_names
    print pod2_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip1[0], "99",
                                   path="/name.html")
    check_round_robin_access_lb_ip(pod2_names, lb_ip2[0], "80",
                                   hostheader="foo.bar.com", path="/name.html")
    # Delete ingress
    expected_result = ['ingress "' + ingress_name1 + '" deleted']
    execute_kubectl_cmds(
        "delete ing "+ingress_name1+" --namespace="+namespace, expected_result)

    # Delete ingress
    expected_result = ['ingress "' + ingress_name2 + '" deleted']
    execute_kubectl_cmds(
        "delete ing "+ingress_name2+" --namespace="+namespace, expected_result)

    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_5(client, kube_hosts):

    # This method case tests deletion of an ingress with just backend,
    # one service and http.port specified

    # Create namespace
    namespace = "testingress5"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service3_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_3.yml"
    ingress_name = "ingress3"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], "99")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)

    print lb_ip
    print pod1_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "99",
                                   path="/name.html")

    # Delete ingress
    expected_result = ['ingress "' + ingress_name + '" deleted']
    execute_kubectl_cmds(
        "delete ing "+ingress_name+" --namespace="+namespace, expected_result)
    # Verify rc is deleted
    expected_error = \
        'Error from server: ingresses.extensions "'+ingress_name+'" not found'
    execute_kubectl_cmds(
        "get ing "+ingress_name+" -o json --namespace="+namespace,
        expected_error=expected_error)

    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_6(client, kube_hosts):

    # This method tests an ingress creation before the
    # creation of its associated service

    # Create namespace
    namespace = "testingress6"
    create_ns(namespace)

    # Create Ingress
    ingress_file_name = "ingress_5.yml"
    ingress_name = "ingress5"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service3_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    wait_until_lb_ip_is_active(lb_ip[0], "80")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)

    print lb_ip[0]
    print pod1_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "80",
                                   path="/name.html")
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_7(client, kube_hosts):

    # This method tests an ingress with two paths
    # specified[no host] and two services

    # Create namespace
    namespace = "testingress7"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service1_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create service2
    selector2 = "k8s-app=k8test2-service"
    service_name2 = "k8test2"
    rc_name2 = "k8testrc2"
    file_name2 = "service2_ingress.yml"
    create_k8_service(file_name2, namespace, service_name2, rc_name2,
                      selector2, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_6.yml"
    ingress_name = "ingress6"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], "80")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print lb_ip[0]
    print pod1_names
    print pod2_names

    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "80",
                                   path="/service3.html")
    check_round_robin_access_lb_ip(pod2_names, lb_ip[0], "80",
                                   path="/name.html")
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_8(client, kube_hosts):

    # This method tests an ingress with two hosts/paths
    # specified and two services

    # Create namespace
    namespace = "testingress8"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service1_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create service2
    selector2 = "k8s-app=k8test2-service"
    service_name2 = "k8test2"
    rc_name2 = "k8testrc2"
    file_name2 = "service2_ingress.yml"
    create_k8_service(file_name2, namespace, service_name2, rc_name2,
                      selector2, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_7.yml"
    ingress_name = "ingress7"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], "80")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print lb_ip[0]
    print pod1_names
    print pod2_names

    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "80",
                                   hostheader="foo.bar.com",
                                   path="/service3.html")
    check_round_robin_access_lb_ip(pod2_names, lb_ip[0], "80",
                                   hostheader="bar.foo.com", path="/name.html")
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_9(client, kube_hosts):

    # This method tests an ingress with rule of one host/path
    # and just path specified and two services

    # Create namespace
    namespace = "testingress9"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service1_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create service2
    selector2 = "k8s-app=k8test2-service"
    service_name2 = "k8test2"
    rc_name2 = "k8testrc2"
    file_name2 = "service2_ingress.yml"
    create_k8_service(file_name2, namespace, service_name2, rc_name2,
                      selector2, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_8.yml"
    ingress_name = "ingress8"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace,
                           wait_for_ingress=True)
    wait_until_lb_ip_is_active(lb_ip[0], "80")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print lb_ip[0]
    print pod1_names
    print pod2_names

    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "80",
                                   hostheader="foo.bar.com",
                                   path="/service3.html")
    check_round_robin_access_lb_ip(pod2_names, lb_ip[0], "80",
                                   path="/name.html")
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_ingress_10(client, kube_hosts):

    # This method tests ingress scaling

    # Create namespace
    namespace = "testingress10"
    create_ns(namespace)

    # Create service1
    selector1 = "k8s-app=k8test1-service"
    service_name1 = "k8test1"
    rc_name1 = "k8testrc1"
    file_name1 = "service3_ingress.yml"
    create_k8_service(file_name1, namespace, service_name1, rc_name1,
                      selector1, scale=2, wait_for_service=True)

    # Create Ingress
    ingress_file_name = "ingress_scale.yml"
    ingress_name = "ingressscale"

    lb_ip = create_ingress(ingress_file_name, ingress_name, namespace, 2,
                           wait_for_ingress=True)
    print "Length of ip list is"
    print len(lb_ip)
    print "The lb ipss are:  "
    print lb_ip[0]
    print lb_ip[1]
    wait_until_lb_ip_is_active(lb_ip[0], "80")
    time.sleep(10)
    wait_until_lb_ip_is_active(lb_ip[1], "80")
    time.sleep(15)

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)

    print lb_ip
    print pod1_names
    check_round_robin_access_lb_ip(pod1_names, lb_ip[0], "80",
                                   path="/name.html")
    check_round_robin_access_lb_ip(pod1_names, lb_ip[1], "80",
                                   path="/name.html")
    teardown_ns(namespace)
