from docker.utils import create_host_config
from common_fixtures import *  # NOQA
import websocket as ws
from test_container import assert_execute, assert_stats, assert_ip_inject

CONTAINER_APPEAR_TIMEOUT_MSG = 'Timed out waiting for container ' \
                               'to appear. Name: [%s].'

NATIVE_TEST_IMAGE = 'cattle/test-agent'

VOLUME_CLEANUP_LABEL = 'io.rancher.container.volume_cleanup_strategy'


@pytest.fixture(scope='module')
def host(client):
    hosts = client.list_host(kind='docker', removed_null=True, state='active')
    assert len(hosts) >= 1
    host = hosts[0]
    return host


@pytest.fixture(scope='module')
def pull_images(client, socat_containers):
    docker_client = get_docker_client(host(client))
    images = [(NATIVE_TEST_IMAGE, 'latest'), ('busybox', 'latest')]
    for image in images:
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


def test_native_net_blank(socat_containers, client, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    docker_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                      name=native_name)
    rancher_container, docker_container = start_and_wait(client,
                                                         docker_container,
                                                         docker_client,
                                                         native_name)
    common_network_asserts(rancher_container, docker_container, 'bridge')


def test_native_net_bridge(socat_containers, client, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    host_config = create_host_config(network_mode='bridge')
    docker_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                      name=native_name,
                                                      host_config=host_config)
    rancher_container, docker_container = start_and_wait(client,
                                                         docker_container,
                                                         docker_client,
                                                         native_name)
    common_network_asserts(rancher_container, docker_container, 'bridge')


def test_native_net_host(socat_containers, client, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    host_config = create_host_config(network_mode='host')
    docker_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                      name=native_name,
                                                      host_config=host_config)
    rancher_container, docker_container = start_and_wait(client,
                                                         docker_container,
                                                         docker_client,
                                                         native_name)
    common_network_asserts(rancher_container, docker_container, 'host')


def test_native_net_container(socat_containers, client, native_name,
                              pull_images):
    docker_client = get_docker_client(host(client))
    target_name = 'target-%s' % native_name
    target_docker_con = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                       name=target_name)
    target_container, target_docker_con = start_and_wait(client,
                                                         target_docker_con,
                                                         docker_client,
                                                         target_name)

    host_config = create_host_config(
        network_mode='container:%s' % target_name)
    docker_container = docker_client.create_container('busybox',
                                                      stdin_open=True,
                                                      tty=True,
                                                      name=native_name,
                                                      host_config=host_config)
    container, docker_container = start_and_wait(client, docker_container,
                                                 docker_client,
                                                 native_name)
    common_network_asserts(container, docker_container, 'container')
    assert container['networkContainerId'] == target_container.id


def test_native_lifecycyle(socat_containers, client, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    docker_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                      name=native_name)
    rancher_container, _ = start_and_wait(client, docker_container,
                                          docker_client,
                                          native_name)
    c_id = rancher_container.id
    assert rancher_container.state == 'running'

    docker_client.stop(docker_container)
    wait_for_state(client, 'stopped', c_id)

    docker_client.start(docker_container)
    wait_for_state(client, 'running', c_id)

    docker_client.kill(docker_container)
    wait_for_state(client, 'stopped', c_id)

    docker_client.start(docker_container)
    wait_for_state(client, 'running', c_id)

    docker_client.remove_container(docker_container, force=True)
    wait_for_state(client, 'removed', c_id)


def test_native_managed_network(socat_containers, client, native_name,
                                pull_images):
    docker_client = get_docker_client(host(client))
    docker_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         labels={'io.rancher.container.network': 'true'})
    container, docker_container = start_and_wait(client, docker_container,
                                                 docker_client,
                                                 native_name)

    assert container.externalId == docker_container['Id']
    assert container.state == 'running'
    assert container.primaryIpAddress != docker_container['NetworkSettings'][
        'IPAddress']
    assert container.networkMode == 'managed'


def wait_for_state(client, expected_state, c_id):
    def stopped_check():
        c = client.by_id_container(c_id)
        return c.state == expected_state

    wait_for(stopped_check,
             'Timeout waiting for container to stop. Id: [%s]' % c_id)


