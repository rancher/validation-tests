from common_fixtures import *  # NOQA
import json

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST
METADATA_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'resources/metadatadc')

logger = logging.getLogger(__name__)

if_compose_data_files = pytest.mark.skipif(
    not os.path.isdir(METADATA_SUBDIR),
    reason='Docker compose files directory location not set/ does not Exist')

metadata_client_service = []
metadata_client_port = 999


@pytest.fixture(scope='session', autouse=True)
def create_metadata_client_service(request, client, super_client):
    env = create_env(client)
    launch_config = {"imageUuid": SSH_IMAGE_UUID,
                     "ports": [str(metadata_client_port) + ":22/tcp"],
                     "labels": {"io.rancher.scheduler.global": "true"}}
    service = client.create_service(name="metadataclient",
                                    environmentId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service, 60)
    env = env.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"
    metadata_client_service.extend(
        get_service_container_list(super_client, service))

    def fin():
        delete_all(client, [service])
    request.addfinalizer(fin)


@if_compose_data_files
def test_metadata_self_2015_12_19(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_1n.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_1n.yml")

    env, service = get_env_service_by_name(client, env_name, "test1n")
    assert service.state == "active"
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]

    service_containers = get_service_container_list(super_client, service)
    port = 6001
    con_metadata = {}

    for con in service_containers:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    wait_for_metadata_propagation(super_client)
    for con in service_containers:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con, port,
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

        host = super_client.by_id('host', con.hosts[0].id)

        # Host related metadata
        metadata_str = fetch_rancher_metadata(super_client, con, port,
                                              "self/host", "2015-12-19")
        metadata = json.loads(metadata_str)
        assert metadata["agent_ip"] == host.ipAddresses()[0].address
        assert metadata["labels"] == host.labels
        assert metadata["name"] == host.hostname
        assert metadata["uuid"] == host.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(super_client, con, port,
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

        metadata_str = fetch_rancher_metadata(super_client, con, port,
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
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_2n.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_2n.yml")

    env, service = get_env_service_by_name(client, env_name, "test2n")
    assert service.state == "active"
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]
    service_containers = get_service_container_list(super_client, service)

    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    wait_for_metadata_propagation(super_client)
    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
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

        metadata_str = fetch_rancher_metadata(super_client, con,
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
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2015-12-19")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        host = super_client.by_id('host', con.hosts[0].id)
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
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_1.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_1.yml")

    env, service = get_env_service_by_name(client, env_name, "test")
    assert service.state == "active"
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]

    service_containers = get_service_container_list(super_client, service)
    port = 6000
    con_names = []
    for con in service_containers:
        con_names.append(con.name)
    wait_for_metadata_propagation(super_client)
    for con in service_containers:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con, port,
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

        host = super_client.by_id('host', con.hosts[0].id)

        # Host related metadata
        metadata_str = fetch_rancher_metadata(super_client, con, port,
                                              "self/host", "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["agent_ip"] == host.ipAddresses()[0].address
        assert metadata["labels"] == host.labels
        assert metadata["name"] == host.hostname
        assert metadata["uuid"] == host.uuid

        # Stack related metadata

        metadata_str = fetch_rancher_metadata(super_client, con, port,
                                              "self/stack", "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["environment_name"] == "Default"
        assert metadata["services"] == ["test"]
        assert metadata["name"] == env.name
        assert metadata["uuid"] == env.uuid

        # Container related metadata

        metadata_str = fetch_rancher_metadata(super_client, con, port,
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
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_2.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_2.yml")

    env, service = get_env_service_by_name(client, env_name, "test2")
    assert service.state == "active"
    print service.metadata
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]
    service_containers = get_service_container_list(super_client, service)
    con_names = []
    for con in service_containers:
        con_names.append(con.name)

    wait_for_metadata_propagation(super_client)
    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
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

        metadata_str = fetch_rancher_metadata(super_client, con,
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
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name,
                                              "2015-07-25")
        metadata = json.loads(metadata_str)
        assert metadata["create_index"] == con.createIndex
        host = super_client.by_id('host', con.hosts[0].id)
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
def test_metadata_update(super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")
    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_3.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_3.yml")

    env, service = get_env_service_by_name(client, env_name, "test3")
    assert service.state == "active"
    assert service.metadata["test1"]["name"] == "t1name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert isinstance(service.metadata["test2"]["name"], list)
    assert service.metadata["test2"]["name"] == [1, 2, 3, 4]

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "test3")
        metadata = json.loads(metadata_str)
        assert metadata["metadata"] == service.metadata

    # Update user metadata

    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_3.yml", env_name,
        "up --upgrade -d", "Updating", "rc_metadata_31.yml")

    service = client.reload(service)
    assert service.state == "active"
    assert service.metadata["test1"]["name"] == "t2name"
    assert service.metadata["test1"]["value"] == "t1value"
    assert isinstance(service.metadata["test2"]["name"], list)
    assert service.metadata["test2"]["name"] == [1, 2, 5]
    assert service.metadata["test3"]["name"] == "t3name"

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "test3")
        metadata = json.loads(metadata_str)
        assert metadata["metadata"] == service.metadata
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_scaleup(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")
    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_4.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_4.yml")

    env, service = get_env_service_by_name(client, env_name, "test4")
    assert service.state == "active"
    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == 2
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        validate_service_container_list(super_client, con, "test4",
                                        con_metadata)

    # Scale up service

    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_4.yml", env_name,
        "scale test4=3", "Setting scale", "rc_metadata_4.yml")

    service = client.reload(service)
    assert service.state == "active"
    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == 3
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        validate_service_container_list(super_client, con, "test4",
                                        con_metadata)
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_scaledown(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")
    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_5.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_5.yml")

    env, service = get_env_service_by_name(client, env_name, "test5")
    assert service.state == "active"
    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == 2
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        validate_service_container_list(super_client, con, "test5",
                                        con_metadata)

    # Scale down service

    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_5.yml", env_name,
        "scale test5=1", "Setting scale", "rc_metadata_5.yml")

    service = client.reload(service)
    assert service.state == "active"
    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == 1
    con_metadata = {}
    for con in service_containers:
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "containers/" + con.name)
        con_metadata[con.name] = json.loads(metadata_str)

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        validate_service_container_list(super_client, con, "test5",
                                        con_metadata)
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_sidekick(super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_sk.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_sk.yml")

    env, service = get_env_service_by_name(client, env_name, "testsk")
    assert service.state == "active"
    service_containers = get_service_container_list(super_client, service)
    con_names = []
    for con in service_containers:
        con_names.append(con.name)
    print con_names
    print metadata_client_service

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "testsk")
        metadata = json.loads(metadata_str)
        assert set(metadata["sidekicks"]) == set(["sk1", "sk2"])
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_links(super_client, client, rancher_compose_container):

    env_name1 = "testlink"

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_links_1.yml", env_name1,
        "up -d", "Creating stack")

    env_name2 = random_str().replace("-", "")

    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_links_2.yml", env_name2,
        "up -d", "Creating stack")

    linked_services = {env_name1 + "/" + "testl1": "linkexttest",
                       env_name2 + "/" + "testl2": "linktest"}

    linked_env, linked_service = \
        get_env_service_by_name(client, env_name1, "testl1")

    env, service = get_env_service_by_name(client, env_name2, "testl2")
    assert service.state == "active"
    env, service = get_env_service_by_name(client, env_name2, "testl3")
    assert service.state == "active"

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "testl3")
        metadata = json.loads(metadata_str)
        print metadata["links"]
        assert metadata["links"] == linked_services
    delete_all(client, [env, linked_env])


