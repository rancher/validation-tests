from common_fixtures import *  # NOQA
import jinja2
import os

if_upgrade_testing = pytest.mark.skipif(
    os.environ.get("UPGRADE_TESTING") != "true",
    reason='UPGRADE_TESTING is not true')

pre_upgrade_namespace = ""
post_upgrade_namespace = ""
pre_port_ext = ""
post_port_ext = ""


@pytest.fixture(scope='session')
def get_env():
    global pre_upgrade_namespace
    global post_upgrade_namespace
    global pre_port_ext
    global post_port_ext
    pre_upgrade_namespace = os.environ.get("PRE_UPGRADE_NAMESPACE")
    post_upgrade_namespace = os.environ.get("POST_UPGRADE_NAMESPACE")
    pre_port_ext = os.environ.get("PRE_PORT_EXT")
    post_port_ext = os.environ.get("POST_PORT_EXT")


# Execute command in container
def execute_cmd(pod, cmd, namespace):
    result = execute_kubectl_cmds(
                "exec " + pod + " --namespace=" + namespace + " -- " + cmd)
    return result


def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path)
    ).get_template(filename).render(context)


def create_stack(input_config):
    namespace = input_config["namespace"]
    create_ns(namespace)

    # Create pre upgrade resources
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    node1 = nodes['items'][0]['status']['addresses'][0]['address']

    # Render the testing yaml
    input_config["external_node"] = node1
    fname = os.path.join(K8_SUBDIR, "upgrade_testing.yml.j2")
    rendered_tmpl = render(fname, input_config)

    with open(os.path.join(K8_SUBDIR, "upgrade_testing.yml"), "wt") as fout:
        fout.write(rendered_tmpl)
    fout.close()
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        file_name="upgrade_testing.yml")


