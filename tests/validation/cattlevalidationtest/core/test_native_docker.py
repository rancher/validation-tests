from docker.utils import create_host_config
from common_fixtures import *  # NOQA
import websocket as ws
from test_container import assert_execute, assert_stats, assert_ip_inject
from cattle import from_env

CONTAINER_APPEAR_TIMEOUT_MSG = 'Timed out waiting for container ' \
                               'to appear. Name: [%s].'
NATIVE_TEST_IMAGE = 'cattle/test-agent'
SP_CREATE = "storagepool.create"


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
def native_name():
    return 'native-' + random_str()


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
                         command=['/bin/bash', '-c', 'sleep 10; '
                                                     'ip addr show eth0'])
    rancher_container, _ = start_and_wait(client, docker_container,
                                          docker_client, native_name)

    assert_ip_inject(rancher_container)


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
        return len(containers) > 0

    wait_for(check, timeout_message=CONTAINER_APPEAR_TIMEOUT_MSG % name)
    r_containers = client.list_container(name=name)
    assert len(r_containers) == 1
    container = r_containers[0]

    kwargs = {}
    if timeout:
        kwargs['timeout'] = timeout
    wait_for_state(client, 'running', container.id)
    container = client.reload(container)
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
                                                      mem_limit='4MB',
                                                      memswap_limit='8MB',
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

    docker_client.start(docker_container)

    def check():
        containers = client.list_container(name=name)
        return len(containers) > 0

    wait_for(check, timeout_message=CONTAINER_APPEAR_TIMEOUT_MSG % name)

    r_containers = client.list_container(name=name)
    assert len(r_containers) == 1
    rancher_container = r_containers[0]
    rancher_container = client.wait_success(rancher_container)
    assert rancher_container.hostname == 'hostname1'
    assert rancher_container.domainName == 'domainname1'
    assert rancher_container.user == 'root'
    assert rancher_container.memory == 4194304
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


def create_agent(client, docker_client, base_name):
    agent_name = 'agent-%s' % base_name
    client.create_container(name=agent_name,
                            imageUuid='docker:alpine',
                            command='sh', tty=True, stdinOpen=True,
                            labels={'io.rancher.container.'
                                    'create_agent': 'true'})
    agent_con = wait_on_rancher_container(client, agent_name)
    ac = docker_client.inspect_container(agent_con.externalId)
    assert ac is not None
    for e in ac['Config']['Env']:
        if e.startswith('CATTLE_ACCESS_KEY'):
            access_key = e.split('=')[1]
        elif e.startswith('CATTLE_SECRET_KEY'):
            secret_key = e.split('=')[1]

    agent_cli = from_env(url=cattle_url(), cache=False, access_key=access_key,
                         secret_key=secret_key)
    hosts = agent_con.hosts()
    return agent_cli, hosts[0]


def create_storage_pool(client, agent_client, driver_name, host_uuids):
    event = agent_client.create_external_storage_pool_event(
        eventType=SP_CREATE,
        hostUuids=host_uuids,
        externalId=driver_name,
        storagePool={
            'name': driver_name,
            'driverName': driver_name,
        })
    assert event is not None
    storage_pool = wait_for(lambda: sp_wait(client, driver_name))
    return storage_pool


def sp_wait(client, driver_name):
    storage_pools = client.list_storage_pool(driverName=driver_name)
    if len(storage_pools) and storage_pools[0].state == 'active':
        return storage_pools[0]


def test_native_convoy_volume(socat_containers, client, pull_images):
    # Faster way to run locally:
    # def test_native_convoy_volume(client):
    #   kwargs = kwargs_from_env(assert_hostname=False)
    #   kwargs['version'] = '1.21'
    #   docker_client = Client(**kwargs)  # get_docker_client(host(client))
    docker_client = get_docker_client(host(client), '1.21')

    driver = 'convoy%s' % random_num()
    agent_cli, h = create_agent(client, docker_client, driver)

    create_storage_pool(client, agent_cli, driver, [h.uuid])

    container = client. \
        create_container(name=native_name(),
                         privileged=True,
                         imageUuid='docker:cjellick/convoy-local:v0.1.0',
                         environment={
                             'CONVOY_SOCKET': '/var/run/%s.sock' % driver,
                             'CONVOY_DATA_DIR': '/tmp/%s' % driver,
                             'CONVOY_DRIVER_NAME': '%s' % driver},
                         dataVolumes=['/var/run/:/var/run/',
                                      '/etc/docker/plugins/:'
                                      '/etc/docker/plugins',
                                      '/tmp/%s:/tmp/%s' % (driver, driver)])

    client.wait_success(container)
    vol_name = 'vol-1-%s' % driver
    vol = docker_client.create_volume(name=vol_name, driver=driver)
    assert vol is not None
    name = 'native-c1-%s' % driver
    host_vol = '/tmp/%s' % random_str()
    container = docker_client.create_container('busybox', name=name,
                                               command='sh',
                                               stdin_open=True, tty=True,
                                               volumes=[
                                                   '/bar',
                                                   '/bang',
                                                   '/tmp2'],
                                               host_config=create_host_config(
                                                   binds=['%s:/bar' % vol_name,
                                                          '%s:'
                                                          '/tmp2' % host_vol]))
    docker_client.start(container)
    rc = wait_on_rancher_container(client, name)
    assert rc.externalId == container['Id']
    assert rc.state == 'running'
    vol = docker_client.inspect_volume(vol_name)

    mounts = rc.mounts()
    assert len(mounts) == 3
    for m in mounts:
        volume = m.volume()
        sp = volume.storagePools()[0]
        if m.path == '/bar':
            share_vol = volume
            assert volume.driver == driver
            assert volume.uri == '%s://%s' % (driver, vol['Mountpoint'])
            assert volume.externalId == vol_name
            assert volume.name == vol_name
            assert volume.isHostPath is False
            assert sp.driverName == driver
        if m.path == '/bang':
            assert volume.driver == 'local'
            assert volume.uri.startswith('file://')
            assert volume.name is not None  # Is a long random string
            assert volume.externalId == volume.name
            assert volume.isHostPath is False
            assert sp.driverName is None
        if m.path == '/tmp2':
            assert volume.driver is None
            assert volume.uri == 'file://%s' % host_vol
            assert volume.externalId is None
            assert volume.isHostPath is True
            assert volume.name == host_vol
            assert sp.driverName is None

    # Create a second container with same shared volume and cofirm they use
    # the same one
    name = 'native-c2-%s' % driver
    container = docker_client.create_container('busybox', name=name,
                                               command='sh',
                                               stdin_open=True, tty=True,
                                               volumes=['/bar2'],
                                               host_config=create_host_config(
                                                   binds=[
                                                       '%s:/bar2' % vol_name]))
    docker_client.start(container)
    rc2 = wait_on_rancher_container(client, name)
    mounts = rc2.mounts()
    assert len(mounts) == 1
    m = mounts[0]
    assert m.path == '/bar2'
    vol = m.volume()
    assert vol.id == share_vol.id
