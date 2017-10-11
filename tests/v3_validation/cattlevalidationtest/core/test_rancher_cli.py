from common_fixtures import *  # NOQA

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST
LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
RCLICOMMANDS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'resources/ranchercli')
RCCOMMANDS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'resources/rccmds')
RCV2COMMANDS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'resources/rccmds/v2')

logger = logging.getLogger(__name__)

if_compose_data_files = pytest.mark.skipif(
    not os.environ.get('CATTLE_TEST_DATA_DIR'),
    reason='Docker compose files directory location not set')


def test_cli_create_service(client, rancher_cli_container):

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

    check_config_for_service(client, service, {"rtest1": "value1"}, 1)

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_create_stop_start_service(client,
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

    check_config_for_service(client, service, {"rtest2": "value2"}, 1)

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "stop " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    assert service. state == "inactive"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(client, service)
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

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    time.sleep(10)
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_create_activate_deactivate_service(client,
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

    check_config_for_service(client, service, {"rtest3": "value3"}, 1)

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    command = "deactivate " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    assert service.state == "inactive"
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        container = client.wait_success(container)
        assert container.state == "stopped"

    command = "activate " + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    time.sleep(10)
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_create_restart_service(client,
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

    check_config_for_service(client, service, {"rtest4": "value4"}, 1)

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 1

    command = "restart " + stack_name + "/" + service.name
    cli_response = execute_rancher_cli(client, stack_name, command)
    service = client.wait_success(service, 60)
    if service.id in cli_response:
        assert True

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [stack])


def test_cli_create_restart_service_batch_interval(client,
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

    check_config_for_service(client, service, {"rtest5": "value5"}, 1)

    container_list = get_service_container_list(client, service)
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

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 4
    for container in container_list:
        assert container.state == "running"
        assert container.startCount == 2

    delete_all(client, [stack])


def test_cli_restart_container(client, rancher_cli_container):

    # This method deletes a standalone container
    stack_name = random_str().replace("-", "")
    container = []
    container = client.create_container(name="test_cont",
                                        networkMode=MANAGED_NETWORK,
                                        image=TEST_IMAGE_UUID)

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


def test_cli_delete_service(client,
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

    check_config_for_service(client, service, {"rtest6": "value6"}, 1)

    container_list = get_service_container_list(client, service)
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


def test_cli_delete_container(client, rancher_cli_container):

    # This method deletes a standalone container

    stack_name = random_str().replace("-", "")
    container = []
    container = client.create_container(name="test_cont_1",
                                        networkMode=MANAGED_NETWORK,
                                        image=TEST_IMAGE_UUID)

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


def test_cli_delete_stack(client,
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

    container_list = get_service_container_list(client, service)
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


def test_cli_show_services(client, rancher_cli_container):

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


def test_cli_show_containers(client, rancher_cli_container):

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


def test_cli_env_list(client, rancher_cli_container):

    # This method tests listing the environments

    stack_name = random_str().replace("-", "")

    command = "env ls"
    expected_response = ["cattle", "Default"]
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The cli response is \n"
    print cli_response
    for response in expected_response:
        if response in expected_response:
            assert True

    envlist = client.list_project()
    found = False
    for env in envlist:
        for resp in cli_response:
            if env.name in resp:
                found = True
    assert found


def test_cli_increment_scale(client, rancher_cli_container):

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

    check_config_for_service(client, service, {"rtest10": "value10"}, 1)

    container_list = get_service_container_list(client, service)
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
    container_list = get_service_container_list(client, service)
    assert len(container_list) == 3
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_decrement_scale(client, rancher_cli_container):

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

    check_config_for_service(client, service, {"rtest11": "value11"}, 1)

    container_list = get_service_container_list(client, service)
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
    container_list = get_service_container_list(client, service)
    assert len(container_list) == 1
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [stack])


def test_cli_inspect_service(client, rancher_cli_container):

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

    check_config_for_service(client, service, {"rtest12": "value12"}, 1)

    container_list = get_service_container_list(client, service)
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


def test_cli_inspect_container(client, rancher_cli_container):

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


def test_cli_create_restart_containers_of_service(client,
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

    check_config_for_service(client, service, {"rtest14": "value14"}, 1)

    container_list = get_service_container_list(client, service)
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


def test_cli_inspect_stack(client, rancher_cli_container):

    # This method tests inspecting a stack

    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc15.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest15")

    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "rtest15"

    # List stack by stack name
    stacklist = client.list_stack(name=stack_name)
    for line in stacklist.data:
        stackdata = line
    print stackdata.serviceIds
    # Confirm service is active and the containers are running
    command = "inspect --type stack " + stack_name
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is: "
    print cli_response

    for line in cli_response:
        cli_response_item = line
    print cli_response_item
    output = json.loads(cli_response_item)
    serviceidarray = output['serviceIds']
    print serviceidarray

    # Ensure all Service ids are in the list obtained from the api call
    for serviceid in stackdata.serviceIds:
        if serviceid in serviceidarray:
            assert True
    assert output['name'] == stack_name
    assert output['kind'] == 'stack'
    assert output['state'] == 'active'
    assert output['healthState'] == 'healthy'

    delete_all(client, [stack])


def test_cli_inspect_env(client, rancher_cli_container):

    # This method tests inspecting an environment

    stack_name = random_str().replace("-", "")

    envlist = client.list_project()
    print envlist
    for env in envlist:
        command = "inspect --type project " + env.name
        cli_response = execute_rancher_cli(client, stack_name, command)
        print "The CLI response is: "
        print cli_response
        for line in cli_response:
            cli_response_item = line
            print cli_response_item
            output = json.loads(cli_response_item)
            assert output['name'] == env.name
            assert output['kind'] == 'project'
            assert output['state'] == 'active'
            assert output['healthState'] == 'healthy'


def test_cli_inspect_host(client, rancher_cli_container):

    # This method tests inspecting a host

    stack_name = random_str().replace("-", "")

    hostlist = client.list_host()
    print hostlist
    for host in hostlist:
        command = "inspect --type host " + host.id
        cli_response = execute_rancher_cli(client, stack_name, command)
        print "The CLI response is: "
        print cli_response
        for line in cli_response:
            cli_response_item = line
            print cli_response_item
            output = json.loads(cli_response_item)
            instanceidarray = output['instanceIds']
            print instanceidarray
            print host.instanceIds
            # Ensure all container ids are in the list obtained from api call
            for id in host.instanceIds:
                if id in instanceidarray:
                    assert True
            assert output['id'] == host.id
            assert output['type'] == 'host'
            assert output['state'] == 'active'


def test_cli_host_list(client, rancher_cli_container):

    # This method tests listing hosts in an environment
    stack_name = random_str().replace("-", "")

    hostlist = client.list_host()
    state = "active"
    print hostlist

    command = "host ls"
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is:"
    print cli_response
    found = False
    for host in hostlist:
        for resp in cli_response:
            if host.id in resp and state in resp and \
                            host.agentIpAddress in resp:
                found = True
    assert found


def test_cli_volume_list(client, rancher_cli_container):

    # This method tests listing the volumes

    stack_name = random_str().replace("-", "")

    vol_list = client.list_volume()
    print "The List of volumes:"
    print vol_list

    command = "volume ls"
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is \n"
    print cli_response

    found = False
    for vol in vol_list:
        for resp in cli_response:
            # If Volume name is None assign it to empty string to
            # allow for comparison with CLI response
            if vol['name'] is None:
                vol['name'] = " "
            if vol['name'] in resp:
                found = True
    assert found


def test_cli_volume_create_remove(client, rancher_cli_container):

    # This method tests creating and deleting a volume

    stack_name = random_str().replace("-", "")

    vol_name = "test_vol"
    driver_name = "local"
    # Create a volume test_vol
    create_command = "volume create " + vol_name + " --driver " + driver_name
    print create_command
    cli_create_response = execute_rancher_cli(client, stack_name,
                                              create_command)
    print "The CLI response is \n"
    print cli_create_response

    # Create a service which uses the created volume test_vol
    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc16.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest16")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "rtest16"

    # List the volumes using API and ensure that the volume
    # created through CLI exists in the list
    vol_list = client.list_volume()
    print "The List of Volumes: "
    print vol_list

    vol_names_list = []
    for vol in vol_list:
        vol_names_list.append(vol['name'])
    if vol_name in vol_names_list:
        print "Success"

    # Delete the stack
    delete_all(client, [stack])

    # Remove the volume test_vol
    remove_command = "volume rm " + vol_name
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response
    # Delay to allow for deletion of volume
    time.sleep(15)

    # List the volumes after deletion
    vol_list = client.list_volume()
    print "The List of Volumes: "
    print vol_list

    vol_names_list = []
    for vol in vol_list:
        vol_names_list.append(vol['name'])
    print vol_names_list
    # Verify the volume is deleted
    if vol_name in vol_names_list:
        print "Volume not deleted"
        assert False


def test_cli_inspect_volume(client, rancher_cli_container):

    # This method tests inspecting volumes

    stack_name = random_str().replace("-", "")

    vol_name = "test_insp_vol"
    driver_name = "local"
    # Create a volume test_insp_vol
    create_command = "volume create " + vol_name + " --driver " + driver_name
    print create_command
    cli_create_response = execute_rancher_cli(client, stack_name,
                                              create_command)
    print "The volume create CLI response is \n"
    print cli_create_response

    # Create a service which uses test_insp_vol volume
    stack_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, stack_name,
        "up -d", "Creating stack", "dc17.yml")

    stack, service = get_env_service_by_name(client, stack_name, "rtest17")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 1
    assert service.name == "rtest17"

    # Inspect the created volume
    inspect_volume_command = "inspect " + vol_name
    cli_inspect_response = execute_rancher_cli(client, stack_name,
                                               inspect_volume_command)
    print "Inspect volume response"
    print cli_inspect_response
    time.sleep(5)
    for line in cli_inspect_response:
        cli_response_item = line
    print cli_response_item
    output = json.loads(cli_response_item)
    assert output['name'] == vol_name
    assert output['kind'] == 'volume'
    assert output['state'] == 'active'
    assert output['driver'] == 'local'

    delete_all(client, [stack])
    time.sleep(5)
    # Remove the volume test_insp_vol
    remove_command = "volume rm " + vol_name
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print "CLI remove response:"
    print cli_remove_response
    # Delay to allow for the deletion of volume
    time.sleep(5)

    # List the volumes after deletion
    vol_list = client.list_volume()
    vol_names_list = []
    for vol in vol_list:
        vol_names_list.append(vol['name'])
    print vol_names_list
    # Verify the volume is deleted
    if vol_name in vol_names_list:
        print "Volume not deleted"
        assert False


def test_cli_catalog_list(client, rancher_cli_container):

    # This method tests listing catalogs

    stack_name = random_str().replace("-", "")
    catalogs = []
    url = os.environ.get('CATTLE_TEST_URL')
    community_catalog_url = url + "/v1-catalog/templates?catalog=community"
    library_catalog_url = url + "/v1-catalog/templates?catalog=library"

    print "Community Catalog URL is" + community_catalog_url
    print "Library Catalog URL is" + library_catalog_url

    # Community Catalog Processing
    response = requests.get(community_catalog_url)
    template = json.loads(response.content)
    print template
    catalogdata = template["data"]
    for item in catalogdata:
        catalogs.append(item["name"])

    # Library Catalog Processing
    response = requests.get(library_catalog_url)
    template = json.loads(response.content)
    print template
    libcatalogdata = template["data"]
    for item in libcatalogdata:
        catalogs.append(item["name"])

    for catalog in catalogs:
        print "Catalog is :" + catalog

    # Execute 'catalog ls' command
    command = "catalog ls"
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The catalog list cli response is \n"
    print cli_response

    # Verify all the catalog items are listed
    found = False
    for catalog in catalogs:
        for line in cli_response:
            if catalog in line:
                found = True
    assert found


def test_cli_env_create_rm_cattle(admin_client, rancher_cli_container):

    # This method tests creating and removing a Cattle environment
    stack_name = random_str().replace("-", "")
    env_name = random_str().replace("-", "")
    orchestration = "cattle"
    command = "env create " + env_name
    print "Command is"
    print command
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The CLI response is \n"
    print cli_response
    envid = cli_response

    # Check if the newly created environment is of orchestration "Cattle"
    command = "env ls"
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The env list CLI response is \n"
    print cli_response
    for resp in cli_response:
        if env_name in resp:
            envarray = resp
    print envarray
    if envarray[2] == orchestration:
        assert True

    print "The env id is :" + repr(envid)
    remove_command = "env rm " + env_name

    # Remove the Environment created and ensure it is deleted
    cli_remove_response = execute_rancher_cli(admin_client, stack_name,
                                              remove_command)
    print cli_remove_response

    if envid in cli_remove_response:
        assert True

    # Verify that the env is removed from the envlist
    envlist = admin_client.list_project()
    for env in envlist:
        if envid == env.id:
            assert False


def test_cli_env_create_rm_kubernetes(admin_client,
                                      rancher_cli_container):
    # This method tests creating and removing a Kubernetes environment

    stack_name = random_str().replace("-", "")
    env_name = random_str().replace("-", "")
    orchestration = "kubernetes"
    command = "env create " + "-t" + " kubernetes " + env_name
    print "Command is"
    print command
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The CLI response is \n"
    print cli_response
    envid = cli_response

    # Check if the newly created environment is of orchestration "Kubernetes"
    command = "env ls"
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The env list CLI response is \n"
    print cli_response
    for resp in cli_response:
        if env_name in resp:
            envarray = resp
    print envarray
    if envarray[2] == orchestration:
        assert True

    print "The env id is :" + repr(envid)
    remove_command = "env rm " + env_name

    # Remove the Environment created and ensure it is deleted
    cli_remove_response = execute_rancher_cli(admin_client, stack_name,
                                              remove_command)
    print cli_remove_response

    if envid in cli_remove_response:
        assert True

    # Verify that the env is removed from the envlist
    envlist = admin_client.list_project()
    for env in envlist:
        if envid == env.id:
            assert False


def test_cli_env_create_rm_swarm(admin_client, rancher_cli_container):

    # This method tests creating and removing a Swarm environment

    stack_name = random_str().replace("-", "")
    env_name = random_str().replace("-", "")
    orchestration = "swarm"
    command = "env create " + "-t" + " swarm " + env_name
    print "Command is"
    print command
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The CLI response is \n"
    print cli_response
    envid = cli_response

    # Check if the newly created environment is of orchestration "Swarm"
    command = "env ls"
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The env list CLI response is \n"
    print cli_response
    for resp in cli_response:
        if env_name in resp:
            envarray = resp
    print envarray
    if envarray[2] == orchestration:
        assert True

    print "The env id is :" + repr(envid)
    remove_command = "env rm " + env_name

    # Remove the Environment created and ensure it is deleted
    cli_remove_response = execute_rancher_cli(admin_client, stack_name,
                                              remove_command)
    print cli_remove_response

    if envid in cli_remove_response:
        assert True

    # Verify that the env is removed from the envlist
    envlist = admin_client.list_project()
    for env in envlist:
        if envid == env.id:
            assert False


def test_cli_env_create_rm_mesos(admin_client, rancher_cli_container):

    # This method tests creating and removing a Mesos environment

    stack_name = random_str().replace("-", "")
    env_name = random_str().replace("-", "")
    orchestration = "mesos"
    command = "env create " + "-t" + " mesos " + env_name
    print "Command is"
    print command
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The CLI response is \n"
    print cli_response
    envid = cli_response

    # Check if the newly created environment is of orchestration "Mesos"
    command = "env ls"
    cli_response = execute_rancher_cli(admin_client, stack_name, command)
    print "The env list CLI response is \n"
    print cli_response

    for resp in cli_response:
        if env_name in resp:
            envarray = resp
    print envarray
    if envarray[2] == orchestration:
        assert True

    print "The env id :" + repr(envid)
    remove_command = "env rm " + env_name

    # Remove the Environment created and ensure it is deleted
    cli_remove_response = execute_rancher_cli(admin_client, stack_name,
                                              remove_command)
    print cli_remove_response

    if envid in cli_remove_response:
        assert True

    # Verify that the env is removed from the envlist
    envlist = admin_client.list_project()
    for env in envlist:
        if envid == env.id:
            assert False


def test_cli_list_system_services(client, rancher_cli_container):

    # This method tests displaying the services through "ps -s"

    stack_name = random_str().replace("-", "")
    services_list = client.list_service(system=True)
    print "The services are"
    print services_list

    command = "ps -s"
    cli_response = execute_rancher_cli(client, stack_name, command)
    print cli_response
    found = False
    # Verify the services listed
    for service in services_list:
        for resp in cli_response:
            if service['name'] in resp:
                found = True
    assert found


def test_cli_env_deactivate_activate(admin_client,
                                     rancher_cli_container):

    client = admin_client
    # This method tests deactivating and activating an environment

    stack_name = random_str().replace("-", "")
    env_name = random_str().replace("-", "")
    active_state = "active"
    inactive_state = "inactive"

    # Create an environment
    command = "env create " + env_name
    cli_response = execute_rancher_cli(client, stack_name, command)
    print "The CLI response is \n"
    print cli_response

    # Deactivate the environment

    deactivate_command = "env deactivate " + env_name
    cli_deactivate_response = execute_rancher_cli(client, stack_name,
                                                  deactivate_command)
    print "The CLI response is :"
    print cli_deactivate_response

    envlist = client.list_project()

    envdata = envlist.data
    for env in envdata:
        if env.name == env_name and env.state == inactive_state:
            print "Environemt is INACTIVE"
            envid = env.id
            assert True

    if envid in cli_deactivate_response:
        assert True

    # Activate the environment

    activate_command = "env activate " + env_name
    cli_activate_response = execute_rancher_cli(client, stack_name,
                                                activate_command)
    print "The CLI response is \n"
    print cli_activate_response

    envlist = client.list_project()

    envdata = envlist.data
    for env in envdata:
        if env.name == env_name and env.state == active_state:
            print "Environment is ACTIVE"
            envid = env.id
            assert True

    if envid in cli_activate_response:
        assert True

    print "The env id is :" + repr(envid)
    remove_command = "env rm " + env_name

    # Remove the Environment created and ensure it is deleted
    cli_remove_response = execute_rancher_cli(client, stack_name,
                                              remove_command)
    print cli_remove_response

    if envid in cli_remove_response:
        assert True

    # Verify that the env is removed from the envlist
    envlist = client.list_project()
    for env in envlist:
        if envid == env.id:
            assert False


def test_rancher_compose_services_log_driver(client,
                                             rancher_cli_container,
                                             socat_containers):
    compose_directory = RCCOMMANDS_SUBDIR
    check_rancher_compose_services_log_driver(client,
                                              compose_directory)


def test_rancher_compose_v2_services_log_driver(client,
                                                rancher_cli_container,
                                                socat_containers):
    compose_directory = RCV2COMMANDS_SUBDIR
    check_rancher_compose_services_log_driver(client,
                                              compose_directory)


def test_rancher_compose_services_network(client,
                                          rancher_cli_container,
                                          socat_containers):
    compose_directory = RCCOMMANDS_SUBDIR
    check_rancher_compose_services_network(client,
                                           compose_directory)


def test_rancher_compose_v2_services_network(client,
                                             rancher_cli_container,
                                             socat_containers):
    compose_directory = RCV2COMMANDS_SUBDIR
    check_rancher_compose_services_network(client,
                                           compose_directory)


def test_rancher_compose_services_security(client,
                                           rancher_cli_container,
                                           socat_containers):
    compose_directory = RCCOMMANDS_SUBDIR
    check_rancher_compose_services_security(client,
                                            compose_directory)


def test_rancher_compose_v2_services_security(client,
                                              rancher_cli_container,
                                              socat_containers):
    compose_directory = RCV2COMMANDS_SUBDIR
    check_rancher_compose_services_security(client,
                                            compose_directory)


def test_rancher_compose_services_volume(client,
                                         rancher_cli_container,
                                         socat_containers):
    compose_directory = RCCOMMANDS_SUBDIR
    check_rancher_compose_services_volume(client,
                                          compose_directory)


def test_rancher_compose_v2_services_volume(client,
                                            rancher_cli_container,
                                            socat_containers):
    compose_directory = RCV2COMMANDS_SUBDIR
    check_rancher_compose_services_network(client,
                                           compose_directory)


def check_rancher_compose_services_security(client,
                                            compose_directory):
    # This method tests the options in security tab in the UI
    stack_name = random_str().replace("-", "")
    dc_file = "dc3.yml"
    rc_file = "rc3.yml"
    # Create an environment using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test3", compose_directory, dc_file, rc_file)
    container_list = get_service_container_list(client, service)
    assert len(container_list) == 3
    for con in container_list:
        assert con.state == "running"
        containers = client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running " + con.name)
        assert inspect["State"]["Running"]
        assert inspect["HostConfig"]["Privileged"]
        assert inspect["HostConfig"]["Memory"] == 104857600
        assert inspect["HostConfig"]["CpuShares"] == 256
        assert inspect["HostConfig"]["CapAdd"] == ["AUDIT_CONTROL",
                                                   "AUDIT_WRITE"]
        assert inspect["HostConfig"]["CapDrop"] == ["BLOCK_SUSPEND",
                                                    "CHOWN"]
        assert inspect["Config"]["Hostname"] == "rancherhost"
        assert inspect["HostConfig"]["PidMode"] == "host"
    delete_all(client, [stack])


def check_rancher_compose_services_network(client,
                                           compose_directory):
    # This method tests the options in Network tab in the UI
    hostname_override = "io.rancher.container.hostname_override"
    requested_ip = "io.rancher.container.requested_ip"
    stack_name = random_str().replace("-", "")

    dc_file = "dc4.yml"
    rc_file = "rc4.yml"
    # Create an environment using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test4", compose_directory, dc_file, rc_file)

    # Confirm service is active and the containers are running
    assert service.state == "active"
    check_config_for_service(client, service,
                             {"testrc": "RANCHER_COMPOSE"}, 1)
    check_config_for_service(client, service,
                             {"io.rancher.container.requested_ip":
                              "209.243.140.21"}, 1)
    check_config_for_service(client, service,
                             {"io.rancher.container.hostname_override":
                                 "container_name"}, 1)

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for con in container_list:
        assert con.state == "running"
        containers = client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running " + con.name)
        assert inspect["State"]["Running"]
        assert inspect["Config"]["Domainname"] == "xyz.com"
        assert \
            inspect["Config"]["Labels"][hostname_override] \
            == "container_name"
        assert inspect["Config"]["Labels"][requested_ip] == "209.243.140.21"
        dns_list = inspect["HostConfig"]["Dns"]
        dnssearch_list = inspect["HostConfig"]["DnsSearch"]
        assert "209.243.150.21" in dns_list
        assert "www.google.com" in dnssearch_list
    delete_all(client, [stack])


def check_rancher_compose_services_log_driver(client,
                                              compose_directory):
    stack_name = random_str().replace("-", "")
    dc_file = "dc3.yml"
    rc_file = "rc3.yml"
    compose_directory = RCCOMMANDS_SUBDIR
    # Create an environment using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test3", compose_directory, dc_file, rc_file)

    # Confirm service is active and the containers are running
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 3
    for con in container_list:
        assert con.state == "running"
        containers = client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running" + con.name)
        assert inspect["State"]["Running"]
        assert inspect["HostConfig"]["LogConfig"]["Type"] == "syslog"

    delete_all(client, [stack])


def check_rancher_compose_services_volume(client,
                                          compose_directory):

    stack_name = random_str().replace("-", "")
    dc_file = "dc5.yml"
    rc_file = "rc5.yml"
    # Create an environment using up
    stack, service = create_stack_using_rancher_cli(
        client, stack_name, "test5", compose_directory, dc_file, rc_file)

    # Confirm service is active and the containers are running
    assert service.state == "active"

    container_list = get_service_container_list(client, service)
    assert len(container_list) == 2
    for con in container_list:
        assert con.state == "running"
        containers = client.list_container(
            externalId=con.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        logger.info("Checked for containers running " + con.name)
        assert inspect["State"]["Running"]
        assert "testvol:/home:rw" in inspect["HostConfig"]["Binds"]
    delete_all(client, [stack])