def validate_stack(input_config):
    namespace = input_config["namespace"]
    lb_port = int("888" + input_config["port_ext"])
    external_port = "3000" + input_config["port_ext"]
    node_port = int("3100" + input_config["port_ext"])
    ingress_port = "8" + input_config["port_ext"]

    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    node1 = nodes['items'][0]['status']['addresses'][0]['address']
    # Verify the nginx pod is created
    waitfor_pods(selector="app=nginx-pod", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod/nginx-pod -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == "nginx-pod"
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert "husseingalal/nginx-curl" in container['image']
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"

    # Verify RC is created
    get_response = execute_kubectl_cmds(
        "get rc/nginx -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc["metadata"]["name"] == "nginx"
    assert rc["metadata"]["labels"]["name"] == "nginx"
    assert rc["spec"]["replicas"] == 2
    assert rc["spec"]["selector"]["name"] == "nginx"
    container = rc["spec"]["template"]["spec"]["containers"][0]
    assert "sangeetha/testnewhostrouting" in container["image"]
    assert container["name"] == "nginx"
    waitfor_pods(
        selector="type=rc", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod --selector=type=rc"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert len(pod["items"]) == 2
    pods_list = []
    for pod in pod["items"]:
        pods_list.append(pod["metadata"]["name"])
        assert pod["metadata"]["labels"]["name"] == "nginx"
        assert pod["metadata"]["namespace"] == namespace
        container = pod["spec"]["containers"][0]
        assert "sangeetha/testnewhostrouting" in container["image"]
        assert container["name"] == "nginx"
        assert pod["status"]["phase"] == "Running"

    # Verify that the Load Balancer service is working
    get_response = execute_kubectl_cmds(
        "get service nginx-lb -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == "nginx-lb"
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['port'] == lb_port
    assert service['spec']['ports'][0]['protocol'] == "TCP"
    time.sleep(20)
    get_response = execute_kubectl_cmds(
        "get service nginx-lb -o json --namespace=" + namespace)
    service = json.loads(get_response)
    lbip = service['status']['loadBalancer']['ingress'][0]["ip"]
    check_round_robin_access_k8s_service(pods_list, lbip, str(lb_port),
                                         path="/name.html")

    # Verify that the external service is working
    check_round_robin_access_k8s_service(pods_list, node1, str(external_port),
                                         path="/name.html")

    # Verify that the Clusterip service is working
    get_response = execute_kubectl_cmds(
        "get service nginx-clusterip -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == "nginx-clusterip"
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['port'] == 8000
    assert service['spec']['ports'][0]['protocol'] == "TCP"
    clusterip = service['spec']['clusterIP']
    clusterport = service['spec']['ports'][0]['port']
    get_response = execute_kubectl_cmds(
        "get pod --selector=app=nginx-pod -o json --namespace="+namespace)
    pods = json.loads(get_response)
    clusterurl = clusterip+":"+str(clusterport)
    nginxpod = pods['items'][0]['metadata']['name']

    cmd_result = execute_cmd(
        nginxpod,
        '''curl -s -w "%{http_code}" ''' + clusterurl + " -o /dev/null",
        namespace)
    cmd_result = cmd_result.rstrip()
    assert cmd_result == "200"

    # Verify that the nodeport service is working
    get_response = execute_kubectl_cmds(
        "get service nodeport-nginx -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == "nodeport-nginx"
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['nodePort'] == node_port
    assert service['spec']['ports'][0]['port'] == 80
    assert service['spec']['ports'][0]['protocol'] == "TCP"
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=nginx -o json --namespace="+namespace)
    pods = json.loads(get_response)
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    for node in nodes["items"]:
        node_ip = node['status']['addresses'][0]['address']
        check_round_robin_access_k8s_service(pods_list, node_ip,
                                             str(node_port), path="/name.html")

    # Check if the ingress works
    ingress_name = "ingress1"
    port = ingress_port

    # Initial set up
    lbips = wait_for_ingress_to_become_active(ingress_name, namespace, 1)

    selector1 = "k8s-app=k8test1-service"
    pod_new_names = get_pod_names_for_selector(selector1, namespace, scale=1)

    check_round_robin_access_lb_ip(pod_new_names, lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")

    check_round_robin_access_lb_ip(["nginx-ingress2"], lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/name.html")


def modify_stack(input_config):
    namespace = input_config["namespace"]
    ingress_port = "8" + input_config["port_ext"]

    # Scale the RC
    get_response = execute_kubectl_cmds(
        "scale rc nginx --replicas=3 --namespace="+namespace)

    get_response = execute_kubectl_cmds(
        "get rc/nginx -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc["metadata"]["name"] == "nginx"
    assert rc["metadata"]["labels"]["name"] == "nginx"
    assert rc["spec"]["replicas"] == 3
    assert rc["spec"]["selector"]["name"] == "nginx"
    container = rc["spec"]["template"]["spec"]["containers"][0]
    assert "sangeetha/testnewhostrouting" in container["image"]
    assert container["name"] == "nginx"
    waitfor_pods(
        selector="type=rc", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds(
        "get pod --selector=type=rc"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert len(pod["items"]) == 3
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == "nginx"
        assert pod["metadata"]["namespace"] == namespace
        container = pod["spec"]["containers"][0]
        assert "sangeetha/testnewhostrouting" in container["image"]
        assert container["name"] == "nginx"
        assert pod["status"]["phase"] == "Running"

    # Check if the ingress works
    ingress_name = "ingress1"
    port = ingress_port

    lbips = wait_for_ingress_to_become_active(ingress_name, namespace, 1)
    selector1 = "k8s-app=k8test1-service"
    rc_name1 = "k8testrc1"
    get_response = execute_kubectl_cmds(
        "scale rc "+rc_name1+" --replicas=3 --namespace="+namespace)
    waitfor_pods(selector=selector1, namespace=namespace, number=3)

    pod_new_names = get_pod_names_for_selector(selector1, namespace, scale=3)

    # Check if the ingress works with the new pods
    ingress_name = "ingress1"

    check_round_robin_access_lb_ip(pod_new_names, lbips[0], port,
                                   hostheader="foo.bar.com",
                                   path="/service3.html")


@if_upgrade_testing
def test_pre_upgrade_validate_stack(kube_hosts, get_env):
    input_config = {
        "namespace": pre_upgrade_namespace,
        "port_ext": pre_port_ext
    }
    create_stack(input_config)
    validate_stack(input_config)


@if_upgrade_testing
def test_post_upgrade_validate_stack(kube_hosts, get_env):
    # Validate pre upgrade stack after the upgrade
    input_config = {
        "namespace": pre_upgrade_namespace,
        "port_ext": pre_port_ext
    }
    validate_stack(input_config)
    modify_stack(input_config)

    # Create and validate new stack on the upgraded setup
    input_config = {
        "namespace": post_upgrade_namespace,
        "port_ext": post_port_ext
    }
    create_stack(input_config)
    validate_stack(input_config)
