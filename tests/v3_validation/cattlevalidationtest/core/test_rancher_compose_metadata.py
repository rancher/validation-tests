from common_fixtures import *  # NOQA
import json


METADATA_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'resources/metadatadc')

logger = logging.getLogger(__name__)
start_project_str = "Starting"

if_compose_data_files = pytest.mark.skipif(
    not os.path.isdir(METADATA_SUBDIR),
    reason='Docker compose files directory location not set/ does not Exist')

metadata_client_service = []
metadata_client_port = 999


@pytest.fixture(scope='session', autouse=True)
def create_metadata_client_service(request, client):
    env = create_env(client)
    launch_config = {"image": SSH_IMAGE_UUID,
                     "ports": [str(metadata_client_port) + ":22/tcp"],
                     "labels": {"io.rancher.scheduler.global": "true"}}
    service = client.create_service(name="metadataclient",
                                    stackId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service, 60)
    env = env.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    metadata_client_service.extend(
        get_service_container_list(client, service))

    def fin():
        delete_all(client, [service])
    request.addfinalizer(fin)


@if_compose_data_files
def test_metadata_self_2016_07_29(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_1_2016_07_29.yml"
    rc_file = "rc_metadata_1_2016_07_29.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test120160729", METADATA_SUBDIR, dc_file, rc_file)

    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]

    service_containers = get_service_container_list(client, service)
    port = 6002
    con_metadata = {}
    wait_for_metadata_propagation(client)
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2016-07-29")
        con_metadata[con.name] = json.loads(metadata_str)

    for con in service_containers:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/service", "2016-07-29")
        service_metadata = json.loads(metadata_str)

        con_list = service_metadata["containers"]
        # Check for container object list
        assert len(con_list) == len(con_metadata.keys())
        for container in con_list:
            print container
            print con_metadata[container["name"]]
            assert cmp(container, con_metadata[container["name"]]) == 0

        assert service_metadata["name"] == "test120160729"
        assert service_metadata["ports"] == ["6002:22/tcp"]
        assert service_metadata["stack_name"] == env_name
        assert service_metadata["kind"] == "service"
        assert service_metadata["labels"] == service.launchConfig["labels"]
        assert service_metadata["metadata"] == service.metadata
        assert service_metadata["uuid"] == service.uuid

        host = con.host()

        # Host related metadata
        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/host", "2016-07-29")
        metadata = json.loads(metadata_str)
        assert metadata["agent_ip"] == host.ipAddresses()[0].address
        assert metadata["labels"] == host.labels
        assert metadata["name"] == host.hostname
        assert metadata["uuid"] == host.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/stack", "2016-07-29")
        metadata = json.loads(metadata_str)

        assert metadata["environment_name"] == "Default"
        # Check for service object list

        # Set token value to None in service metadata object returned
        # from self before comparing service object retrieved by index
        service_metadata["token"] = None
        assert cmp(metadata["services"][0], service_metadata) == 0

        assert metadata["name"] == env.name
        assert metadata["uuid"] == env.uuid

        # Container related metadata

        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/container", "2016-07-29")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        assert metadata["host_uuid"] == host.uuid
        assert metadata["ips"] == [con.primaryIpAddress]
        assert metadata["labels"] == con.labels
        assert metadata["name"] == con.name
        assert metadata["ports"] == ["0.0.0.0" +
                                     ":6002:22/tcp"]
        assert metadata["primary_ip"] == con.primaryIpAddress
        assert metadata["service_name"] == "test120160729"
        assert metadata["stack_name"] == env.name
        assert metadata["uuid"] == con.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_byname_2016_07_29(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_2_2016_07_29.yml"
    rc_file = "rc_metadata_2_2016_07_29.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test2120160729", METADATA_SUBDIR, dc_file, rc_file)
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]
    service_containers = get_service_container_list(client, service)
    wait_for_metadata_propagation(client)
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2016-07-29")
        con_metadata[con.name] = json.loads(metadata_str)

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "test2120160729",
                                              "2016-07-29")
        service_metadata = json.loads(metadata_str)
        con_list = service_metadata["containers"]
        # Check for container object list
        assert len(con_list) == len(con_metadata.keys())
        for container in con_list:
            assert cmp(container, con_metadata[container["name"]]) == 0

        print service_metadata["external_ips"]
        print service_metadata["hostname"]
        assert service_metadata["name"] == "test2120160729"
        assert service_metadata["stack_name"] == env_name
        assert service_metadata["kind"] == "service"
        assert service_metadata["labels"] == service.launchConfig["labels"]
        assert service_metadata["metadata"] == service.metadata
        assert service_metadata["uuid"] == service.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "stacks/" + env_name,
                                              "2016-07-29")
        metadata = json.loads(metadata_str)
        assert metadata["environment_name"] == "Default"
        # Check for service object list
        assert cmp(metadata["services"][0], service_metadata) == 0
        assert metadata["name"] == env.name
        assert metadata["uuid"] == env.uuid

        # Container related metadata
        con = service_containers[0]
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2016-07-29")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        host = con.host()
        assert metadata["host_uuid"] == host.uuid
        assert metadata["ips"] == [con.primaryIpAddress]
        assert metadata["labels"] == con.labels
        assert metadata["name"] == con.name
        assert metadata["primary_ip"] == con.primaryIpAddress
        assert metadata["service_name"] == "test2120160729"
        assert metadata["stack_name"] == env.name
        assert metadata["uuid"] == con.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_self_2015_12_19(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_1n.yml"
    rc_file = "rc_metadata_1n.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test1n", METADATA_SUBDIR, dc_file, rc_file)
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]

    service_containers = get_service_container_list(client, service)
    port = 6001
    con_metadata = {}
    wait_for_metadata_propagation(client)
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2015-12-19")
        con_metadata[con.name] = json.loads(metadata_str)

    for con in service_containers:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/service", "2015-12-19")
        service_metadata = json.loads(metadata_str)

        con_list = service_metadata["containers"]
        # Check for container object list
        assert len(con_list) == len(con_metadata.keys())
        for container in con_list:
            assert cmp(container, con_metadata[container["name"]]) == 0

        assert service_metadata["name"] == "test1n"
        assert service_metadata["ports"] == ["6001:22/tcp"]
        assert service_metadata["stack_name"] == env_name
        assert service_metadata["kind"] == "service"
        assert service_metadata["labels"] == service.launchConfig["labels"]
        assert service_metadata["metadata"] == service.metadata
        assert service_metadata["uuid"] == service.uuid

        host = con.host()

        # Host related metadata
        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/host", "2015-12-19")
        metadata = json.loads(metadata_str)
        assert metadata["agent_ip"] == host.ipAddresses()[0].address
        assert metadata["labels"] == host.labels
        assert metadata["name"] == host.hostname
        assert metadata["uuid"] == host.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/stack", "2015-12-19")
        metadata = json.loads(metadata_str)

        assert metadata["environment_name"] == "Default"
        # Check for service object list

        # Set token value to None in service metadata object returned
        # from self before comparing service object retrieved by index
        service_metadata["token"] = None
        assert cmp(metadata["services"][0], service_metadata) == 0

        assert metadata["name"] == env.name
        assert metadata["uuid"] == env.uuid

        # Container related metadata

        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/container", "2015-12-19")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        assert metadata["host_uuid"] == host.uuid
        assert metadata["ips"] == [con.primaryIpAddress]
        assert metadata["labels"] == con.labels
        assert metadata["name"] == con.name
        assert metadata["ports"] == [host.ipAddresses()[0].address +
                                     ":6001:22/tcp"]
        assert metadata["primary_ip"] == con.primaryIpAddress
        assert metadata["service_name"] == "test1n"
        assert metadata["stack_name"] == env.name
        assert metadata["uuid"] == con.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_byname_2015_12_19(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_2n.yml"
    rc_file = "rc_metadata_2n.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test2n", METADATA_SUBDIR, dc_file, rc_file)
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]
    service_containers = get_service_container_list(client, service)
    wait_for_metadata_propagation(client)
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2015-12-19")
        con_metadata[con.name] = json.loads(metadata_str)

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "test2n",
                                              "2015-12-19")
        service_metadata = json.loads(metadata_str)
        con_list = service_metadata["containers"]
        # Check for container object list
        assert len(con_list) == len(con_metadata.keys())
        for container in con_list:
            assert cmp(container, con_metadata[container["name"]]) == 0

        print service_metadata["external_ips"]
        print service_metadata["hostname"]
        assert service_metadata["name"] == "test2n"
        assert service_metadata["stack_name"] == env_name
        assert service_metadata["kind"] == "service"
        assert service_metadata["labels"] == service.launchConfig["labels"]
        assert service_metadata["metadata"] == service.metadata
        assert service_metadata["uuid"] == service.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "stacks/" + env_name,
                                              "2015-12-19")
        metadata = json.loads(metadata_str)
        assert metadata["environment_name"] == "Default"
        # Check for service object list
        assert cmp(metadata["services"][0], service_metadata) == 0
        assert metadata["name"] == env.name
        assert metadata["uuid"] == env.uuid

        # Container related metadata
        con = service_containers[0]
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2015-12-19")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        host = con.host()
        assert metadata["host_uuid"] == host.uuid
        assert metadata["ips"] == [con.primaryIpAddress]
        assert metadata["labels"] == con.labels
        assert metadata["name"] == con.name
        assert metadata["primary_ip"] == con.primaryIpAddress
        assert metadata["service_name"] == "test2n"
        assert metadata["stack_name"] == env.name
        assert metadata["uuid"] == con.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_self_2015_07_25(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_1.yml"
    rc_file = "rc_metadata_1.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test", METADATA_SUBDIR, dc_file, rc_file)
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]
    wait_for_metadata_propagation(client)
    service_containers = get_service_container_list(client, service)
    port = 6000
    con_names = []
    for con in service_containers:
        con_names.append(con.name)

    for con in service_containers:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/service", "2015-07-25")
        metadata = json.loads(metadata_str)

        assert set(metadata["containers"]) == set(con_names)
        print metadata["external_ips"]
        print metadata["hostname"]
        assert metadata["name"] == "test"
        assert metadata["ports"] == ["6000:22/tcp"]
        assert metadata["stack_name"] == env_name
        assert metadata["kind"] == "service"
        assert metadata["labels"] == service.launchConfig["labels"]
        assert metadata["metadata"] == service.metadata
        assert metadata["uuid"] == service.uuid

        host = con.host()

        # Host related metadata
        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/host", "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["agent_ip"] == host.ipAddresses()[0].address
        assert metadata["labels"] == host.labels
        assert metadata["name"] == host.hostname
        assert metadata["uuid"] == host.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/stack", "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["environment_name"] == "Default"
        assert metadata["services"] == ["test"]
        assert metadata["name"] == env.name
        assert metadata["uuid"] == env.uuid

        # Container related metadata

        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/container", "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        assert metadata["host_uuid"] == host.uuid
        assert metadata["ips"] == [con.primaryIpAddress]
        assert metadata["labels"] == con.labels
        assert metadata["name"] == con.name
        assert metadata["ports"] == [host.ipAddresses()[0].address +
                                     ":6000:22/tcp"]
        assert metadata["primary_ip"] == con.primaryIpAddress
        assert metadata["service_name"] == "test"
        assert metadata["stack_name"] == env.name
        assert metadata["uuid"] == con.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_byname_2015_07_25(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_2.yml"
    rc_file = "rc_metadata_2.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test2", METADATA_SUBDIR, dc_file, rc_file)
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]
    service_containers = get_service_container_list(client, service)
    con_names = []
    for con in service_containers:
        con_names.append(con.name)

    wait_for_metadata_propagation(client)
    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "test2",
                                              "2015-07-25")
        metadata = json.loads(metadata_str)

        assert set(metadata["containers"]) == set(con_names)
        print metadata["external_ips"]
        print metadata["hostname"]
        assert metadata["name"] == "test2"
        assert metadata["stack_name"] == env_name
        assert metadata["kind"] == "service"
        assert metadata["labels"] == service.launchConfig["labels"]
        assert metadata["metadata"] == service.metadata
        assert metadata["uuid"] == service.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "stacks/" + env_name,
                                              "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["environment_name"] == "Default"
        assert metadata["services"] == ["test2"]
        assert metadata["name"] == env.name
        assert metadata["uuid"] == env.uuid

        # Container related metadata
        con = service_containers[0]
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        host = con.host()
        assert metadata["host_uuid"] == host.uuid
        assert metadata["ips"] == [con.primaryIpAddress]
        assert metadata["labels"] == con.labels
        assert metadata["name"] == con.name
        assert metadata["primary_ip"] == con.primaryIpAddress
        assert metadata["service_name"] == "test2"
        assert metadata["stack_name"] == env.name
        assert metadata["uuid"] == con.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_update(client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_3.yml"
    rc_file = "rc_metadata_3.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test3", METADATA_SUBDIR, dc_file, rc_file)
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert isinstance(service.metadata["test2"]["name"], list)
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "test3")
        metadata = json.loads(metadata_str)
        assert metadata["metadata"] == service.metadata

    # Update user metadata

    launch_rancher_cli_from_file(
        client, METADATA_SUBDIR, env_name,
        "up --upgrade -d", "Updating",
        "dc_metadata_3.yml", "rc_metadata_31.yml")

    service = client.reload(service)
    assert service.state == "active"
    assert service.metadata["test1"]["name"] == "t2name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert isinstance(service.metadata["test2"]["name"], list)
    assert service.metadata["test2"]["name"] == [1, 2, 5]
    assert service.metadata["test3"]["name"] == "t3name"

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "test3")
        metadata = json.loads(metadata_str)
        assert metadata["metadata"] == service.metadata
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_scaleup(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_4.yml"
    rc_file = "rc_metadata_4.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test4", METADATA_SUBDIR, dc_file, rc_file)
    service_containers = get_service_container_list(client, service)
    assert len(service_containers) == 2
    wait_for_metadata_propagation(client)
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    for con in metadata_client_service:
        validate_service_container_list(client, con, "test4",
                                        con_metadata)

    # Scale up service

    launch_rancher_cli_from_file(
        client, METADATA_SUBDIR, env_name,
        "scale test4=3", "test4")
    service = client.wait_success(service, 60)
    assert service.state == "active"
    service_containers = get_service_container_list(client, service)
    assert len(service_containers) == 3
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        validate_service_container_list(client, con, "test4",
                                        con_metadata)
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_scaledown(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_5.yml"
    rc_file = "rc_metadata_5.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "test5", METADATA_SUBDIR, dc_file, rc_file)

    service_containers = get_service_container_list(client, service)
    assert len(service_containers) == 2
    wait_for_metadata_propagation(client)
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    for con in metadata_client_service:
        validate_service_container_list(client, con, "test5",
                                        con_metadata)

    # Scale down service

    launch_rancher_cli_from_file(
        client, METADATA_SUBDIR, env_name,
        "scale test5=1", "test5")

    service = client.wait_success(service, 60)
    assert service.state == "active"
    service_containers = get_service_container_list(client, service)
    assert len(service_containers) == 1
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        validate_service_container_list(client, con, "test5",
                                        con_metadata)
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_sidekick(client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_sk.yml"
    rc_file = "rc_metadata_sk.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "testsk", METADATA_SUBDIR, dc_file, rc_file)

    service_containers = get_service_container_list(client, service)
    con_names = []
    for con in service_containers:
        con_names.append(con.name)
    print con_names
    print metadata_client_service

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "testsk")
        metadata = json.loads(metadata_str)
        assert set(metadata["sidekicks"]) == set(["sk1", "sk2"])
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_links(client, rancher_cli_container):

    env_name1 = "testlink"
    dc_file = "dc_metadata_links_1.yml"

    # Create an environment using up
    linked_env, linked_service = create_stack_using_rancher_cli(
        client, env_name1, "testl1", METADATA_SUBDIR, dc_file)

    env_name2 = random_str().replace("-", "")
    dc_file = "dc_metadata_links_2.yml"

    env, service = create_stack_using_rancher_cli(
        client, env_name2, "testl2", METADATA_SUBDIR, dc_file)

    linked_services = {env_name1 + "/" + "testl1": "linkexttest",
                       env_name2 + "/" + "testl2": "linktest"}

    linked_env, linked_service = \
        get_env_service_by_name(client, env_name1, "testl1")

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "testl3")
        metadata = json.loads(metadata_str)
        print metadata["links"]
        assert metadata["links"] == linked_services
    delete_all(client, [env, linked_env])


