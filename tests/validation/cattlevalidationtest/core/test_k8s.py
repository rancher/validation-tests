from common_fixtures import *  # NOQA

if_test_k8s = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY') or
    not os.environ.get('TEST_K8S'),
    reason='DIGITALOCEAN_KEY/TEST_K8S is not set')


@if_test_k8s
def test_k8s_env_create(
        super_client, admin_client, client, kube_hosts):
    name = "testnginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create", expected_result, file_name="create_nginx.yml")

    # Verify service is created
    get_response = execute_kubectl_cmds(
        "get service testnginx -o json")
    service = json.loads(get_response)
    assert service["spec"]["ports"][0]["protocol"] == "TCP"
    assert service["spec"]["ports"][0]["port"] == 8000
    assert service["spec"]["ports"][0]["targetPort"] == 80
    assert service["spec"]["selector"]["name"] == name

    assert service["metadata"]["labels"]["name"] == name

    # Verify rc is created
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json")
    rc = json.loads(get_response)

    assert rc["metadata"]["name"] == name
    assert rc["metadata"]["labels"]["name"] == name
    assert rc["spec"]["replicas"] == 2
    assert rc["spec"]["selector"]["name"] == "testnginx"
    container = rc["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "sangeetha/testnewhostrouting"
    assert container["name"] == name
    assert container["imagePullPolicy"] == "Always"

    time.sleep(30)
    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=testnginx -o json")
    pod = json.loads(get_response)

    assert len(pod["items"]) == 2
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == name
        assert pod["metadata"]["namespace"] == "default"
        container = pod["spec"]["containers"][0]
        assert container["image"] == "sangeetha/testnewhostrouting"
        assert container["name"] == name
        assert container["imagePullPolicy"] == "Always"
        assert pod["status"]["phase"] == "Running"


@if_test_k8s
def test_k8s_env_edit(
        super_client, admin_client, client, kube_hosts):
    name = "testeditnginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create", expected_result, file_name="edit_nginx.yml")

    get_response = execute_kubectl_cmds(
        "get rc testeditnginx -o json")
    rc = json.loads(get_response)
    replica_count = rc["spec"]["replicas"]
    assert replica_count == 2

    expected_result = ['replicationcontroller "'+name+'" replaced']
    execute_kubectl_cmds(
        "replace", expected_result, file_name="edit_update-rc-nginx.yml")
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json")
    rc = json.loads(get_response)
    replica_count = rc["spec"]["replicas"]
    assert replica_count == 3
    time.sleep(30)

    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name="+name+" -o json")
    pod = json.loads(get_response)

    assert len(pod["items"]) == 3
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == name
        assert pod["metadata"]["namespace"] == "default"
        container = pod["spec"]["containers"][0]
        assert container["image"] == "nginx"
        assert container["name"] == name
        assert container["imagePullPolicy"] == "Always"
        assert pod["status"]["phase"] == "Running"


@if_test_k8s
def test_k8s_env_delete(
        super_client, admin_client, client, kube_hosts):
    name = "testdeletenginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create", expected_result, file_name="delete_nginx.yml")
    # Verify service is created
    get_response = execute_kubectl_cmds(
        "get service "+name+" -o json")
    service = json.loads(get_response)
    assert service["metadata"]["name"] == name

    # Verify rc is created
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json")
    rc = json.loads(get_response)
    assert rc["metadata"]["name"] == name

    time.sleep(30)
    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name="+name+" -o json")
    pod = json.loads(get_response)

    assert len(pod["items"]) == 2
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == name

    # Delete service
    expected_result = ['service "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete service "+name, expected_result)

    # Verify service is deleted
    expected_error = 'Error from server: services "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get service "+name+" -o json", expected_error=expected_error)

    # Delete RC
    expected_result = ['replicationcontroller "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete rc "+name, expected_result)

    # Verify RC is deleted
    expected_error = \
        'Error from server: replicationcontrollers "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json", expected_error=expected_error)

    # Verify pods are deleted
    expected_result = ['Error from server: rc "'+name+'" not found']
    get_response = execute_kubectl_cmds(
        "get pod --selector=name="+name+" -o json")

    pod = json.loads(get_response)
    assert len(pod["items"]) == 0
