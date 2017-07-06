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


def check_k8s_dashboard():
    k8s_client = kubectl_client_con["k8s_client"]
    project_id = k8s_client.list_project()[0].id
    dashboard_url = rancher_server_url() + \
        '/r/projects/' + \
        project_id + \
        '/kubernetes-dashboard:9090/'
    try:
        r = requests.get(dashboard_url)
        r.close()
        return r.ok
    except requests.ConnectionError:
        logger.info("Connection Error - " + url)
        return False


def upgrade_k8s():
    k8s_client = kubectl_client_con["k8s_client"]
    k8s_stack = k8s_client.list_stack(name="kubernetes")[0]
    docker_compose = k8s_stack.dockerCompose
    rancher_compose = k8s_stack.rancherCompose
    # Getting Environment
    k8s_catalog_url = \
        rancher_server_url() + "/v1-catalog/templates/library:infra*k8s"
    r = requests.get(k8s_catalog_url)
    template_details = json.loads(r.content)
    r.close()
    default_version_link = template_details["defaultTemplateVersionId"]

    default_k8s_catalog_url = \
        rancher_server_url() + "/v1-catalog/templates/" + default_version_link
    r = requests.get(default_k8s_catalog_url)
    template = json.loads(r.content)
    r.close()
    env = {}
    questions = template["questions"]
    for question in questions:
        label = question["variable"]
        value = question["default"]
        env[label] = value
    external_id = k8s_stack.externalId
    time.sleep(10)
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
    environment = k8s_client.list_stack(name="kubernetes")[0]
    wait_for_condition(
        k8s_client, environment,
        lambda x: x.healthState == "healthy",
        lambda x: 'State is: ' + x.healthState,
        timeout=1200)


def validate_kubectl():
    # make sure that kubectl is working
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    assert len(nodes['items']) == 4


def validate_helm():
    response = execute_helm_cmds("create validation-nginx")
    print response
    get_response = execute_helm_cmds("install validation-nginx \
        --name stresstest --namespace stresstest-ns --replace")

    if "STATUS: DEPLOYED" not in get_response:
        print "dies at install"
        return False
    time.sleep(10)

    get_response = execute_kubectl_cmds(
                    "get svc stresstest-validation-ng --namespace \
                    stresstest-ns -o json")
    print get_response
    service = json.loads(get_response)
    assert service['metadata']['name'] == "stresstest-validation-ng"

    waitfor_pods(
        selector="app=stresstest-validation-ng",
        namespace="stresstest-ns", number=1)
    get_response = execute_kubectl_cmds(
        "get pods -o json -l 'app=stresstest-validation-ng'  ")
    pod = json.loads(get_response)

    for pod in pod["items"]:
        assert pod["status"]["phase"] == "Running"
        assert pod['kind'] == "Pod"

    # Remove the release
    response = execute_helm_cmds("delete --purge stresstest")
    print response
    time.sleep(10)
    response = execute_helm_cmds("ls -q stresstest")
    assert response is ''
    return True


@if_stress_testing
def test_k8s_dashboard(kube_hosts):
    assert check_k8s_dashboard()


@if_stress_testing
def test_deploy_k8s_yaml(kube_hosts):
    input_config = {
        "namespace": "stresstest-ns",
        "port_ext": "8"
    }
    create_stack(input_config)
    validate_stack(input_config)


@if_stress_testing
def test_validate_helm(kube_hosts):
    assert validate_helm()


@if_stress_testing
def test_upgrade_validate_k8s(kube_hosts):
    input_config = {
        "namespace": "stresstest-ns",
        "port_ext": "8"
    }
    for i in range(10):
        upgrade_k8s()
        validate_kubectl()
        assert check_k8s_dashboard()
        validate_stack(input_config)
        assert validate_helm()