@if_compose_data_files
def test_metadata_hostnet(client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_hostnet.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "testhostdns", METADATA_SUBDIR, dc_file)

    service_containers = get_service_container_list(client, service)
    assert len(service_containers) == service.scale
    port = 33

    wait_for_metadata_propagation(client)
    for con in service_containers:
        host = con.host()

        # Host related metadata
        metadata_str = fetch_rancher_metadata(client, con, port,
                                              "self/host")
        metadata = json.loads(metadata_str)
        assert metadata["agent_ip"] == host.ipAddresses()[0].address
        assert metadata["labels"] == host.labels
        assert metadata["name"] == host.hostname
        assert metadata["uuid"] == host.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_externalservice_ip(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_extservice_ip.yml"
    rc_file = "rc_metadata_extservice_ip.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "testextip", METADATA_SUBDIR, dc_file, rc_file)

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "testextip")
        metadata = json.loads(metadata_str)
        print metadata["external_ips"]
        assert set(metadata["external_ips"]) == set(["1.1.1.1", "2.2.2.2"])
        assert metadata["kind"] == "externalService"
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_externalservice_cname(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_extservice_cname.yml"
    rc_file = "rc_metadata_extservice_cname.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "testextcname", METADATA_SUBDIR, dc_file, rc_file)

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "testextcname")
        metadata = json.loads(metadata_str)
        print metadata["hostname"]
        assert metadata["hostname"] == "google.com"
        assert metadata["kind"] == "externalService"
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_lb(client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_lb.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "lb-1", METADATA_SUBDIR, dc_file)

    linked_services = {env_name + "/" + "web1": "web1",
                       env_name + "/" + "web2": "web2"}

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "lb-1")
        metadata = json.loads(metadata_str)
        assert metadata["links"] == linked_services
        assert metadata["kind"] == "loadBalancerService"

    delete_all(client, [env])