@if_compose_data_files
def test_metadata_hostnet(super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_hostnet.yml", env_name,
        "up -d", "Creating stack")

    env, service = get_env_service_by_name(client, env_name, "testhostdns")
    assert service.state == "active"

    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == service.scale
    port = 33

    wait_for_metadata_propagation(super_client)
    for con in service_containers:
        host = super_client.by_id('host', con.hosts[0].id)

        # Host related metadata
        metadata_str = fetch_rancher_metadata(super_client, con, port,
                                              "self/host")
        metadata = json.loads(metadata_str)
        assert metadata["agent_ip"] == host.ipAddresses()[0].address
        assert metadata["labels"] == host.labels
        assert metadata["name"] == host.hostname
        assert metadata["uuid"] == host.uuid
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_externalservice_ip(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_extservice_ip.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_extservice_ip.yml")

    env, service = get_env_service_by_name(client, env_name, "testextip")
    assert service.state == "active"
    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "testextip")
        metadata = json.loads(metadata_str)
        print metadata["external_ips"]
        assert set(metadata["external_ips"]) == set(["1.1.1.1", "2.2.2.2"])
        assert metadata["kind"] == "externalService"
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_externalservice_cname(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_extservice_cname.yml", env_name,
        "up -d", "Creating stack", "rc_metadata_extservice_cname.yml")

    env, service = get_env_service_by_name(client, env_name, "testextcname")
    assert service.state == "active"
    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "testextcname")
        metadata = json.loads(metadata_str)
        print metadata["hostname"]
        assert metadata["hostname"] == "google.com"
        assert metadata["kind"] == "externalService"
    delete_all(client, [env])


