from common_fixtures import *  # NOQA
import jinja2
import os

if_stress_testing = pytest.mark.skipif(
    os.environ.get("STRESS_TESTING") != "true",
    reason='STRESS_TESTING is not true')


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


def create_stack(input_config):
    namespace = input_config["namespace"]
    create_ns(namespace)

    # Create pre upgrade resources
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    node1 = nodes['items'][0]['status']['addresses'][0]['address']

    # Render the testing yaml
    input_config["external_node"] = node1
    fname = os.path.join(K8_SUBDIR, "stress_testing.yml.j2")
    rendered_tmpl = render(fname, input_config)

    with open(os.path.join(K8_SUBDIR, "stress_testing.yml"), "wt") as fout:
        fout.write(rendered_tmpl)
    fout.close()
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        file_name="stress_testing.yml")


def upgrade_k8s():
    k8s_client = kubectl_client_con["k8s_client"]
    k8s_stack = k8s_client.list_stack(name="kubernetes")[0]
    docker_compose = k8s_stack.dockerCompose
    rancher_compose = k8s_stack.rancherCompose
    env = k8s_stack.environment
    external_id = k8s_stack.externalId

    upgraded_k8s_stack = k8s_stack.upgrade(
                            name="kubernetes",
                            dockerCompose=docker_compose,
                            rancherCompose=rancher_compose,
                            environment=env,
                            externalId=external_id)
    upgraded_k8s_stack = k8s_client.wait_success(
                            upgraded_k8s_stack,
                            timeout=300)
    upgraded_k8s_stack.finishupgrade()


def validate_kubectl_and_dashboard():
    # make sure that kubectl is working
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    assert len(nodes['items']) == 3
    # make sure that dashboard is working


def validate_app_and_helm():
    # Validate app
    input_config = {
        "namespace": "stresstest-ns",
        "port_ext": "8"
    }
    validate_stack(input_config)
    # Validate Helm


@if_stress_testing
def test_k8s_dashboard(kube_hosts):
    assert True


@if_stress_testing
def test_deploy_k8s_yaml(kube_hosts):
    input_config = {
        "namespace": "stresstest-ns",
        "port_ext": "8"
    }
    create_stack(input_config)
    validate_stack(input_config)


@if_stress_testing
def test_upgrade_validate_k8s(kube_hosts):
    for i in range(10):
        upgrade_k8s()
        validate_kubectl_and_dashboard()
        validate_app_and_helm()