def test_native_volumes(socat_containers, client, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    docker_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         volumes=['/foo',
                                  '/host/var',
                                  '/host/tmpreadonly'])
    docker_client.start(docker_container,
                        binds={'/var': {'bind': '/host/var'},
                               '/tmp1': {'bind': '/host/tmpreadonly',
                                         'ro': True}})

    rancher_container = wait_on_rancher_container(client, native_name)

    assert rancher_container.externalId == docker_container['Id']
    assert rancher_container.state == 'running'
    mounts = rancher_container.mounts()
    assert len(mounts) == 3

    foo_mount, var_mount, tmp_mount = None, None, None
    for m in mounts:
        if m.path == '/foo':
            foo_mount = m
        elif m.path == '/host/var':
            var_mount = m
        elif m.path == '/host/tmpreadonly':
            tmp_mount = m

    assert foo_mount.path == '/foo'
    volume = foo_mount.volume()
    assert not volume.isHostPath

    assert var_mount.path == '/host/var'
    assert var_mount.permissions == 'rw'
    volume = var_mount.volume()
    assert volume.isHostPath
    assert volume.uri == 'file:///var'

    assert tmp_mount.path == '/host/tmpreadonly'
    assert tmp_mount.permissions == 'ro'
    volume = tmp_mount.volume()
    assert volume.isHostPath
    assert volume.uri == 'file:///tmp1'


def test_native_logs(client, socat_containers, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    test_msg = 'LOGS_WORK'
    docker_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash', '-c', 'echo ' + test_msg])
    rancher_container, _ = start_and_wait(client, docker_container,
                                          docker_client,
                                          native_name)

    found_msg = search_logs(rancher_container, test_msg)
    assert found_msg


def test_native_exec(client, socat_containers, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    test_msg = 'EXEC_WORKS'
    docker_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash'])
    rancher_container, _ = start_and_wait(client, docker_container,
                                          docker_client,
                                          native_name)

    assert_execute(rancher_container, test_msg)


def test_native_ip_inject(client, socat_containers, native_name,
                          pull_images):
    docker_client = get_docker_client(host(client))
    docker_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         labels={'io.rancher.container.network': 'true'},
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash', '-c', 'until $(ip addr show | '
                                                     'grep -q 10.42); '
                                                     'do sleep 1 && echo .; '
                                                     'done; ip addr show'])
    rancher_container, _ = start_and_wait(client, docker_container,
                                          docker_client, native_name)
    assert_ip_inject(client.reload(rancher_container))


def test_native_container_stats(client, socat_containers, native_name,
                                pull_images):
    docker_client = get_docker_client(host(client))
    docker_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash'])
    rancher_container, _ = start_and_wait(client, docker_container,
                                          docker_client,
                                          native_name)

    assert_stats(rancher_container)


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


def start_and_wait(client, docker_container, docker_client, native_name):
    docker_client.start(docker_container)
    docker_container = docker_client.inspect_container(docker_container)
    rancher_container = wait_on_rancher_container(client, native_name,
                                                  timeout=180)
    return rancher_container, docker_container


def common_network_asserts(rancher_container, docker_container,
                           expected_net_mode):
    assert rancher_container.externalId == docker_container['Id']
    assert rancher_container.state == 'running'
    assert rancher_container.primaryIpAddress == \
        docker_container['NetworkSettings']['IPAddress']

    assert rancher_container.networkMode == expected_net_mode


def wait_on_rancher_container(client, name, timeout=None):
    def check():
        containers = client.list_container(name=name)
        return len(containers) > 0 and containers[0].state != 'requested'

    wait_for(check, timeout_message=CONTAINER_APPEAR_TIMEOUT_MSG % name)
    r_containers = client.list_container(name=name)
    assert len(r_containers) == 1
    container = r_containers[0]

    kwargs = {}
    if timeout:
        kwargs['timeout'] = timeout
    container = client.wait_success(container, **kwargs)
    return container


def test_native_fields(socat_containers, client, pull_images):
    docker_client = get_docker_client(host(client))
    name = 'native-%s' % random_str()

    host_config = create_host_config(
        privileged=True,
        publish_all_ports=True,
        dns=['1.2.3.4'], dns_search=['search.dns.com'],
        cap_add=['SYSLOG'], cap_drop=['KILL', 'LEASE'],
        restart_policy={'MaximumRetryCount': 5,
                        'Name': 'on-failure'},
        devices=['/dev/null:/dev/xnull:rw'])

    docker_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                      name=name,
                                                      hostname='hostname1',
                                                      domainname='domainname1',
                                                      user='root',
                                                      mem_limit='16MB',
                                                      memswap_limit='32MB',
                                                      cpu_shares=1024,
                                                      cpuset='0',
                                                      tty=True,
                                                      stdin_open=True,
                                                      working_dir='/root',
                                                      environment={
                                                          'FOO': 'BA'},
                                                      command=['-c',
                                                               'sleep 3'],
                                                      entrypoint=['/bin/sh'],
                                                      host_config=host_config)

    rancher_container, _ = start_and_wait(client, docker_container,
                                          docker_client, name)
    assert rancher_container.hostname == 'hostname1'
    assert rancher_container.domainName == 'domainname1'
    assert rancher_container.user == 'root'
    assert rancher_container.memory == 16777216
    assert rancher_container.cpuShares == 1024
    assert rancher_container.cpuSet == '0'
    assert rancher_container.tty is True
    assert rancher_container.stdinOpen is True
    assert rancher_container.imageUuid == 'docker:' + NATIVE_TEST_IMAGE
    assert rancher_container.workingDir == '/root'
    assert rancher_container.environment['FOO'] == 'BA'
    assert rancher_container.command == ['-c', 'sleep 3']
    assert rancher_container.entryPoint == ['/bin/sh']
    assert rancher_container.privileged is True
    assert rancher_container.publishAllPorts is True
    assert rancher_container.dns == ['1.2.3.4']
    assert rancher_container.dnsSearch == ['search.dns.com']
    assert rancher_container.capAdd == ['SYSLOG']
    assert rancher_container.capDrop == ['KILL', 'LEASE']
    assert rancher_container.restartPolicy == {'name': 'on-failure',
                                               'maximumRetryCount': 5}
    assert rancher_container.devices == ['/dev/null:/dev/xnull:rw']


