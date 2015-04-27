from common_fixtures import *  # NOQA
from docker import Client
import websocket as ws
from test_container import assert_execute, assert_stats, assert_ip_inject

CONTAINER_APPEAR_TIMEOUT_MSG = 'Timed out waiting for container ' \
                               'to appear. Name: [%s].'

NATIVE_TEST_IMAGE = 'cattle/test-agent'

socat_test_image = os.environ.get('CATTLE_CLUSTER_SOCAT_IMAGE',
                                  'docker:sonchang/socat-test')


@pytest.fixture(scope='module')
def docker_client(client, unmanaged_network, request):
    # When these tests run in the CI environment, the hosts don't expose the
    # docker daemon over tcp, so we need to create a container that binds to
    # the docker socket and exposes it on a port
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) >= 1
    host = hosts[0]
    socat_container = client.create_container(
        name='socat-%s' % random_str(),
        networkIds=[unmanaged_network.id],
        imageUuid=socat_test_image,
        ports='2375',
        stdinOpen=False,
        tty=False,
        publishAllPorts=True,
        dataVolumes='/var/run/docker.sock:/var/run/docker.sock',
        requestedHostId=host.id)

    def remove_socat():
        client.delete(socat_container)

    request.addfinalizer(remove_socat)

    wait_for_condition(
        client, socat_container,
        lambda x: x.state == 'running',
        lambda x: 'State is: ' + x.state)

    socat_container = client.reload(socat_container)
    ip = host.ipAddresses()[0].address
    port = socat_container.ports()[0].publicPort

    params = {}
    params['base_url'] = 'tcp://%s:%s' % (ip, port)
    api_version = os.getenv('DOCKER_API_VERSION', '1.15')
    params['version'] = api_version

    return Client(**params)


@pytest.fixture(scope='module')
def pull_images(docker_client):
    image = (NATIVE_TEST_IMAGE, 'latest')
    images = docker_client.images(image[0])
    if not images:
        docker_client.pull(image[0], image[1])


@pytest.fixture(scope='module', autouse=True)
def native_cleanup(client, request):
    def fin():
        containers = client.list_container()
        for c in containers:
            try:
                if c.name.startswith('native-'):
                    client.delete(c)
            except:
                # Tried our best
                pass

    request.addfinalizer(fin)


@pytest.fixture()
def native_name(random_str):
    return 'native-' + random_str


def test_native_unmanaged_network(docker_client, client, native_name,
                                  pull_images):
    d_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                 name=native_name)
    docker_client.start(d_container)
    inspect = docker_client.inspect_container(d_container)

    container = wait_on_rancher_container(client, native_name)

    assert container.externalId == d_container['Id']
    assert container.state == 'running'
    assert container.primaryIpAddress == inspect['NetworkSettings'][
        'IPAddress']


def test_native_managed_network(docker_client, client, native_name,
                                pull_images):
    d_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         environment=['RANCHER_NETWORK=true'])
    docker_client.start(d_container)
    inspect = docker_client.inspect_container(d_container)

    container = wait_on_rancher_container(client, native_name,
                                          timeout=180)

    assert container.externalId == d_container['Id']
    assert container.state == 'running'
    assert container.primaryIpAddress != inspect['NetworkSettings'][
        'IPAddress']

    # Let's test more of the life cycle
    container = client.wait_success(container.stop(timeout=0))
    assert container.state == 'stopped'

    container = client.wait_success(container.start(timeout=0))
    assert container.state == 'running'

    container = client.wait_success(container.restart(timeout=0))
    assert container.state == 'running'

    container = client.wait_success(container.stop(timeout=0))
    assert container.state == 'stopped'

    container = client.wait_success(container.remove(timeout=0))
    assert container.state == 'removed'

    container = client.wait_success(container.purge(timeout=0))
    assert container.state == 'purged'


def test_native_not_started(docker_client, client, native_name, pull_images):
    d_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE, name=native_name,
                         environment=['RANCHER_NETWORK=true'])

    container = wait_on_rancher_container(client, native_name)
    inspect = docker_client.inspect_container(d_container)

    c_id = container.id
    assert container.externalId == d_container['Id']
    assert container.state == 'running'

    def stopped_check():
        c = client.by_id_container(c_id)
        return c.state == 'stopped'

    wait_for(stopped_check,
             'Timeout waiting for container to stop. Id: [%s]' % c_id)

    assert container.primaryIpAddress != inspect['NetworkSettings'][
        'IPAddress']


def test_native_removed(docker_client, client, native_name, pull_images):
    d_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                 name=native_name)
    docker_client.remove_container(d_container)
    container = wait_on_rancher_container(client, native_name)

    assert container.externalId == d_container['Id']


def test_native_volumes(docker_client, client, native_name, pull_images):
    d_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                 name=native_name,
                                                 volumes=['/foo',
                                                          '/host/var'])
    docker_client.start(d_container,
                        binds={'/var': {'bind': '/host/var'}})

    container = wait_on_rancher_container(client, native_name)

    assert container.externalId == d_container['Id']
    assert container.state == 'running'
    mounts = container.mounts()
    assert len(mounts) == 2

    mount = mounts[0]
    assert mount.path == '/foo'
    volume = mount.volume()
    assert not volume.isHostPath

    mount = mounts[1]
    assert mount.path == '/host/var'
    volume = mount.volume()
    assert volume.isHostPath
    assert volume.uri == 'file:///var'


def test_native_logs(client, docker_client, native_name, pull_images):
    image = TEST_IMAGE_UUID.replace('docker:', '')
    test_msg = 'LOGS_WORK'
    d_container = docker_client. \
        create_container(image,
                         name=native_name,
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash', '-c', 'echo ' + test_msg])
    docker_client.start(d_container)
    container = wait_on_rancher_container(client, native_name)

    found_msg = search_logs(container, test_msg)
    assert found_msg


def test_native_exec(client, docker_client, native_name, pull_images):
    test_msg = 'EXEC_WORKS'
    d_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash'])
    docker_client.start(d_container)
    container = wait_on_rancher_container(client, native_name)

    assert_execute(container, test_msg)


def test_native_ip_inject(client, docker_client, native_name,
                          pull_images):
    d_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         environment=['RANCHER_NETWORK=true'],
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash', '-c', 'sleep 10; '
                                                     'ip addr show eth0'])
    docker_client.start(d_container)
    container = wait_on_rancher_container(client, native_name)

    assert_ip_inject(container)


def test_native_container_stats(client, docker_client, native_name,
                                pull_images):
    d_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash'])
    docker_client.start(d_container)
    container = wait_on_rancher_container(client, native_name)

    assert_stats(container)


def search_logs(container, test_msg):
    logs = container.logs()
    conn = ws.create_connection(logs.url + '?token=' + logs.token, timeout=10)
    count = 0
    found_msg = False
    while count <= 100:
        count += 1
        try:
            result = conn.recv()
            if test_msg in result:
                found_msg = True
                break
        except ws.WebSocketConnectionClosedException:
            break
    return found_msg


def wait_on_rancher_container(client, name, timeout=None):
    def check():
        containers = client.list_container(name=name)
        return len(containers) > 0

    wait_for(check, timeout_message=CONTAINER_APPEAR_TIMEOUT_MSG % name)
    r_containers = client.list_container(name=name)
    assert len(r_containers) == 1
    container = r_containers[0]

    kwargs = {}
    if timeout:
        kwargs['timeout'] = timeout
    container = client.wait_success(container, **kwargs)
    return container
