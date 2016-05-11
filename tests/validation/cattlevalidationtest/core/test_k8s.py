from common_fixtures import *  # NOQA

if_test_k8s = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY') or
    not os.environ.get('TEST_K8S'),
    reason='DIGITALOCEAN_KEY/TEST_K8S is not set')


# Creating Environment namespace
def create_ns(namespace):
    expected_result = ['namespace "'+namespace+'" created']
    execute_kubectl_cmds(
        "create namespace "+namespace, expected_result)
    # Verify namespace is created
    get_response = execute_kubectl_cmds(
        "get namespace "+namespace+" -o json")
    secret = json.loads(get_response)
    assert secret["metadata"]["name"] == namespace
    assert secret["status"]["phase"] == "Active"


# Teardown Environment namespace
def teardown_ns(namespace):
    expected_result = ['namespace "'+namespace+'" deleted']
    execute_kubectl_cmds(
        "delete namespace "+namespace, expected_result)
    time.sleep(30)
    # Verify namespace is deleted
    expected_error = \
        'Error from server: namespaces "'+namespace+'" not found'
    execute_kubectl_cmds(
        "get namespace "+namespace+" -o json", expected_error=expected_error)


# Waitfor Pod
def waitfor_pods(selector=None, namespace="default", number=1, state="Running"):
    timeout = 0
    all_running = True
    get_response = execute_kubectl_cmds("get pod --selector="+selector+" -o json -a --namespace="+namespace)
    pod = json.loads(get_response)
    pods = pod['items']
    pods_no = len(pod['items'])
    while True:
        if pods_no == number:
            for pod in pods:
                if pod['status']['phase'] != state:
                    all_running = False
            if all_running:
                break
        time.sleep(5)
        timeout += 5
        if timeout == 300:
            raise ValueError('Timeout Exception: pods did not run properly')
        get_response = execute_kubectl_cmds("get pod --selector="+selector+" -o json -a --namespace="+namespace)
        pod = json.loads(get_response)
        pods = pod['items']
        pods_no = len(pod['items'])
        all_running = True


