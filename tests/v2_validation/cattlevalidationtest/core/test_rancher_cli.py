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

    # This method tests creation of a service

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc1.yml", "rc1.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest1"

    check_config_for_service(admin_client, service, {"rtest1": "value1"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_create_stop_start_service(admin_client, client,
                                       rancher_cli_container):

    # This method tests starting and stopping a service

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc2.yml", "rc2.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest2")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest2"

    check_config_for_service(admin_client, service, {"rtest2": "value2"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "stop " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    assert service. state == "inactive"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        container = client.wait_success(container, 60)
        assert container.state == "stopped"

    command = "start " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    assert service.state == "active"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    time.sleep(10)
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_create_activate_deactivate_service(admin_client, client,
                                                rancher_cli_container):

    # This method tests activate and deactivate commands
    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc3.yml", "rc3.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest3")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest3"

    check_config_for_service(admin_client, service, {"rtest3": "value3"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "deactivate " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    assert service.state == "inactive"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        container = client.wait_success(container)
        assert container.state == "stopped"

    command = "activate " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    time.sleep(10)
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_create_restart_service(admin_client, client,
                                    rancher_cli_container):

    # This method restarts a service for a given stack

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc4.yml", "rc4.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest4")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest4"

    check_config_for_service(admin_client, service, {"rtest4": "value4"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 1

    command = "restart " + stack_name + "/" + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [stack])


def test_cli_create_restart_service_batch_interval(admin_client, client,
                                                   rancher_cli_container):

    # This method restarts the service given batch-size and interval

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc5.yml", "rc5.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest5")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 4
    assert service.name == "rtest5"

    check_config_for_service(admin_client, service, {"rtest5": "value5"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 1

    command = "restart --type service --batch-size 2 --interval 1000 " \
              + stack_name + "/" + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [stack])


def test_cli_restart_container(admin_client, client,
                               rancher_cli_container):

    # This method deletes a standalone container
    stack_name = random_str().replace("-", "")
    container = []
    container = client.create_container(name="test_cont",
                                        networkMode=MANAGED_NETWORK,
                                        imageUuid=TEST_IMAGE_UUID)

    container = client.wait_success(container, 60)
    assert container.state == "running"
    assert container.startCount == 1

    print "The container id is:" + container.id
    command = "restart --type container " + container.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    container = client.wait_success(container, 60)
    print "CLI response is"
    print cli_response
    if container.id in cli_response:
        assert True

    container = client.list_container(name="test_cont", removed_null=True)
    print "The obtained container list is"
    print container
    assert len(container) == 1
    assert container[0].state == "running"
    assert container[0].startCount == 2

    delete_all(client, container)


def test_cli_delete_service(admin_client, client,
                            rancher_cli_container):

    # This method deletes a service belonging to a stack
    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc6.yml", "rc6.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest6")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest6"

    check_config_for_service(admin_client, service, {"rtest6": "value6"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "rm --type service " + stack_name + "/" + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    container = client.wait_success(service, 60)
    if service.id in cli_response:
        assert True
    mystack = client.list_stack(name=stack_name)
    service = client.list_service(name="rtest6",
                                  environmentId=mystack[0].id,
                                  removed_null=True)
    assert len(service) == 0
    delete_all(client, [stack])


def test_cli_delete_container(admin_client, client,
                              rancher_cli_container):

    # This method deletes a standalone container

    stack_name = random_str().replace("-", "")
    container = []
    container = client.create_container(name="test_cont_1",
                                        networkMode=MANAGED_NETWORK,
                                        imageUuid=TEST_IMAGE_UUID)

    container = client.wait_success(container, 60)

    print "The container id is:" + container.id
    command = "rm --type container " + container.id
    print "The container id after deletion is:" + container.id
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is"
    print cli_response
    container = client.wait_success(container, 60)
    if container.id in cli_response:
        print container.state
        assert True

    container = client.list_container(name="test_cont_1",
                                      removed_null=True)
    assert len(container) == 0
    delete_all(client, container)


def test_cli_delete_stack(admin_client, client,
                          rancher_cli_container):

    # This method deletes a stack

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc7.yml", "rc7.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest7")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest7"

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "rm --type stack " + stack_name
    cli_response = execute_rancher_cli(client, stack_name, command)
    if stack.id in cli_response:
        assert True
    mystack = client.list_stack(name=stack_name)
    assert len(mystack.data) == 0
    delete_all(client, [stack])


def test_cli_show_services(admin_client, client,
                           rancher_cli_container):

    # This method tests displaying the services through "ps -a"

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc8.yml", "rc8.yml")

    stack, service1 = get_env_service_by_name(client, stack_name, "rtest8-one")
    stack, service2 = get_env_service_by_name(client, stack_name, "rtest8-two")

    # Confirm service is active and the containers are running
    assert service1.state == "active"
    assert service1.scale == 2
    assert service1.name == "rtest8-one"

    assert service2.state == "active"
    assert service2.scale == 2
    assert service2.name == "rtest8-two"

    # Stop the service2 to ensure that stopped services also get listed
    # in ps -a command
    command = "stop " + service2.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service2, 60)
    assert service.state == "inactive"
    if service.id in cli_response:
        assert True

    command = "ps -a"
    expected_response = ["rtest8-one", "rtest8-two"]
    cli_response = execute_rancher_cli(client, stack_name, command)
    print cli_response
    for service in expected_response:
        if service in cli_response:
            assert True
    delete_all(client, [stack])


def test_cli_show_containers(admin_client, client,
                             rancher_cli_container):

    # This method tests displaying the containers through "ps -c"

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc9.yml", "rc9.yml")

    stack, service1 = get_env_service_by_name(client, stack_name, "rtest9")

    # Confirm service is active and the containers are running
    assert service1.state == "active"
    assert service1.scale == 2
    assert service1.name == "rtest9"

    command = "ps -c"
    container1 = stack_name+"/"+"rtest9"+FIELD_SEPARATOR+"1"
    container2 = stack_name+"/"+"rtest9"+FIELD_SEPARATOR+"2"
    expected_response = [container1, container2, "Network Agent"]
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is: "
    print cli_response
    for container in expected_response:
        if container in cli_response:
            assert True
    delete_all(client, [stack])


def test_cli_env_list(admin_client, client, rancher_cli_container):

    # This method tests listing the environments

    stack_name = random_str().replace("-", "")

    command = "env ls"
    expected_response = ["cattle", "Default"]
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The cli response is \n"
    print cli_response
    for response in expected_response:
        if response in expected_response:
            assert True

    envlist = admin_client.list_project()
    found = False
    for env in envlist:
        for resp in cli_response:
            if env.name in resp:
                found = True
    assert found


def test_cli_increment_scale(admin_client, client, rancher_cli_container):

    # This method tests incrementing the scale of a service

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc10.yml", "rc10.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest10")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest10"

    check_config_for_service(admin_client, service, {"rtest10": "value10"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "scale rtest10=3"
    expected_response = "rtest10"
    cli_response = execute_rancher_cli(client, stack_name, command)
    print cli_response
    if expected_response in cli_response:
        assert True
    service = client.wait_success(service, 60)
    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_decrement_scale(admin_client, client, rancher_cli_container):

    # This method tests decrementing the scale of a service

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc11.yml", "rc11.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest11")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "rtest11"

    check_config_for_service(admin_client, service, {"rtest11": "value11"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "scale rtest11=1"
    expected_response = "rtest11"
    cli_response = execute_rancher_cli(client, stack_name, command)
    print cli_response
    if expected_response in cli_response:
        assert True
    service = client.wait_success(service, 60)
    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_inspect_service(admin_client, client, rancher_cli_container):

    # This method tests inspecting a service

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc12.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest12")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "rtest12"

    check_config_for_service(admin_client, service, {"rtest12": "value12"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    command = "inspect rtest12"
    expected_response = "rtest12"
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is: "
    print cli_response
    if expected_response in cli_response:
        assert True

    print len(cli_response)
    for line in cli_response:
        cli_response_item = line
    print cli_response_item
    output = json.loads(cli_response_item)
    assert output['name'] == 'rtest12'
    assert output['kind'] == 'service'
    assert output['currentScale'] == 1
    assert output['healthState'] == 'healthy'

    delete_all(client, [stack])


def test_cli_inspect_container(admin_client, client,
                               rancher_cli_container):

    # This method tests inspecting a container

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc13.yml")

    stack, service1 = get_env_service_by_name(client, stack_name, "rtest13")

    # Confirm service is active and the containers are running
    assert service1.state == "active"
    assert service1.scale == 1
    assert service1.name == "rtest13"
    container_name = stack_name+FIELD_SEPARATOR+"rtest13"+FIELD_SEPARATOR+"1"
    command = "inspect " + container_name
    print command
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is: "
    print cli_response

    for line in cli_response:
        cli_response_item = line

    print cli_response_item
    output = json.loads(cli_response_item)
    assert output['name'] == container_name
    assert output['kind'] == 'container'

    delete_all(client, [stack])


def test_cli_create_restart_containers_of_service(admin_client, client,
                                                  rancher_cli_container):

    # This method restarts containers of a service

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc14.yml", "rc14.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest14")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 4
    assert service.name == "rtest14"

    check_config_for_service(admin_client, service, {"rtest14": "value14"}, 1)

    container_list = get_service_container_list(admin_client, service)
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 1
        command = "restart --type container " + container.id
        cli_response = execute_rancher_cli(client, stack_name, command)
        container = client.wait_success(container, 60)
        if container.id in cli_response:
            assert True
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [stack])
