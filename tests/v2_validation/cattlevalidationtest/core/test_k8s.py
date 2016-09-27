from common_fixtures import *  # NOQA
from urllib2 import urlopen
import websocket as ws
import base64
import os

quay_creds = {}
quay_creds["email"] = os.environ.get('QUAY_EMAIL')
quay_creds["username"] = os.environ.get('QUAY_USERNAME')
quay_creds["password"] = os.environ.get('QUAY_PASSWORD')
quay_creds["image"] = os.environ.get('QUAY_IMAGE')
quay_creds["serverAddress"] = "quay.io"
quay_creds["name"] = "quay"


registry_list = {}

if_test_k8s = pytest.mark.skipif(
    not os.environ.get('TEST_K8S'),
    reason='TEST_K8S is not set')

if_test_privatereg = pytest.mark.skipif(
    not os.environ.get('TEST_K8S') or
    not os.environ.get('QUAY_EMAIL') or
    not os.environ.get('QUAY_USERNAME') or
    not os.environ.get('QUAY_IMAGE'),
    reason='PRIVATEREG_CREDENTIALS/TEST_K8S not set')

if_test_kubectl_1_2_skip = pytest.mark.skipif(
    kubectl_version.startswith("v1.2"),
    reason='Kubernetes version is v1.2.x')


def create_registry(client, registry_creds):

    registry = client.create_registry(
        serverAddress=registry_creds["serverAddress"],
        name=registry_creds["name"])
    registry = client.wait_success(registry)

    reg_cred = client.create_registry_credential(
        registryId=registry.id,
        email=registry_creds["email"],
        publicValue=registry_creds["username"],
        secretValue=registry_creds["password"])
    reg_cred = client.wait_success(reg_cred)

    return reg_cred


def remove_registry(client, admin_client, registry_creds, reg_cred):

    registry_list[registry_creds["name"]] = reg_cred

    for reg_cred in registry_list.values():
        reg_cred = client.wait_success(reg_cred.deactivate())
        reg_cred = client.delete(reg_cred)
        reg_cred = client.wait_success(reg_cred)
        assert reg_cred.state == 'removed'
        registry = admin_client.by_id('registry', reg_cred.registryId)
        registry = client.wait_success(registry.deactivate())
        assert registry.state == 'inactive'
        registry = client.delete(registry)
        registry = client.wait_success(registry)
        assert registry.state == 'removed'


# Execute command in container
def execute_cmd(container, cmd):
    ex = container.execute(
        attachStdin=True,
        attachStdout=True,
        command=cmd,
        tty=True)
    conn = ws.create_connection(ex.url + '?token=' + ex.token, timeout=10)

    # Python is weird about closures
    closure_wrapper = {
        'result': ''
    }

    msg = conn.recv()
    print msg
    closure_wrapper['result'] += base64.b64decode(msg)
    return closure_wrapper['result'].rstrip()


# Get containers of Pod
def get_pod_container_list(admin_client, pod, namespace='default'):
    container = []
    all_containers = admin_client.list_container()
    for cont in all_containers:
        if bool(cont.labels):
            if "io.kubernetes.pod.name" in cont.labels.keys():
                if (cont['labels']['io.kubernetes.pod.name'] == pod and
                    cont['state'] == 'running' and
                    cont.imageUuid != 'docker:gcr.io/'
                    'google_containers/pause:2.0' and
                    cont['labels']
                        ['io.kubernetes.pod.namespace'] == namespace):
                    container.append(cont)
    return container


