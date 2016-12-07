from common_fixtures import *  # NOQA
import os


if_test_k8s = pytest.mark.skipif(
    not os.environ.get('TEST_K8S'),
    reason='TEST_K8S is not set')


@pytest.fixture(scope='session', autouse=True)
def create_test_pod(kube_hosts, request):
    namespace = 'dns-test'
    create_ns(namespace)
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-test.yml")
    waitfor_pods(selector="app=dns-test-pod", namespace=namespace, number=1)

    def fin():
        teardown_ns(namespace)
    request.addfinalizer(fin)


# Execute command in pod
def execute_cmd(pod, cmd, namespace):
    result = execute_kubectl_cmds(
                "exec " + pod + " --namespace=" + namespace + " -- " + cmd)
    return result


# 1,2,3
@if_test_k8s
def test_k8s_dns_service_clusterip(kube_hosts):
    namespace = 'dns-clusterip-namespace'
    create_ns(namespace)
    name = "dns-nginx"
    test_pod = "dns-test-pod"
    test_pod_namespace = "dns-test-namespace"

    # Create rc and service
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-clusterip.yml")
    waitfor_pods(selector="name="+name, namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get service "+name+" -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['spec']['ports'][0]['port'] == 8000
    clusterip = service['spec']['clusterIP']

    # test resolving service name
    cmd_result = execute_cmd(
        test_pod_namespace, "dig "+name+" +search +short", namespace)
    assert cmd_result.rstrip() == clusterip

    # test resolving service_name.namespace
    cmd_result = execute_cmd(
        test_pod,
        "dig "+name+"."+namespace+" +search +short",
        "dns-test")
    assert cmd_result.rstrip() == clusterip

    # test resolving fqdn
    cmd_result = execute_cmd(
        test_pod,
        'dig '+name+"."+namespace+'.svc.cluster.local. +short',
        "dns-test")
    assert cmd_result.rstrip() == clusterip

    # Test connectivity to the pod
    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local:8000/name.html", "dns-test")
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 4
@if_test_k8s
def test_k8s_dns_headless_service_clusterip(kube_hosts):
    namespace = 'dns-headless-namespace'
    test_pod = "dns-test-pod"
    create_ns(namespace)
    name = "dns-nginx-headless"
    # Create rc and service
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-headless-clusterip.yml")
    waitfor_pods(
        selector="name=dns-nginx-headless", namespace=namespace, number=2)

    get_response = execute_kubectl_cmds(
        "get pod --selector=name=dns-nginx-headless"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)

    pods_ips = []
    assert len(pod["items"]) == 2
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == name
        assert pod["metadata"]["namespace"] == namespace
        pods_ips.append(pod['status']['podIP'])
        container = pod["spec"]["containers"][0]
        assert container["name"] == name
        assert container["imagePullPolicy"] == "Always"
        assert pod["status"]["phase"] == "Running"

    # test resolving service name
    t = 0
    while True:
        if t >= 100:
            assert False
        cmd_result = execute_cmd(
            test_pod,
            'dig '+name+"."+namespace+'.svc.cluster.local. +short',
            "dns-test")
        if len(cmd_result.splitlines()) == 2:
            break
        else:
            time.sleep(5)
            t += 5

    ips = cmd_result.splitlines()
    ips = [ip.rstrip() for ip in ips]
    assert set(ips) == set(pods_ips)

    # Test connectivity to the pod
    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local/name.html", "dns-test")
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 5
@if_test_k8s
def test_k8s_dns_service_namedport(kube_hosts):
    namespace = 'dns-namedport-namespace'
    test_pod = "dns-test-pod"
    create_ns(namespace)
    name = "dns-nginx-namedport"
    # Create rc and service
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-namedport.yml")
    waitfor_pods(
        selector="name=dns-nginx-namedport", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get service "+name+" -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == name
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['port'] == 9999
    assert service['spec']['ports'][0]['protocol'] == "TCP"

    # test SRV record
    cmd_result = execute_cmd(
        test_pod,
        'dig SRV ' +
        '_tcpport._tcp.'+name+"."+namespace+'.svc.cluster.local. +short',
        "dns-test")
    srv_record = cmd_result.rsplit()
    assert srv_record[2] == '9999'
    assert srv_record[3] == name + '.' + namespace + '.svc.cluster.local.'

    # Test connectivity to the pod
    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local:9999/name.html", "dns-test")
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 6
@if_test_k8s
def test_k8s_dns_headless_service_namedport(kube_hosts):
    namespace = 'dns-headless-namedport-namespace'
    test_pod = "dns-test-pod"
    create_ns(namespace)
    name = "dns-headless-namedport"
    # Create rc and service
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-headless-namedport.yml")
    waitfor_pods(
        selector="name=dns-headless-namedport", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get service "+name+" -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == name
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['port'] == 9999
    assert service['spec']['ports'][0]['protocol'] == "TCP"

    # test CNAME
    t = 0
    while True:
        if t >= 100:
            assert False
        cmd_result = execute_cmd(
            test_pod,
            'dig ' +
            '_tcpport._tcp.'+name+"."+namespace+'.svc.cluster.local. +short',
            "dns-test")
        if len(cmd_result.split()) > 0:
            break
        else:
            time.sleep(5)
            t += 5
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=dns-headless-namedport"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)
    cmd_result = execute_cmd(
        test_pod,
        'dig ' +
        '_tcpport._tcp.'+name+"."+namespace+'.svc.cluster.local. +short',
        "dns-test")
    cname_record = cmd_result.rsplit()
    assert cname_record[1] == pod["items"][0]['status']['podIP']

    # test SRV record
    cmd_result = execute_cmd(
        test_pod,
        'dig SRV ' +
        '_tcpport._tcp.'+name+"."+namespace+'.svc.cluster.local. +short',
        "dns-test")
    srv_record = cmd_result.rsplit()
    assert srv_record[2] == '80'
    assert name + '.' + namespace + '.svc.cluster.local.' in srv_record[3]

    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local/name.html", "dns-test")
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 7
@if_test_k8s
def test_k8s_dns_pod(kube_hosts):
    name = 'dns-pod-nginx'
    namespace = 'dns-pod-nginx'
    test_pod = "dns-test-pod"
    create_ns(namespace)
    # pod
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-pod.yml")
    waitfor_pods(
        selector="app=dns-pod-nginx", namespace=namespace, number=1)

    get_response = execute_kubectl_cmds(
        "get pod --selector=app=dns-pod-nginx"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)
    pod_ip = pod["items"][0]['status']['podIP']
    pod_ip2 = pod_ip.replace(".", "-")

    # test ip
    cmd_result = execute_cmd(
        test_pod,
        'dig ' +
        pod_ip2+'.'+namespace+'.pod.cluster.local. +short',
        "dns-test")
    assert cmd_result.rstrip() == pod_ip

    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  pod_ip2 +
                  "." +
                  namespace +
                  ".pod.cluster.local/name.html", "dns-test")
    assert name == cmd_result.rstrip()
    teardown_ns(namespace)


# 8
@if_test_k8s
def test_k8s_dns_pod_hostname(kube_hosts):
    # hostname of the pod
    name = 'foo'
    namespace = 'dns-podhostname-nginx'
    test_pod = "dns-test-pod"
    create_ns(namespace)
    # pod
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-pod-hostname.yml")
    waitfor_pods(
        selector="app=dns-pod-hostname", namespace=namespace, number=1)

    get_response = execute_kubectl_cmds(
        "get pod --selector=app=dns-pod-hostname"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)
    pod_ip = pod["items"][0]['status']['podIP']

    # test ip
    cmd_result = execute_cmd(
        test_pod,
        'dig ' +
        'foo.bar.'+namespace+'.svc.cluster.local. +short',
        "dns-test")
    assert cmd_result.rstrip() == pod_ip

    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  'foo.bar.' + namespace +
                  ".svc.cluster.local/name.html", "dns-test")
    assert name == cmd_result.rstrip()
    teardown_ns(namespace)