@if_compose_data_files
def test_metadata_lb_updatetarget(
        client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    dc_file = "dc_metadata_lb_1.yml"

    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "lb-2", METADATA_SUBDIR, dc_file)
    linked_services = {env_name + "/" + "web1": "web1",
                       env_name + "/" + "web2": "web2"}

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "lb-2")
        metadata = json.loads(metadata_str)
        assert metadata["links"] == linked_services
        assert metadata["kind"] == "loadBalancerService"

    # Add another target to existing LB service
    dc_file = "dc_metadata_lb_11.yml"

    """
    # Create an environment using up
    env, service = create_stack_using_rancher_cli(
        client, env_name, "lb-2", METADATA_SUBDIR, dc_file)
    """
    launch_rancher_cli_from_file(
        client, METADATA_SUBDIR, env_name,
        "up --upgrade -d", "Updating",
        "dc_metadata_lb_11.yml")

    linked_services = {env_name + "/" + "web1": "web1",
                       env_name + "/" + "web2": "web2",
                       env_name + "/" + "web3": "web3"}

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(client, con,
                                              metadata_client_port,
                                              "services/" + "lb-2")
        metadata = json.loads(metadata_str)
        assert metadata["links"] == linked_services
        assert metadata["kind"] == "loadBalancerService"

    delete_all(client, [env])


