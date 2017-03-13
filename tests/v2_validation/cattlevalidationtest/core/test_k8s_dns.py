from common_fixtures import *  # NOQA


if_test_k8s = pytest.mark.skipif(
    RANCHER_ORCHESTRATION != "k8s",
    reason='RANCHER_ORCHESTRATION is not k8s')


random_ns = random_str()


def waitfor_dns_records(cmd, namespace, pod):
    t = 0
    while True:
        if t >= 100:
            assert False
        cmd_result = execute_cmd(pod, cmd, namespace)
        if cmd_result.rstrip() != "":
            break
        else:
            time.sleep(5)
            t += 5


@pytest.fixture(scope='session', autouse=True)
def create_test_pod(kube_hosts, request):
    namespace = random_ns + '-dns-test'
    name = "dns-test-pod"
    create_ns(namespace)
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dns-test.yml")
    waitfor_pods(selector="app="+name, namespace=namespace, number=1)

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
    namespace = random_ns + '-dns-clusterip-namespace'
    create_ns(namespace)
    name = "dns-nginx"
    local_test_pod = "dns-test-clusterip"
    global_test_pod = "dns-test-pod"
    global_test_pod_namespace = random_ns + "-dns-test"

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
    cmd = "dig "+name+" +search +short"
    waitfor_dns_records(cmd, namespace, local_test_pod)
    cmd_result = execute_cmd(
        local_test_pod, cmd, namespace)
    assert cmd_result.rstrip() == clusterip

    # test resolving service_name.namespace
    cmd_result = execute_cmd(
        global_test_pod,
        "dig "+name+"."+namespace+" +search +short",
        global_test_pod_namespace)
    assert cmd_result.rstrip() == clusterip

    # test resolving fqdn
    cmd_result = execute_cmd(
        global_test_pod,
        'dig '+name+"."+namespace+'.svc.cluster.local. +short',
        global_test_pod_namespace)
    assert cmd_result.rstrip() == clusterip

    # Test connectivity to the pod
    cmd_result = execute_cmd(
                  global_test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local:8000/name.html",
                  global_test_pod_namespace)
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 4
@if_test_k8s
def test_k8s_dns_headless_service_clusterip(kube_hosts):
    namespace = random_ns + '-dns-headless-namespace'
    global_test_pod_namespace = random_ns + "-dns-test"
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
    cmd = 'dig '+name+"."+namespace+'.svc.cluster.local. +short'
    waitfor_dns_records(cmd, global_test_pod_namespace, test_pod)
    cmd_result = execute_cmd(
        test_pod,
        cmd,
        global_test_pod_namespace)
    ips = cmd_result.splitlines()
    ips = [ip.rstrip() for ip in ips]
    assert set(ips) == set(pods_ips)

    # Test connectivity to the pod
    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local/name.html", global_test_pod_namespace)
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 5
@if_test_k8s
def test_k8s_dns_service_namedport(kube_hosts):
    namespace = random_ns + '-dns-namedport-namespace'
    global_test_pod_namespace = random_ns + "-dns-test"
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
    cmd = 'dig SRV ' \
          '_tcpport._tcp.'+name+"."+namespace+'.svc.cluster.local. +short'
    waitfor_dns_records(cmd, global_test_pod_namespace, test_pod)
    cmd_result = execute_cmd(
        test_pod,
        cmd,
        global_test_pod_namespace)
    srv_record = cmd_result.rsplit()
    assert srv_record[2] == '9999'
    assert srv_record[3] == name + '.' + namespace + '.svc.cluster.local.'

    # Test connectivity to the pod
    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local:9999/name.html",
                  global_test_pod_namespace)
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 6
@if_test_k8s
def test_k8s_dns_headless_service_namedport(kube_hosts):
    namespace = random_ns + '-dns-headless-namedport-namespace'
    global_test_pod_namespace = random_ns + "-dns-test"
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
    cmd = 'dig ' \
          '_tcpport._tcp.'+name+"."+namespace+'.svc.cluster.local. +short'
    waitfor_dns_records(cmd, global_test_pod_namespace, test_pod)
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=dns-headless-namedport"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)
    cmd_result = execute_cmd(
        test_pod,
        cmd,
        global_test_pod_namespace)
    cname_record = cmd_result.rsplit()
    assert cname_record[1] == pod["items"][0]['status']['podIP']

    # test SRV record
    cmd_result = execute_cmd(
        test_pod,
        'dig SRV ' +
        '_tcpport._tcp.'+name+"."+namespace+'.svc.cluster.local. +short',
        global_test_pod_namespace)
    srv_record = cmd_result.rsplit()
    assert srv_record[2] == '80'
    assert name + '.' + namespace + '.svc.cluster.local.' in srv_record[3]

    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  name+"." + namespace +
                  ".svc.cluster.local/name.html", global_test_pod_namespace)
    assert name in cmd_result.rstrip()
    teardown_ns(namespace)


# 7
@if_test_k8s
def test_k8s_dns_pod(kube_hosts):
    name = 'dns-pod-nginx'
    global_test_pod_namespace = random_ns + "-dns-test"
    namespace = random_ns + '-dns-pod-nginx'
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
    cmd = 'dig ' + \
          pod_ip2+'.'+namespace+'.pod.cluster.local. +short'
    waitfor_dns_records(cmd, global_test_pod_namespace, test_pod)
    cmd_result = execute_cmd(
        test_pod,
        cmd,
        global_test_pod_namespace)
    assert cmd_result.rstrip() == pod_ip

    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  pod_ip2 +
                  "." +
                  namespace +
                  ".pod.cluster.local/name.html", global_test_pod_namespace)
    assert name == cmd_result.rstrip()
    teardown_ns(namespace)


# 8
@if_test_k8s
def test_k8s_dns_pod_hostname(kube_hosts):
    # hostname of the pod
    name = 'foo'
    global_test_pod_namespace = random_ns + "-dns-test"
    namespace = random_ns + '-dns-podhostname-nginx'
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
    cmd = 'dig ' \
          'foo.bar.'+namespace+'.svc.cluster.local. +short'
    waitfor_dns_records(cmd, global_test_pod_namespace, test_pod)
    cmd_result = execute_cmd(
        test_pod,
        cmd,
        global_test_pod_namespace)
    assert cmd_result.rstrip() == pod_ip

    cmd_result = execute_cmd(
        test_pod, "wget -q -O- " +
                  'foo.bar.' + namespace +
                  ".svc.cluster.local/name.html", global_test_pod_namespace)
    assert name == cmd_result.rstrip()
    teardown_ns(namespace)