@if_test_k8s
def test_k8s_env_create(
        admin_client, client, kube_hosts):
    namespace = "create-namespace"
    create_ns(namespace)
    name = "testnginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="create_nginx.yml")

    # Verify service is created
    get_response = execute_kubectl_cmds(
        "get service testnginx -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service["spec"]["ports"][0]["protocol"] == "TCP"
    assert service["spec"]["ports"][0]["port"] == 8000
    assert service["spec"]["ports"][0]["targetPort"] == 80
    assert service["spec"]["selector"]["name"] == name

    assert service["metadata"]["labels"]["name"] == name

    # Verify rc is created
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)

    assert rc["metadata"]["name"] == name
    assert rc["metadata"]["labels"]["name"] == name
    assert rc["spec"]["replicas"] == 2
    assert rc["spec"]["selector"]["name"] == "testnginx"
    container = rc["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "sangeetha/testnewhostrouting"
    assert container["name"] == name
    assert container["imagePullPolicy"] == "Always"

    waitfor_pods(
        selector="name=testnginx", namespace=namespace, number=2)
    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=testnginx"
        " -o json --namespace="+namespace)
    pod = json.loads(get_response)

    assert len(pod["items"]) == 2
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == name
        assert pod["metadata"]["namespace"] == namespace
        container = pod["spec"]["containers"][0]
        assert container["image"] == "sangeetha/testnewhostrouting"
        assert container["name"] == name
        assert container["imagePullPolicy"] == "Always"
        assert pod["status"]["phase"] == "Running"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_edit(
        admin_client, client, kube_hosts):
    namespace = "edit-namespace"
    create_ns(namespace)
    name = "testeditnginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="edit_nginx.yml")

    get_response = execute_kubectl_cmds(
        "get rc testeditnginx -o json --namespace="+namespace)
    rc = json.loads(get_response)
    replica_count = rc["spec"]["replicas"]
    assert replica_count == 2

    expected_result = ['replicationcontroller "'+name+'" replaced']
    execute_kubectl_cmds(
        "replace --namespace="+namespace,
        expected_result, file_name="edit_update-rc-nginx.yml")
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    replica_count = rc["spec"]["replicas"]
    assert replica_count == 3
    waitfor_pods(
        selector="name="+name, namespace=namespace, number=3)

    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name="+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)

    assert len(pod["items"]) == 3
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == name
        assert pod["metadata"]["namespace"] == namespace
        container = pod["spec"]["containers"][0]
        assert container["image"] == "nginx"
        assert container["name"] == name
        assert container["imagePullPolicy"] == "Always"
        assert pod["status"]["phase"] == "Running"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_delete(
        admin_client, client, kube_hosts):
    namespace = "delete-namespace"
    create_ns(namespace)
    name = "testdeletenginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="delete_nginx.yml")
    # Verify service is created
    get_response = execute_kubectl_cmds(
        "get service "+name+" -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service["metadata"]["name"] == name

    # Verify rc is created
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc["metadata"]["name"] == name

    waitfor_pods(selector="name="+name,
                 namespace=namespace, number=2)
    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name="+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)

    assert len(pod["items"]) == 2
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == name

    # Delete service
    expected_result = ['service "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete service --namespace="+namespace+" "+name, expected_result)

    # Verify service is deleted
    expected_error = 'Error from server: services "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get service "+name+" -o json --namespace="+namespace,
        expected_error=expected_error)

    # Delete RC
    expected_result = ['replicationcontroller "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete rc "+name+" --namespace="+namespace, expected_result)

    # Verify RC is deleted
    expected_error = \
        'Error from server: replicationcontrollers "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace,
        expected_error=expected_error)

    # Verify pods are deleted
    expected_result = ['Error from server: rc "'+name+'" not found']
    get_response = execute_kubectl_cmds(
        "get pod --selector=name="+name+" -o json --namespace="+namespace)

    pod = json.loads(get_response)
    assert len(pod["items"]) == 0
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_secret(
        admin_client, client, kube_hosts):
    namespace = "secret-namespace"
    create_ns(namespace)
    name = "testsecret"
    expected_result = ['secret "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="secret.yml")
    # Verify secret is created
    get_response = execute_kubectl_cmds(
        "get secret testsecret -o json --namespace="+namespace)
    secret = json.loads(get_response)
    assert secret["type"] == "Opaque"
    assert secret["metadata"]["name"] == name
    assert secret["data"]["username"] == "YWRtaW4K"
    assert secret["data"]["password"] == "MWYyZDFlMmU2N2RmCg=="
    # Delete secret
    expected_result = ['secret "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete --namespace="+namespace,
        expected_result, file_name="secret.yml")
    # Verify Secret is deleted
    expected_error = \
        'Error from server: secrets "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get secret "+name+" -o json --namespace="+namespace,
        expected_error=expected_error)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_namespace(
        admin_client, client, kube_hosts):
    namespace = "testnamespace"
    create_ns(namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_rollingupdates(
        admin_client, client, kube_hosts):
    namespace = "rollingupdates-namespace"
    create_ns(namespace)
    name = "testru"
    expected_result = ['replicationcontroller "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="rollingupdates_nginx.yml")

    # Verify rc is created
    get_response = execute_kubectl_cmds(
        "get rc testru -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc["spec"]["replicas"] == 1
    assert rc["metadata"]["name"] == name
    container = rc["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "nginx:1.7.9"
    assert container["name"] == "nginx"

    waitfor_pods(selector="name=nginx", namespace=namespace)
    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=nginx -o json --namespace="+namespace)
    pod = json.loads(get_response)

    assert len(pod["items"]) == 1
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == "nginx"
        assert pod["metadata"]["namespace"] == namespace
        container = pod["spec"]["containers"][0]
        assert container["image"] == "nginx:1.7.9"
        assert container["name"] == "nginx"
        assert pod["status"]["phase"] == "Running"

    # Run the rollingupdates
    command = ("rolling-update testru"
               " testruv2 --image=nginx:1.9.1 --namespace="+namespace)
    execute_kubectl_cmds(command)

    waitfor_pods(selector="name=nginx", namespace=namespace)
    # Verify new pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=nginx -o json --namespace="+namespace)
    pod = json.loads(get_response)

    assert len(pod["items"]) == 1
    for pod in pod["items"]:
        assert pod["metadata"]["labels"]["name"] == "nginx"
        assert pod["metadata"]["namespace"] == namespace
        container = pod["spec"]["containers"][0]
        assert container["image"] == "nginx:1.9.1"
        assert container["name"] == "nginx"
        assert pod["status"]["phase"] == "Running"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_configmaps(
        admin_client, client, kube_hosts):
    namespace = "configmaps-namespace"
    create_ns(namespace)
    name = "testconfigmap"
    expected_result = ['configmap "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="configmap.yml")

    # Verify namespace is created
    get_response = execute_kubectl_cmds(
        "get configmaps testconfigmap -o json --namespace="+namespace)
    secret = json.loads(get_response)
    assert secret["metadata"]["name"] == name
    assert secret["data"]["test.name"] == "configmap"
    assert secret["data"]["test.type"] == "resources"

    # Delete namespace
    expected_result = ['configmap "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete configmap testconfigmap --namespace="+namespace,
        expected_result)

    # Verify namespace is deleted
    expected_error = \
        'Error from server: configmaps "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get configmap "+name+" -o json --namespace="+namespace,
        expected_error=expected_error)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_resourceQuota(
        admin_client, client, kube_hosts):
    name = "quota"
    namespace = "quota-example"
    create_ns(namespace)
    # Create resource quota object
    expected_result = ['resourcequota "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="quota.json")
    # Create rc to test the quota
    execute_kubectl_cmds(
        "create", file_name="quota_nginx.yml")
    # Verify that creation failed
    describe_response = execute_kubectl_cmds(
        "describe rc testnginx --namespace="+namespace)
    failed_str = 'Error creating: pods "testnginx-" '
    'is forbidden: Exceeded quota: quota'
    assert failed_str in describe_response
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_deployments(
        admin_client, client, kube_hosts):
    namespace = 'deployments-namespace'
    create_ns(namespace)
    name = "nginx-deployment"
    # Create deployment
    expected_result = ['deployment "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="nginx-deployment.yml")
    waitfor_pods(
        selector="app=nginx", namespace=namespace, number=3)
    # Verify new pods are created
    get_response = execute_kubectl_cmds(
        "get deployment "+name+" -o json --namespace="+namespace)
    deployment = json.loads(get_response)
    assert deployment["kind"] == "Deployment"
    assert deployment["spec"]["replicas"] == 3
    assert deployment["metadata"]["name"] == name
    assert deployment["spec"]["strategy"]["type"] == "RollingUpdate"
    assert deployment["status"]["replicas"] == 3
    assert deployment["status"]["availableReplicas"] == 3
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_deployments_rollback(
        admin_client, client, kube_hosts):
    namespace = 'deploymentsrollback-namespace'
    create_ns(namespace)
    name = "nginx-deployment"
    # Create deployment
    expected_result = ['deployment "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="nginx-deployment.yml")
    waitfor_pods(
        selector="app=nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds(
        "get deployment "+name+" -o json --namespace="+namespace)
    deployment = json.loads(get_response)
    assert deployment["kind"] == "Deployment"
    assert deployment["spec"]["replicas"] == 3
    assert deployment["metadata"]["name"] == name
    assert deployment["spec"]["strategy"]["type"] == "RollingUpdate"
    assert deployment["status"]["replicas"] == 3
    assert deployment["status"]["availableReplicas"] == 3
    containers = deployment["spec"]["template"]["spec"]["containers"]
    assert containers[0]["image"] == "nginx:1.7.9"
    # Update deployment
    expected_result = ['deployment "'+name+'" configured']
    execute_kubectl_cmds(
        "apply --namespace="+namespace,
        expected_result, file_name="nginx-deploymentv2.yml")
    waitfor_pods(
        selector="app=nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds(
        "get deployment "+name+" -o json --namespace="+namespace)
    deployment = json.loads(get_response)
    assert deployment["kind"] == "Deployment"
    assert deployment["spec"]["replicas"] == 3
    assert deployment["metadata"]["name"] == name
    assert deployment["spec"]["strategy"]["type"] == "RollingUpdate"
    assert deployment["status"]["availableReplicas"] == 3
    containers = deployment["spec"]["template"]["spec"]["containers"]
    assert containers[0]["image"] == "nginx:1.9.1"
    # Rollback deployment
    expected_result = ['deployment "nginx-deployment" rolled back']
    execute_kubectl_cmds(
        "rollout undo --namespace="+namespace+" deployment/"+name,
        expected_result)
    waitfor_pods(selector="app=nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds(
        "get deployment "+name+" -o json --namespace="+namespace)
    deployment = json.loads(get_response)
    assert deployment["kind"] == "Deployment"
    assert deployment["spec"]["replicas"] == 3
    assert deployment["metadata"]["name"] == name
    assert deployment["spec"]["strategy"]["type"] == "RollingUpdate"
    assert deployment["status"]["availableReplicas"] == 3
    containers = deployment["spec"]["template"]["spec"]["containers"]
    assert containers[0]["image"] == "nginx:1.7.9"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_jobs(
        admin_client, client, kube_hosts):
    namespace = 'jobs-namespace'
    create_ns(namespace)
    name = "pitest"
    # Create deployment
    expected_result = ['job "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="job.yml")
    waitfor_pods(
        selector="job-name=pitest", namespace=namespace,
        state="Succeeded", number=1)
    get_response = execute_kubectl_cmds(
        "get jobs "+name+" -o json --namespace="+namespace)
    deployment = json.loads(get_response)
    assert deployment["kind"] == "Job"
    assert deployment["metadata"]["name"] == name
    assert deployment["status"]["conditions"][0]["type"] == "Complete"
    assert deployment["status"]["conditions"][0]["status"] == "True"
    assert deployment["status"]["succeeded"] == 1
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_scale(
        admin_client, client, kube_hosts):
    namespace = 'scale-namespace'
    create_ns(namespace)
    name = "scale-nginx"
    # Create rc
    expected_result = ['replicationcontroller "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace,
        expected_result, file_name="scale-rc.yml")
    waitfor_pods(
        selector="app=scalable-nginx", namespace=namespace, number=2)
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc["kind"] == "ReplicationController"
    assert rc["metadata"]["name"] == name
    assert rc["spec"]["replicas"] == rc["status"]["replicas"]
    assert rc["status"]["replicas"] == 2
    container = rc["spec"]["template"]["spec"]["containers"][0]
    assert container["name"] == "nginx"
    # Scale rc
    expected_result = ['replicationcontroller "'+name+'" scaled']
    execute_kubectl_cmds(
        "scale rc "+name+" --replicas=3 --namespace="+namespace,
        expected_result)
    waitfor_pods(
        selector="app=scalable-nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc["kind"] == "ReplicationController"
    assert rc["metadata"]["name"] == name
    assert rc["spec"]["replicas"] == rc["status"]["replicas"]
    assert rc["status"]["replicas"] == 3
    assert rc["status"]["observedGeneration"] == 2
    container = rc["spec"]["template"]["spec"]["containers"][0]
    assert container["name"] == "nginx"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_daemonsets(
        admin_client, client, kube_hosts):
    namespace = 'daemonset-namespace'
    create_ns(namespace)
    name = "daemonset"
    # Create daemonset
    expected_result = ['daemonset "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="daemonset.yml")
    waitfor_pods(selector="app=daemonset-nginx", namespace=namespace, number=2)
    get_response = execute_kubectl_cmds(
        "get pods --selector=app=daemonset-nginx"
        " -o json --namespace="+namespace)
    pods = json.loads(get_response)
    nodes_of_pods = set()
    for pod in pods['items']:
        assert pod['status']['phase'] == "Running"
        assert pod['status']['containerStatuses'][0]['name'] == "nginx"
        node = pod['spec']['nodeName']
        nodes_of_pods.add(node)
    # Get nodes
    nodes_in_cluster = set()
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    for node in nodes['items']:
        nodes_in_cluster.add(node['metadata']['name'])
    assert nodes_in_cluster == nodes_of_pods
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_replicasets(
        admin_client, client, kube_hosts):
    namespace = 'replicaset-namespace'
    create_ns(namespace)
    name = "rs"
    # Create daemonset
    expected_result = ['replicaset "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="replicaset.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds(
        "get rs "+name+" -o json --namespace="+namespace)
    rs = json.loads(get_response)
    assert rs['metadata']['name'] == name
    assert rs['kind'] == "ReplicaSet"
    assert rs['status']['replicas'] == rs['spec']['replicas']
    teardown_ns(namespace)


# Pod Attributes
@if_test_k8s
def test_k8s_env_create_pod(
        admin_client, client, kube_hosts):
    namespace = 'pod-create-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create daemonset
    expected_result = ['pod "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="pod-nginx.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_create_priv_pod(
        admin_client, client, kube_hosts):
    namespace = 'pod-priv-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create daemonset
    expected_result = ['pod "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="pod-priv-nginx.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    assert pod['spec']['containers'][0]['securityContext']['privileged']
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_delete_pod(
        admin_client, client, kube_hosts):
    namespace = 'pod-delete-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create daemonset
    expected_result = ['pod "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="pod-nginx.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    # Delete pod
    expected_result = ['pod "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete pods "+name+" --namespace="+namespace, expected_result)
    # Verify Pod is deleted
    expected_error = \
        'Error from server: pods "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get pods "+name+" -o json --namespace="+namespace,
        expected_error=expected_error)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_edit_pod(
        admin_client, client, kube_hosts):
    namespace = 'pod-edit-namespace'
    create_ns(namespace)
    oldname = "nginx"
    name = "nginxv2"
    # Create daemonset
    expected_result = ['pod "'+oldname+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="pod-nginx.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+oldname+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == oldname
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['name'] == "nginx"
    assert container['ready']
    # Edit pod
    expected_result = ['pod "'+name+'" replaced']
    execute_kubectl_cmds(
        "replace --force --namespace="+namespace,
        expected_result, file_name="pod-replace-nginx.yml")
    waitfor_pods(selector="app=nginxv2", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx:1.9.1"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginxv2"
    teardown_ns(namespace)


# Podspecs
@if_test_k8s
def test_k8s_env_podspec_volume(
        admin_client, client, kube_hosts):
    namespace = 'volume-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create pod with service
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="podspec-volume.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    volume = pod['spec']['containers'][0]['volumeMounts'][0]
    assert volume['name'] == pod['spec']['volumes'][0]['name']
    assert volume['mountPath'] == "/usr/share/nginx/html"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "husseingalal/podspec-vol"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    # Testing the volumes
    nodeIP = pod['status']['hostIP']
    nodePort = "32445"
    page = urlopen("http://"+nodeIP+":"+nodePort)
    output = page.read()
    assert output == "Volume spec is working Pod\n"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_restartPolicy(
        admin_client, client, kube_hosts):
    namespace = 'restartpolicy-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create pod with service
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="pod-nginx-rp.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    # stop containers in the pod
    containers = get_pod_container_list(
        admin_client, name, namespace=namespace)
    for c in containers:
        admin_client.wait_success(c.stop())
    time.sleep(5)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Succeeded"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert not container['ready']
    assert container['name'] == "nginx"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_podspec_activeDeadlineSeconds(
        admin_client, client, kube_hosts):
    namespace = 'ads-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create pod with active deadline seconds
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="pod-nginx-ads.yml")
    waitfor_pods(
        selector="app=nginx", namespace=namespace, number=1, state="Failed")
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Failed"
    assert pod['status']['reason'] == "DeadlineExceeded"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_podspec_terminationGracePeriodSeconds(
        admin_client, client, kube_hosts):
    namespace = 'tgps-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create pod with termination grace period
    expected_result = ['pod "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="pod-nginx-tgp.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['spec']['terminationGracePeriodSeconds'] == 100
    assert pod['status']['phase'] == "Running"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_podspec_nodeSelector(
        admin_client, client, kube_hosts):
    namespace = 'nodeselector-namespace'
    create_ns(namespace)
    name = "nginx"
    # Get all nodes
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    last_node = nodes['items'][len(nodes['items'])-1]['metadata']['name']
    # Add label on the last node
    expected_result = ['node "'+last_node+'" labeled']
    execute_kubectl_cmds(
        "label nodes "+last_node+" role=testnode", expected_result)
    # Create pod with nodeselector
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="pod-nginx-nodeSelector.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['spec']['nodeName'] == last_node
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    # Remove label from node
    expected_result = ['node "'+last_node+'" labeled']
    execute_kubectl_cmds(
        "label nodes "+last_node+" role-", expected_result)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_podspec_nodeName(
        admin_client, client, kube_hosts):
    namespace = 'nodename-namespace'
    create_ns(namespace)
    name = "nginx"
    # Get all nodes
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    last_node = nodes['items'][len(nodes['items'])-1]['metadata']['name']
    # Change nodename in yml file
    fname = os.path.join(K8_SUBDIR, "pod-nginx-nodeName.yml")
    with open(os.path.join(K8_SUBDIR,
                           "pod-nginx-nodeName-2.yml"), "wt") as fout:
        with open(fname, "rt") as fin:
            for line in fin:
                fout.write(line.replace('placeholder', last_node))
    fin.close()
    fout.close()
    # Create pod with nodeselector
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="pod-nginx-nodeName-2.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['spec']['nodeName'] == last_node
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    # Remove the updated file
    os.remove(os.path.join(K8_SUBDIR, "pod-nginx-nodeName-2.yml"))
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_podspec_hostPID(
        admin_client, client, kube_hosts):
    namespace = 'hostpid-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create pod with hostpid
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="pod-nginx-hostpid.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['spec']['hostPID']
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    # check for PID
    cont = get_pod_container_list(admin_client, name, namespace=namespace)
    cmd_result = execute_cmd(cont[0], ['ps', '-p', '1', '-o', 'comm='])
    assert cmd_result != 'nginx'
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_podspec_hostIPC(
        admin_client, client, kube_hosts):
    namespace = 'hostipc-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create pod with hostpid
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="pod-nginx-hostipc.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['spec']['hostIPC']
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "nginx"
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "nginx"
    teardown_ns(namespace)


# ReplicationController Attributes/Specs
@if_test_k8s
def test_k8s_env_rc_create(
        admin_client, client, kube_hosts):
    namespace = 'rc-create-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create rc
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="rc-nginx.yml")
    waitfor_pods(selector="name=nginx", namespace=namespace, number=2)
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc['metadata']['name'] == name
    assert rc['status']['replicas'] == rc['spec']['replicas']
    assert rc['kind'] == "ReplicationController"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_rc_delete(
        admin_client, client, kube_hosts):
    namespace = 'rc-delete-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create rc
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="rc-nginx.yml")
    waitfor_pods(selector="name=nginx", namespace=namespace, number=2)
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc['metadata']['name'] == name
    assert rc['status']['replicas'] == rc['spec']['replicas']
    assert rc['kind'] == "ReplicationController"
    # Delete rc
    expected_result = ['replicationcontroller "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete rc "+name+" --namespace="+namespace, expected_result)
    # Verify rc is deleted
    expected_error = \
        'Error from server: replicationcontrollers "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace,
        expected_error=expected_error)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_rc_edit(
        admin_client, client, kube_hosts):
    namespace = 'rc-edit-namespace'
    create_ns(namespace)
    name = "nginx"
    # Create rc
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="rc-nginx.yml")
    waitfor_pods(
        selector="name=nginx", namespace=namespace, number=2)
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc['metadata']['name'] == name
    assert rc['status']['replicas'] == rc['spec']['replicas']
    assert rc['kind'] == "ReplicationController"
    # Edit pod
    newname = 'nginxv2'
    expected_result = ['replicationcontroller "'+newname+'" replaced']
    execute_kubectl_cmds(
        "replace --force --namespace="+namespace,
        expected_result, file_name="rc-replace-nginx.yml")
    waitfor_pods(selector="name=nginxv2", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds(
        "get rc "+newname+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc['metadata']['name'] == newname
    assert rc['status']['replicas'] == rc['spec']['replicas']
    assert rc['kind'] == "ReplicationController"
    teardown_ns(namespace)


# Service Attributes/Specs
@if_test_k8s
def test_k8s_env_service_lb(
        admin_client, client, kube_hosts):
    namespace = 'service-namespace-lb'
    create_ns(namespace)
    lbname = "lbnginx"
    # Create rc and services
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="service-nginx-lb.yml")
    waitfor_pods(selector="name=nginx", namespace=namespace, number=1)
    # Verify that all services created
    get_response = execute_kubectl_cmds(
        "get service "+lbname+" -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == lbname
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['port'] == 8888
    assert service['spec']['ports'][0]['protocol'] == "TCP"

    # Check for loadbalancer service
    if kubectl_version.startswith("v1.2"):
        services = admin_client.list_service()
        for s in services:
            if 'lb-' in s.name:
                lbservice = s
        containers = get_service_container_list(admin_client, lbservice)
        assert len(containers) == 1
        lb_containers = admin_client.list_container(
            externalId=containers[0].externalId,
            include="hosts",
            removed_null=True)
        assert len(lb_containers) == 1
        lbip = lb_containers[0].hosts[0].ipAddresses()[0].address
    else:
        time.sleep(20)
        get_response = execute_kubectl_cmds(
            "get service " + lbname + " -o json --namespace=" + namespace)
        service = json.loads(get_response)
        lbip = service['status']['loadBalancer']['ingress'][0]["ip"]
    response = urlopen("http://"+lbip+":8888")
    assert response.code == 200
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_service_clusterip(
        admin_client, client, kube_hosts):
    namespace = 'service-namespace-clusterip'
    create_ns(namespace)
    clusteripname = "clusterip-nginx"
    # Create rc and services
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="service-nginx-clusterip.yml")
    waitfor_pods(selector="name=nginx", namespace=namespace, number=1)

    get_response = execute_kubectl_cmds(
        "get service "+clusteripname+" -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == clusteripname
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['port'] == 8000
    assert service['spec']['ports'][0]['protocol'] == "TCP"
    clusterip = service['spec']['clusterIP']
    clusterport = service['spec']['ports'][0]['port']

    # Check for cluster IP
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=nginx -o json --namespace="+namespace)
    pods = json.loads(get_response)
    clusterurl = clusterip+":"+str(clusterport)
    nginxpod = pods['items'][0]['metadata']['name']
    if kubectl_version.startswith("v1.2"):
        nginxcont = get_pod_container_list(
            admin_client, nginxpod, namespace=namespace)[0]
    else:
        nginxcont = get_pod_container_list(
            admin_client, nginxpod, namespace=namespace)[1]
    cmd_result = execute_cmd(
        nginxcont, ['curl', '-s', '-w', '%{http_code}\\n',
                    clusterurl, '-o', '/dev/null'])
    cmd_result = cmd_result.rstrip("\r\n")
    assert cmd_result == "200"
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_service_externalip(
        admin_client, client, kube_hosts):
    namespace = 'service-namespace-externalip'
    create_ns(namespace)
    # Get all nodes ips
    get_response = execute_kubectl_cmds("get nodes -o json")
    nodes = json.loads(get_response)
    node1 = nodes['items'][0]['status']['addresses'][0]['address']
    node2 = nodes['items'][1]['status']['addresses'][0]['address']
    # Change nodes ips in yml file
    fname = os.path.join(K8_SUBDIR, "service-nginx-externalip.yml")
    with open(os.path.join(K8_SUBDIR,
                           "service-nginx-externalip-1.yml"), "wt") as fout:
        with open(fname, "rt") as fin:
            for line in fin:
                fout.write(line.replace('placeholder-1', node1))
    fin.close()
    fout.close()
    fname = os.path.join(K8_SUBDIR,
                         "service-nginx-externalip-1.yml")
    with open(os.path.join(K8_SUBDIR,
                           "service-nginx-externalip-2.yml"), "wt") as fout:
        with open(fname, "rt") as fin:
            for line in fin:
                fout.write(line.replace('placeholder-2', node2))
    fin.close()
    fout.close()
    # Create rc and services
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="service-nginx-externalip-2.yml")
    waitfor_pods(selector="name=nginx", namespace=namespace, number=1)
    # Check for external IP
    response = urlopen("http://"+node1+":30003")
    assert response.code == 200
    response = urlopen("http://"+node2+":30003")
    assert response.code == 200
    os.remove(os.path.join(K8_SUBDIR, "service-nginx-externalip-1.yml"))
    os.remove(os.path.join(K8_SUBDIR, "service-nginx-externalip-2.yml"))
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_service_nodeport(
        admin_client, client, kube_hosts):
    namespace = 'service-namespace-nodeport'
    create_ns(namespace)
    nodeportname = "nodeport-nginx"
    # Create rc and services
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="service-nginx-nodeport.yml")
    waitfor_pods(selector="name=nginx", namespace=namespace, number=1)

    get_response = execute_kubectl_cmds(
        "get service "+nodeportname+" -o json --namespace="+namespace)
    service = json.loads(get_response)
    assert service['metadata']['name'] == nodeportname
    assert service['kind'] == "Service"
    assert service['spec']['ports'][0]['nodePort'] == 30000
    assert service['spec']['ports'][0]['port'] == 80
    assert service['spec']['ports'][0]['protocol'] == "TCP"

    # Check for nodeport IP
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=nginx -o json --namespace="+namespace)
    pods = json.loads(get_response)
    nodeportip = pods['items'][0]['status']['hostIP']
    response = urlopen("http://"+nodeportip+":30000")
    assert response.code == 200
    teardown_ns(namespace)


# Failed tests
# hostnetwork #4345
@if_test_k8s
def test_k8s_env_podspec_hostnetwork(
        admin_client, client, kube_hosts):
    namespace = 'hostnetwork-namespace'
    create_ns(namespace)
    name = "nginx"
    # create pod with hostnetwork
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="pod-nginx-hostnet.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == "husseingalal/podspec-hostnet"
    assert container['ready']
    assert container['name'] == "nginx"
    teardown_ns(namespace)


# dashboard #4452
@if_test_k8s
def test_k8s_env_dashboard(
        admin_client, client, kube_hosts):
    namespace = 'dashboard-namespace'
    name = 'kubernetes-dashboard'
    create_ns(namespace)
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="dashboard.yml")
    waitfor_pods(selector="app=kubernetes-dashboard",
                 namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc['metadata']['name'] == name
    assert rc['status']['replicas'] == rc['spec']['replicas']
    assert rc['kind'] == "ReplicationController"
    get_response = execute_kubectl_cmds(
        "get pod --selector=app=kubernetes-dashboard"
        " -o json --namespace="+namespace)
    pods = json.loads(get_response)
    pod = pods['items'][0]
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['ready']
    assert container['restartCount'] == 0
    # Check for nodeport IP
    get_response = execute_kubectl_cmds(
        "get pod --selector=app=kubernetes-dashboard"
        " -o json --namespace="+namespace)
    pods = json.loads(get_response)
    nodeportip = pods['items'][0]['status']['hostIP']
    response = urlopen("http://"+nodeportip+":30803")
    assert response.code == 200
    teardown_ns(namespace)


# heapster #4451
@if_test_k8s
def test_k8s_env_heapster(
        admin_client, client, kube_hosts):
    namespace = 'heapster-namespace'
    name = 'heapster'
    create_ns(namespace)
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="heapster.yml")
    waitfor_pods(selector="k8s-app=heapster", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    assert rc['metadata']['name'] == name
    assert rc['status']['replicas'] == rc['spec']['replicas']
    assert rc['kind'] == "ReplicationController"
    get_response = execute_kubectl_cmds(
        "get pod --selector=k8s-app=heapster -o json --namespace="+namespace)
    pods = json.loads(get_response)
    pod = pods['items'][0]
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    container = pod['status']['containerStatuses'][0]
    assert container['ready']
    # Check for nodeport IP for grafana and influx
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=influxGrafana -o json --namespace="+namespace)
    pods = json.loads(get_response)
    nodeportip = pods['items'][0]['status']['hostIP']
    response = urlopen("http://"+nodeportip+":30804")
    assert response.code == 200
    response = urlopen("http://"+nodeportip+":30805")
    assert response.code == 200
    teardown_ns(namespace)


# ServiceAccounts #4548
@if_test_k8s
def test_k8s_env_serviceaccount(
        admin_client, client, kube_hosts):
    name = 'build-robot'
    namespace = 'serviceaccount-namespace'
    create_ns(namespace)
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="serviceaccount.yml")
    get_response = execute_kubectl_cmds(
        "get serviceaccount "+name+" -o json --namespace="+namespace)
    sa = json.loads(get_response)
    assert sa['metadata']['name'] == name
    assert sa['kind'] == "ServiceAccount"
    assert 'build-robot' in sa['secrets'][0]['name']
    teardown_ns(namespace)


# exec/logs
@if_test_kubectl_1_2_skip
@if_test_k8s
def test_k8s_env_logs(
        admin_client, client, kube_hosts):
    name = 'hello-nginx'
    namespace = 'logs-namespace'
    create_ns(namespace)
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="hello-nginx.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['status']['phase'] == "Running"
    expected_result = ['Logs Worked!']
    execute_kubectl_cmds(
        "logs "+name+" --namespace="+namespace, expected_result)
    teardown_ns(namespace)


@if_test_kubectl_1_2_skip
@if_test_k8s
def test_k8s_env_exec(
        admin_client, client, kube_hosts):
    name = 'hello-nginx'
    namespace = 'exec-namespace'
    create_ns(namespace)
    execute_kubectl_cmds("create --namespace="+namespace,
                         file_name="hello-nginx.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['status']['phase'] == "Running"
    expected_result = ['Exec Worked!']
    execute_kubectl_cmds(
        "exec "+name+" --namespace=" + namespace + " cat /tmp/exec",
        expected_result)
    teardown_ns(namespace)


@if_test_privatereg
def test_k8s_env_create_pod_with_private_registry_image(
        admin_client, client, kube_hosts):

    quay_image = quay_creds["image"]
    # Create namespace
    namespace = 'privateregns'
    create_ns(namespace)
    name = "privateregpod"

    # Create registry
    reg_cred = create_registry(client, quay_creds)
    registry_list[quay_creds["name"]] = reg_cred

    # Create pod with the image in private registry
    expected_result = ['pod "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result,
                         file_name="pod-private-registry.yml")
    waitfor_pods(selector="app=privatereg", namespace=namespace, number=1)
    get_response = execute_kubectl_cmds(
        "get pod "+name+" -o json --namespace="+namespace)
    pod = json.loads(get_response)
    assert pod['metadata']['name'] == name
    assert pod['kind'] == "Pod"
    assert pod['status']['phase'] == "Running"
    assert pod['spec']['containers'][0]['securityContext']['privileged']
    container = pod['status']['containerStatuses'][0]
    assert container['image'] == quay_image
    assert container['restartCount'] == 0
    assert container['ready']
    assert container['name'] == "privateregpod"
    # Remove registry
    remove_registry(client, admin_client, quay_creds, reg_cred)
    teardown_ns(namespace)