def get_env_service_by_name(client, env_name, service_name):
    env = client.list_stack(name=env_name, removed_null=True)
    assert len(env) == 1
    service = client.list_service(name=service_name,
                                  stackId=env[0].id,
                                  removed_null=True)
    assert len(service) == 1
    return env[0], service[0]


def fetch_rancher_metadata(client, con, port, command, version=None):

    host = con.host()
    if version is None:
        version = "latest"
    rancher_metadata_cmd = \
        "wget -O result.txt --header 'Accept: application/json' " + \
        "http://rancher-metadata/"+version+"/" + command + "; cat result.txt"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host.ipAddresses()[0].address,
                username="root",
                password="root",
                port=port)
    print rancher_metadata_cmd
    stdin, stdout, stderr = ssh.exec_command(rancher_metadata_cmd)
    response = stdout.readlines()
    assert len(response) > 0
    return response[0]


def validate_service_container_list(client, con, serviceName,
                                    con_metadata):
    metadata_str = fetch_rancher_metadata(client, con,
                                          metadata_client_port,
                                          "services/"+serviceName)
    metadata = json.loads(metadata_str)
    print metadata
    con_list = metadata["containers"]
    assert len(con_list) == len(con_metadata.keys())
    for con in con_list:
        print con
        print con_metadata[con["name"]]
        assert cmp(con, con_metadata[con["name"]]) == 0