@if_compose_data_files
def test_metadata_lb(super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_lb.yml", env_name,
        "up -d", "Creating stack")

    linked_services = {env_name + "/" + "web1": "web1",
                       env_name + "/" + "web2": "web2"}

    env, service = get_env_service_by_name(client, env_name, "lb-1")
    assert service.state == "active"

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "lb-1")
        metadata = json.loads(metadata_str)
        assert metadata["links"] == linked_services
        assert metadata["kind"] == "loadBalancerService"

    delete_all(client, [env])


@if_compose_data_files
def test_metadata_lb_updatetarget(
        super_client, client, rancher_compose_container):

    env_name = random_str().replace("-", "")

    # Create an environment using up
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_lb_1.yml", env_name,
        "up -d", "Starting project")

    linked_services = {env_name + "/" + "web1": "web1",
                       env_name + "/" + "web2": "web2"}

    env, service = get_env_service_by_name(client, env_name, "lb-2")
    assert service.state == "active"

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "lb-2")
        metadata = json.loads(metadata_str)
        assert metadata["links"] == linked_services
        assert metadata["kind"] == "loadBalancerService"

    # Add another target to existing LB service
    launch_rancher_compose_from_file(
        client, METADATA_SUBDIR, "dc_metadata_lb_11.yml", env_name,
        "up -d", "Starting project")

    linked_services = {env_name + "/" + "web1": "web1",
                       env_name + "/" + "web2": "web2",
                       env_name + "/" + "web3": "web3"}

    service = client.reload(service)
    assert service.state == "active"

    assert len(metadata_client_service) == \
        len(client.list_host(kind='docker', removed_null=True))

    wait_for_metadata_propagation(super_client)
    for con in metadata_client_service:
        # Service related metadata
        metadata_str = fetch_rancher_metadata(super_client, con,
                                              metadata_client_port,
                                              "services/" + "lb-2")
        metadata = json.loads(metadata_str)
        assert metadata["links"] == linked_services
        assert metadata["kind"] == "loadBalancerService"

    delete_all(client, [env])


def get_env_service_by_name(client, env_name, service_name):
    env = client.list_environment(name=env_name, removed_null=True)
    assert len(env) == 1
    service = client.list_service(name=service_name,
                                  environmentId=env[0].id,
                                  removed_null=True)
    assert len(service) == 1
    return env[0], service[0]


def fetch_rancher_metadata(super_client, con, port, command, version=None):

    host = super_client.by_id('host', con.hosts[0].id)
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


def validate_service_container_list(super_client, con, serviceName,
                                    con_metadata):
    metadata_str = fetch_rancher_metadata(super_client, con,
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
