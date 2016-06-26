from common_fixtures import *  # NOQA


if_test_k8s = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY') or
    not os.environ.get('TEST_K8S'),
    reason='DIGITALOCEAN_KEY/TEST_K8S is not set')


@if_test_k8s
def test_k8s_ingress_1(client, kube_hosts):
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
    wait_until_lb_ip_is_active(lb_ip, "80")

    # Validate Ingress rules
    pod1_names = get_pod_names_for_selector(selector1, namespace, scale=2)
    pod2_names = get_pod_names_for_selector(selector2, namespace, scale=2)

    print lb_ip
    print pod1_names
    print pod2_names
    check_round_robin_access_lb_ip(pod2_names, lb_ip, "80",
                                   hostheader="foo.bar.com", path="/name.html")
    check_round_robin_access_lb_ip(pod1_names, lb_ip, "80",
                                   hostheader="foo.bar.com",
                                   path="/service3.html")
    teardown_ns(namespace)