def check_mounts(resource, count):
    mounts = [x for x in resource.mounts() if x.state != 'removed']
    assert len(mounts) == count
    return mounts


def volume_cleanup_setup(docker_client, rancher_client, con_name,
                         strategy=None):
    labels = {}
    if strategy:
        labels[VOLUME_CLEANUP_LABEL] = strategy

    vol_name = random_str()

    host_config = docker_client.create_host_config(
        binds=['%s:/namedvolpath' % vol_name])

    docker_container = \
        docker_client.create_container(NATIVE_TEST_IMAGE,
                                       name=con_name,
                                       volumes=['/namedvolpath',
                                                '/unnamedvolpath'],
                                       labels=labels, host_config=host_config)
    rancher_container, docker_container = start_and_wait(rancher_client,
                                                         docker_container,
                                                         docker_client,
                                                         con_name)

    if strategy:
        assert rancher_container.labels[VOLUME_CLEANUP_LABEL] == strategy

    mounts = check_mounts(rancher_container, 2)
    v1 = mounts[0].volume()
    v2 = mounts[1].volume()
    named_vol = v1 if v1.name == vol_name else v2
    unnamed_vol = v1 if v1.name != vol_name else v2
    named_vol = rancher_client.wait_success(named_vol)
    unnamed_vol = rancher_client.wait_success(unnamed_vol)
    assert named_vol.state == 'active'
    assert unnamed_vol.state == 'active'
    rancher_container = rancher_client.wait_success(
        rancher_container.stop(remove=True, timeout=0))
    rancher_container = rancher_client.wait_success(rancher_container.purge())
    check_mounts(rancher_container, 0)
    return rancher_container, named_vol, unnamed_vol


def test_native_cleanup_volume_strategy(client, socat_containers, pull_images):
    docker_client = get_docker_client(host(client))

    # With no cleanup strategy label, default strategy is 'none'
    c, named_vol, unnamed_vol = volume_cleanup_setup(docker_client, client,
                                                     native_name(random_str()))
    assert client.wait_success(named_vol).state == 'inactive'
    assert client.wait_success(unnamed_vol).state == 'inactive'

    # Unnamed strategy
    c, named_vol, unnamed_vol = volume_cleanup_setup(docker_client, client,
                                                     native_name(random_str()),
                                                     strategy='unnamed')
    assert client.wait_success(named_vol).state == 'inactive'
    assert client.wait_success(unnamed_vol).state == 'removed'

    # None strategy
    c, named_vol, unnamed_vol = volume_cleanup_setup(docker_client, client,
                                                     native_name(random_str()),
                                                     strategy='none')
    assert client.wait_success(named_vol).state == 'inactive'
    assert client.wait_success(unnamed_vol).state == 'inactive'

    # All strategy
    c, named_vol, unnamed_vol = volume_cleanup_setup(docker_client, client,
                                                     native_name(random_str()),
                                                     strategy='all')
    assert client.wait_success(named_vol).state == 'removed'
    assert client.wait_success(unnamed_vol).state == 'removed'
