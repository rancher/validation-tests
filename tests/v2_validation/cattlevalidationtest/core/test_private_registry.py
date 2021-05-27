from common_fixtures import *  # NOQA

quay_creds = {}
quay_creds["email"] = os.environ.get('QUAY_EMAIL')
quay_creds["username"] = os.environ.get('QUAY_USERNAME')
quay_creds["password"] = os.environ.get('QUAY_PASSWORD')
quay_creds["image"] = os.environ.get('QUAY_IMAGE')
quay_creds["serverAddress"] = "quay.io"
quay_creds["name"] = "quay"

dockerhub_creds = {}
dockerhub_creds["email"] = os.environ.get('DOCKERHUB_EMAIL')
dockerhub_creds["username"] = os.environ.get('DOCKERHUB_USERNAME')
dockerhub_creds["password"] = os.environ.get('DOCKERHUB_PASSWORD')
dockerhub_creds["image"] = os.environ.get('DOCKERHUB_IMAGE')
dockerhub_creds["serverAddress"] = "index.docker.io"
dockerhub_creds["name"] = "docker"

registry_list = {}

parallelThreads = os.environ.get("CATTLE_TEST_PARALLEL_THREADS")
multiThreaded = parallelThreads is not None and parallelThreads > 1

if_quay_creds_available = pytest.mark.skipif(
    None in quay_creds.values() or "" in quay_creds.values() or multiThreaded,
    reason='Not all Quay credentials are available '
           'or tests are run in parallel')

if_docker_creds_available = pytest.mark.skipif(
    None in dockerhub_creds.values() or
    "" in dockerhub_creds.values() or
    multiThreaded, reason='Not all Docker credentials are avaialable' +
                          'or tests are run in parallel')

print(quay_creds.values())
print(dockerhub_creds.values())
print(None in quay_creds.values())
print("" in dockerhub_creds.values())


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


@pytest.fixture(scope='session')
def registries(client, admin_client, request):

    if len(registry_list.keys()) > 0:
        return

    reg_cred = create_registry(client, quay_creds)
    registry_list[quay_creds["name"]] = reg_cred
    reg_cred = create_registry(client, dockerhub_creds)
    registry_list[dockerhub_creds["name"]] = reg_cred

    def remove_registries():
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

    request.addfinalizer(remove_registries)


@if_quay_creds_available
def test_create_container_with_quay_registry_credential(client,
                                                        socat_containers,
                                                        registries):
    image_id = quay_creds["serverAddress"]+"/" + quay_creds["image"]
    cleanup_images(client, [image_id+":latest"])

    image_id = "docker:"+quay_creds["serverAddress"]+"/" + quay_creds["image"]
    reg_cred = registry_list[quay_creds["name"]]
    container = client.create_container(name=random_str(),
                                        imageUuid=image_id,
                                        registryCredentialId=reg_cred.id)
    container = client.wait_success(container, 180)
    assert container.state == "running"
    delete_all(client, [container])


@if_quay_creds_available
def test_create_services_with_quay_registry_credential(client, admin_client,
                                                       socat_containers,
                                                       registries):
    image_id = quay_creds["serverAddress"]+"/" + quay_creds["image"]
    cleanup_images(client, [image_id+":latest"]),
    launch_config = {"imageUuid": "docker:"+image_id}

    scale = 2

    service, env = create_env_and_svc(client, launch_config,
                                      scale)
    # Activate Services
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(admin_client, service)
    delete_all(client, [env])


@if_docker_creds_available
def test_create_container_with_docker_registry_credential(client,
                                                          socat_containers,
                                                          registries):

    image_id = dockerhub_creds["image"]
    cleanup_images(client, [image_id+":latest"])

    reg_cred = registry_list[dockerhub_creds["name"]]
    container = client.create_container(name=random_str(),
                                        imageUuid="docker:"+image_id,
                                        registryCredentialId=reg_cred.id,
                                        stdinOpen=True,
                                        tty=True)
    container = client.wait_success(container, 180)
    assert container.state == "running"
    delete_all(client, [container])


@if_docker_creds_available
def test_create_services_with_docker_registry_credential(client, admin_client,
                                                         socat_containers,
                                                         registries):

    image_id = dockerhub_creds["image"]
    cleanup_images(client, [image_id+":latest"])

    launch_config = {"imageUuid": "docker:"+image_id,
                     "stdinOpen": "True",
                     "tty": "True"}

    scale = 2

    service, env = create_env_and_svc(client, launch_config,
                                      scale)
    # Activate Services
    service = service.activate()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    check_container_in_service(admin_client, service)

    delete_all(client, [env])


@if_quay_creds_available
def test_create_container_with_quay(client, socat_containers,
                                    registries):
    image_id = quay_creds["serverAddress"]+"/" + quay_creds["image"]
    cleanup_images(client, [image_id+":latest"])

    image_id = "docker:"+quay_creds["serverAddress"]+"/" + quay_creds["image"]
    container = client.create_container(name=random_str(),
                                        imageUuid=image_id)
    container = client.wait_success(container, 180)
    assert container.state == "running"
    delete_all(client, [container])


@if_docker_creds_available
def test_create_container_with_docker(client, socat_containers,
                                      registries):
    image_id = dockerhub_creds["image"]
    cleanup_images(client, [image_id+":latest"])
    container = client.create_container(name=random_str(),
                                        imageUuid="docker:"+image_id,
                                        stdinOpen=True,
                                        tty=True)
    container = client.wait_success(container, 180)
    assert container.state == "running"
    delete_all(client, [container])
