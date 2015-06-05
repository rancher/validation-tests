from common_fixtures import *  # NOQA
import websocket as ws
from test_container import assert_execute, assert_stats, assert_ip_inject

CONTAINER_APPEAR_TIMEOUT_MSG = 'Timed out waiting for container ' \
                               'to appear. Name: [%s].'

NATIVE_TEST_IMAGE = 'cattle/test-agent'


@pytest.fixture(scope='module')
def host(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) >= 1
    host = hosts[0]
    return host


@pytest.fixture(scope='module')
def pull_images(client, socat_containers):
    docker_client = get_docker_client(host(client))
    image = (NATIVE_TEST_IMAGE, 'latest')
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


def test_native_unmanaged_network(socat_containers, client, native_name,
                                  pull_images):
    docker_client = get_docker_client(host(client))
    d_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                 name=native_name)
    docker_client.start(d_container)
    inspect = docker_client.inspect_container(d_container)

    container = wait_on_rancher_container(client, native_name)

    assert container.externalId == d_container['Id']
    assert container.state == 'running'
    assert container.primaryIpAddress == inspect['NetworkSettings'][
        'IPAddress']


def test_native_lifecycyle(socat_containers, client,
                           native_name, pull_images):
    docker_client = get_docker_client(host(client))
    d_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                 name=native_name)
    docker_client.start(d_container)

    container = wait_on_rancher_container(client, native_name)
    c_id = container.id
    assert container.state == 'running'

    docker_client.stop(d_container)
    wait_for_state(client, 'stopped', c_id)

    docker_client.start(d_container)
    wait_for_state(client, 'running', c_id)

    docker_client.kill(d_container)
    wait_for_state(client, 'stopped', c_id)

    docker_client.start(d_container)
    wait_for_state(client, 'running', c_id)

    docker_client.remove_container(d_container, force=True)
    wait_for_state(client, 'removed', c_id)


def test_native_managed_network(socat_containers, client, native_name,
                                pull_images):
    docker_client = get_docker_client(host(client))
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


def wait_for_state(client, expected_state, c_id):
    def stopped_check():
        c = client.by_id_container(c_id)
        return c.state == expected_state

    wait_for(stopped_check,
             'Timeout waiting for container to stop. Id: [%s]' % c_id)


def test_native_volumes(socat_containers, client, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    d_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                 name=native_name,
                                                 volumes=['/foo',
                                                          '/host/var',
                                                          '/host/tmpreadonly'])
    docker_client.start(d_container,
                        binds={'/var': {'bind': '/host/var'},
                               '/tmp1': {'bind': '/host/tmpreadonly',
                                         'ro': True}})

    container = wait_on_rancher_container(client, native_name)

    assert container.externalId == d_container['Id']
    assert container.state == 'running'
    mounts = container.mounts()
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
    d_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         tty=True,
                         stdin_open=True,
                         detach=True,
                         command=['/bin/bash', '-c', 'echo ' + test_msg])
    docker_client.start(d_container)
    container = wait_on_rancher_container(client, native_name)

    found_msg = search_logs(container, test_msg)
    assert found_msg


def test_native_exec(client, socat_containers, native_name, pull_images):
    docker_client = get_docker_client(host(client))
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


def test_native_ip_inject(client, socat_containers, native_name,
                          pull_images):
    docker_client = get_docker_client(host(client))
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


def test_native_container_stats(client, socat_containers, native_name,
                                pull_images):
    docker_client = get_docker_client(host(client))
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


def test_native_fields(socat_containers, client, pull_images):
    docker_client = get_docker_client(host(client))
    name = 'native-%s' % random_str()
    d_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                 name=name,
                                                 hostname='hostname1',
                                                 domainname='domainname1',
                                                 user='root',
                                                 mem_limit='4m',
                                                 cpu_shares=1024,
                                                 cpuset='0',
                                                 tty=True,
                                                 stdin_open=True,
                                                 working_dir='/root',
                                                 environment={'FOO': 'BA'},
                                                 command=['-c', 'sleep 3'],
                                                 entrypoint=['/bin/sh'])

    docker_client.start(d_container, privileged=True,
                        publish_all_ports=True,
                        lxc_conf={'lxc.utsname': 'docker'},
                        dns=['1.2.3.4'], dns_search=['search.dns.com'],
                        cap_add=['SYSLOG'], cap_drop=['KILL', 'LEASE'],
                        restart_policy={'MaximumRetryCount': 5,
                                        'Name': 'on-failure'},
                        devices=['/dev/null:/dev/xnull:rw'])

    def check():
        containers = client.list_container(name=name)
        return len(containers) > 0

    wait_for(check, timeout_message=CONTAINER_APPEAR_TIMEOUT_MSG % name)

    r_containers = client.list_container(name=name)
    assert len(r_containers) == 1
    container = r_containers[0]
    container = client.wait_success(container)
    assert container.hostname == 'hostname1'
    assert container.domainName == 'domainname1'
    assert container.user == 'root'
    assert container.memory == 4194304
    assert container.cpuShares == 1024
    assert container.cpuSet == '0'
    assert container.tty is True
    assert container.stdinOpen is True
    assert container.imageUuid == 'docker:' + NATIVE_TEST_IMAGE
    assert container.workingDir == '/root'
    assert container.environment['FOO'] == 'BA'
    assert container.command == ['-c', 'sleep 3']
    assert container.entryPoint == ['/bin/sh']
    assert container.privileged is True
    assert container.publishAllPorts is True
    assert container.lxcConf == {'lxc.utsname': 'docker'}
    assert container.dns == ['1.2.3.4']
    assert container.dnsSearch == ['search.dns.com']
    assert container.capAdd == ['SYSLOG']
    assert container.capDrop == ['KILL', 'LEASE']
    assert container.restartPolicy == {'name': 'on-failure',
                                       'maximumRetryCount': 5}
    assert container.devices == ['/dev/null:/dev/xnull:rw']