@if_test_k8s
def test_k8s_env_create(
        super_client, admin_client, client, kube_hosts):
    namespace = "create-namespace"
    create_ns(namespace)
    name = "testnginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="create_nginx.yml")

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

    waitfor_pods(selector="name=testnginx", namespace=namespace, number=2)
    # Verify pods are created
    get_response = execute_kubectl_cmds(
        "get pod --selector=name=testnginx -o json --namespace="+namespace)
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
        super_client, admin_client, client, kube_hosts):
    namespace = "edit-namespace"
    create_ns(namespace)
    name = "testeditnginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="edit_nginx.yml")

    get_response = execute_kubectl_cmds(
        "get rc testeditnginx -o json --namespace="+namespace)
    rc = json.loads(get_response)
    replica_count = rc["spec"]["replicas"]
    assert replica_count == 2

    expected_result = ['replicationcontroller "'+name+'" replaced']
    execute_kubectl_cmds(
        "replace --namespace="+namespace, expected_result, file_name="edit_update-rc-nginx.yml")
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace)
    rc = json.loads(get_response)
    replica_count = rc["spec"]["replicas"]
    assert replica_count == 3
    waitfor_pods(selector="name="+name, namespace=namespace, number=3)

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
        super_client, admin_client, client, kube_hosts):
    namespace = "delete-namespace"
    create_ns(namespace)
    name = "testdeletenginx"
    expected_result = ['replicationcontroller "'+name+'" created',
                       'service "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="delete_nginx.yml")
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

    waitfor_pods(selector="name="+name, namespace=namespace, number=2)
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
        "get service "+name+" -o json --namespace="+namespace, expected_error=expected_error)

    # Delete RC
    expected_result = ['replicationcontroller "'+name+'" deleted']
    execute_kubectl_cmds(
        "delete rc "+name+" --namespace="+namespace, expected_result)

    # Verify RC is deleted
    expected_error = \
        'Error from server: replicationcontrollers "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get rc "+name+" -o json --namespace="+namespace, expected_error=expected_error)

    # Verify pods are deleted
    expected_result = ['Error from server: rc "'+name+'" not found']
    get_response = execute_kubectl_cmds(
        "get pod --selector=name="+name+" -o json --namespace="+namespace)

    pod = json.loads(get_response)
    assert len(pod["items"]) == 0
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_secret(
        super_client, admin_client, client, kube_hosts):
    namespace = "secret-namespace"
    create_ns(namespace)
    name = "testsecret"
    expected_result = ['secret "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="secret.yml")
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
        "delete --namespace="+namespace, expected_result, file_name="secret.yml")
    # Verify Secret is deleted
    expected_error = \
        'Error from server: secrets "'+name+'" not found'
    get_response = execute_kubectl_cmds(
        "get secret "+name+" -o json --namespace="+namespace, expected_error=expected_error)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_namespace(
        super_client, admin_client, client, kube_hosts):
    namespace = "testnamespace"
    create_ns(namespace)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_rollingupdates(
        super_client, admin_client, client, kube_hosts):
    namespace = "rollingupdates-namespace"
    create_ns(namespace)
    name = "testru"
    expected_result = ['replicationcontroller "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="rollingupdates_nginx.yml")

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
    command = "rolling-update testru testruv2 --image=nginx:1.9.1 --namespace="+namespace
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
        super_client, admin_client, client, kube_hosts):
    namespace = "configmaps-namespace"
    create_ns(namespace)
    name = "testconfigmap"
    expected_result = ['configmap "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="configmap.yml")

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
        "delete configmap testconfigmap --namespace="+namespace, expected_result)

    # Verify namespace is deleted
    expected_error = \
        'Error from server: configmaps "'+name+'" not found'
    get_response = execute_kubectl_cmds("get configmap "+name+" -o json --namespace="+namespace, expected_error=expected_error)
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_resourceQuota(
        super_client, admin_client, client, kube_hosts):
    name = "quota"
    namespace = "quota-example"
    create_ns(namespace)
    # Create resource quota object
    expected_result = ['resourcequota "'+name+'" created']
    execute_kubectl_cmds(
        "create --namespace="+namespace, expected_result, file_name="quota.json")
    # Create rc to test the quota
    execute_kubectl_cmds(
        "create", file_name="quota_nginx.yml")
    # Verify that creation failed
    describe_response = execute_kubectl_cmds(
        "describe rc testnginx --namespace="+namespace)
    failed_str = 'Error creating: pods "testnginx-" is forbidden: Exceeded quota: quota'
    assert failed_str in describe_response
    teardown_ns(namespace)


@if_test_k8s
def test_k8s_env_deployments(
        super_client, admin_client, client, kube_hosts):
    namespace = 'deployments-namespace'
    create_ns(namespace)
    name = "nginx-deployment"
    # Create deployment
    expected_result = ['deployment "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result, file_name="nginx-deployment.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=3)
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
        super_client, admin_client, client, kube_hosts):
    namespace = 'deploymentsrollback-namespace'
    create_ns(namespace)
    name = "nginx-deployment"
    # Create deployment
    expected_result = ['deployment "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result, file_name="nginx-deployment.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds("get deployment "+name+" -o json --namespace="+namespace)
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
    execute_kubectl_cmds("apply --namespace="+namespace, expected_result, file_name="nginx-deploymentv2.yml")
    waitfor_pods(selector="app=nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds("get deployment "+name+" -o json --namespace="+namespace)
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
    execute_kubectl_cmds("rollout undo --namespace="+namespace+" deployment/"+name, expected_result)
    waitfor_pods(selector="app=nginx", namespace=namespace, number=3)
    get_response = execute_kubectl_cmds("get deployment "+name+" -o json --namespace="+namespace)
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
        super_client, admin_client, client, kube_hosts):
    namespace = 'jobs-namespace'
    create_ns(namespace)
    name = "pitest"
    # Create deployment
    expected_result = ['job "'+name+'" created']
    execute_kubectl_cmds("create --namespace="+namespace, expected_result, file_name="job.yml")
    waitfor_pods(selector="job-name=pitest", namespace=namespace, state="Succeeded", number=1)
    get_response = execute_kubectl_cmds("get jobs "+name+" -o json --namespace="+namespace)
    deployment = json.loads(get_response)
    assert deployment["kind"] == "Job"
    assert deployment["metadata"]["name"] == name
    assert deployment["status"]["conditions"][0]["type"] == "Complete"
    assert deployment["status"]["conditions"][0]["status"] == "True"
    assert deployment["status"]["succeeded"] == 1
    teardown_ns(namespace)
