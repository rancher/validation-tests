from common_fixtures import *  # NOQA
from test_upgrade import  *
import jinja2
import os

upgrade_loops = int(os.environ.get("UPGRADE_LOOPS", "10"))

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
    assert len(nodes['items']) == kube_host_count


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
        "namespace": "stresstest-ns-1",
        "port_ext": "1"
    }
    create_stack(input_config)
    time.sleep(120)
    validate_stack(input_config)


@if_stress_testing
def test_validate_helm(kube_hosts):
    assert validate_helm()


@if_stress_testing
def test_upgrade_validate_k8s(kube_hosts):
    input_config = {
        "namespace": "stresstest-ns-1",
        "port_ext": "1"
    }
    for i in range(2, upgrade_loops):
        upgrade_k8s()
        time.sleep(60)
        validate_kubectl()
        assert check_k8s_dashboard()
        modify_stack(input_config)
        # New stack
        input_config = {
            "namespace": "stresstest-ns-"+str(i),
            "port_ext": str(i)
        }
        create_stack(input_config)
        validate_stack(input_config)
        assert validate_helm()
