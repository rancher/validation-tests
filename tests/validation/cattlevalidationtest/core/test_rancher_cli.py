from common_fixtures import *  # NOQA

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST
LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
RCLICOMMANDS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'resources/ranchercli')
logger = logging.getLogger(__name__)

if_compose_data_files = pytest.mark.skipif(
    not os.environ.get('CATTLE_TEST_DATA_DIR'),
    reason='Docker compose files directory location not set')


def test_cli_create_service(admin_client, client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc1.yml", "rc1.yml")

    env, service = get_env_service_by_name(client, stack_name, "test1")

    print "ID is:" + service.id

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "test1"

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])


def test_cli_create_stop_start_service(admin_client, client,
                                       rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc1.yml", "rc1.yml")

    env, service = get_env_service_by_name(client, stack_name, "test1")
    print service.id

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "test1"

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "stop " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       service.id, docker_compose=None,
                                       rancher_compose=None)
    service = client.wait_success(service, 300)
    assert service. state == "inactive"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        container = client.wait_success(container, 300)
        assert container.state == "stopped"

    command = "start " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       service.id, docker_compose=None,
                                       rancher_compose=None)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    time.sleep(10)
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])


def test_cli_create_activate_deactivate_service(admin_client, client,
                                                rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc1.yml", "rc1.yml")

    env, service = get_env_service_by_name(client, stack_name, "test1")
    print service.id

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "test1"

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "deactivate " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       service.id, docker_compose=None,
                                       rancher_compose=None)
    service = client.wait_success(service, 300)
    assert service.state == "inactive"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        container = client.wait_success(container)
        assert container.state == "stopped"

    command = "activate " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       service.id, docker_compose=None,
                                       rancher_compose=None)
    service = client.wait_success(service, 300)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    time.sleep(10)
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])


def test_cli_create_restart_service(admin_client, client,
                                    rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc1.yml", "rc1.yml")

    env, service = get_env_service_by_name(client, stack_name, "test1")
    print service.id

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "test1"

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "restart " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       service.id, docker_compose=None,
                                       rancher_compose=None)
    service = client.wait_success(service, 300)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [env])


def test_cli_create_restart_service_batch_interval(admin_client, client,
                                                   rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc2.yml", "rc2.yml")

    env, service = get_env_service_by_name(client, stack_name, "test2")
    print service.id

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 4
    assert service.name == "test2"

    check_config_for_service(admin_client, service, {"test2": "value2"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"

    command = "restart --type service --batch-size 2 --interval 1000 " \
              + service.name
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       service.id, docker_compose=None,
                                       rancher_compose=None)
    service = client.wait_success(service)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [env])


def test_cli_delete_service(admin_client, client,
                            rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc1.yml", "rc1.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test1")
    print service.id

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "test1"

    check_config_for_service(admin_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "rm --type service " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       service.id, docker_compose=None,
                                       rancher_compose=None)
    if service.id in cli_response:
        assert True
    env = client.list_environment(name=stack_name)
    service = client.list_service(name="test1",
                                  environmentId=env[0].id,
                                  removed_null=True)
    assert len(service) == 0
    delete_all(client, [stack])


def test_cli_delete_container(admin_client, client,
                              rancher_cli_container):

    stack_name = random_str().replace("-", "")
    container = []
    container = client.create_container(name="test_name",
                                        networkMode=MANAGED_NETWORK,
                                        imageUuid=TEST_IMAGE_UUID)

    container = client.wait_success(container, 60)

    command = "rm --type container " + container.id
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       container.id, docker_compose=None,
                                       rancher_compose=None)
    container = client.wait_success(container, 60)
    print container.id
    if container.id in cli_response:
        assert True

    container = client.list_container(name="test_name",
                                      removed_null=True)
    assert len(container) == 0
    delete_all(client, container)


def test_cli_list_process(admin_client, client,
                          rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc3.yml", "rc3.yml")

    env, service1 = get_env_service_by_name(client, stack_name, "test1")
    env, service2 = get_env_service_by_name(client, stack_name, "test2")

    print "ID is:" + service1.id

    # Confirm service is active and the containers are running
    assert service1.state == "active"
    assert service1.scale == 2
    assert service1.name == "test1"

    assert service2.state == "active"
    assert service2.scale == 2
    assert service2.name == "test2"

    command = "ps -a"
    expected_response = ["test1", "test2"]
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       expected_response, docker_compose=None,
                                       rancher_compose=None)
    for service in expected_response:
        if service in cli_response:
            assert True
    delete_all(client, [env])


def test_cli_env_list(admin_client, client, rancher_cli_container):

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc2.yml", "rc2.yml")

    stack, service = get_env_service_by_name(client, stack_name, "test2")
    print service.id

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 4
    assert service.name == "test2"

    check_config_for_service(admin_client, service, {"test2": "value2"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"

    command = "env ls"
    expected_response = "cattle"
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       expected_response, docker_compose=None,
                                       rancher_compose=None)
    if expected_response in cli_response:
        assert True

    delete_all(client, [stack])


def test_cli_catalog_list(admin_client, client,
                          rancher_cli_container):

    stack_name = random_str().replace("-", "")

    command = "catalog ls"
    catalogs = []
    response = []
    catalog_url = cattle_url() + "v1-catalog/catalogs/community/templates"
    print "URL is" + catalog_url
    response = requests.get(catalog_url)
    template = json.loads(response.content)
    catalogdata = template["data"]
    for item in catalogdata:
        catalogs.append(item["name"])
    print "\n"
    for catalog in catalogs:
        print "Catalog is :" + catalog
    cli_response = execute_rancher_cli(client, stack_name, command,
                                       catalogs, docker_compose=None,
                                       rancher_compose=None)
    print cli_response
    found = False
    for catalog in catalogs:
        for line in cli_response:
            if catalog in line:
                found = True
    assert found
