from common_fixtures import *  # NOQA
import websocket as ws
from test_container import assert_execute, assert_stats, assert_ip_inject

CONTAINER_APPEAR_TIMEOUT_MSG = 'Timed out waiting for container ' \
                               'to appear. Name: [%s].'

NATIVE_TEST_IMAGE = 'cattle/test-agent'


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
    common_network_asserts(rancher_container, docker_container, 'default')


def test_native_net_bridge(socat_containers, client, native_name, pull_images):
    docker_client = get_docker_client(host(client))
    host_config = docker_client.create_host_config(network_mode='bridge')
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
    host_config = docker_client.create_host_config(network_mode='host')
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

    host_config = docker_client.create_host_config(
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
    config = docker_client.create_host_config(
                                binds={'/var': {'bind': '/host/var'},
                                       '/tmp1': {'bind': '/host/tmpreadonly',
                                                 'ro': True}})
    docker_container = docker_client. \
        create_container(NATIVE_TEST_IMAGE,
                         name=native_name,
                         volumes=['/foo',
                                  '/host/var',
                                  '/host/tmpreadonly'],
                         host_config=config)
    docker_client.start(docker_container)

    rancher_container = wait_on_rancher_container(client, native_name)

    assert rancher_container.externalId == docker_container['Id']
    assert rancher_container.state == 'running'
    mounts = rancher_container.mounts
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

    assert var_mount.path == '/host/var'
    assert var_mount.permission == 'rw'
    assert var_mount.volumeName == '/var'

    assert tmp_mount.path == '/host/tmpreadonly'
    assert tmp_mount.permission == 'ro'
    assert tmp_mount.volumeName == '/tmp1'


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
    if rancher_container.primaryIpAddress is None:
        ip_address = ""
    else:
        ip_address = rancher_container.primaryIpAddress
    assert ip_address == \
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

    host_config = docker_client.create_host_config(
        privileged=True,
        publish_all_ports=True,
        dns=['1.2.3.4'], dns_search=['search.dns.com'],
        cap_add=['SYSLOG'], cap_drop=['KILL', 'LEASE'],
        restart_policy={'MaximumRetryCount': 5,
                        'Name': 'on-failure'},
        devices=['/dev/null:/dev/xnull:rw'],
        mem_limit='16MB',
        memswap_limit='32MB')

    docker_container = docker_client.create_container(NATIVE_TEST_IMAGE,
                                                      name=name,
                                                      hostname='hostname1',
                                                      domainname='domainname1',
                                                      user='root',
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
    assert rancher_container.restartPolicy["name"] == u"on-failure"
    assert rancher_container.restartPolicy["maximumRetryCount"] == 5
    assert rancher_container.devices == ['/dev/null:/dev/xnull:rw']


def test_native_net_with_network_label_blank(client, socat_containers):
    validate_native_containers_with_network_label(client)


def test_native_net_with_network_label_bridge(client, socat_containers):
    validate_native_containers_with_network_label(client, "bridge")


def test_native_net_with_network_label_none(client, socat_containers):
    validate_native_containers_with_network_label(client, "none")


def test_native_net_with_network_label_host(client, socat_containers):
    validate_native_containers_with_network_label(client, "host")


def validate_native_containers_with_network_label(client, network_mode=None):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 1
    docker_client = get_docker_client(hosts[0])

    if network_mode is None:
        network_mode_str = "blank"
    else:
        network_mode_str = "blank"
    primary_con_name = "test-native-"+network_mode_str+"-label-"+random_str()

    if network_mode is not None:
        host_config = docker_client.create_host_config(
            network_mode=network_mode)
        docker_container = docker_client.create_container(
            SSH_IMAGE_UUID_HOSTNET[7:],
            name=primary_con_name,
            labels={'io.rancher.container.network': 'true'},
            host_config=host_config)
    else:
        docker_container = docker_client.create_container(
            SSH_IMAGE_UUID_HOSTNET[7:],
            name=primary_con_name,
            labels={'io.rancher.container.network': 'true'})
    primary_container, docker_container = start_and_wait(client,
                                                         docker_container,
                                                         docker_client,
                                                         primary_con_name)

    sec_con_name = "test-native-side-"+network_mode_str+"-label-"+random_str()
    host_config = docker_client.create_host_config(
        network_mode='container:'+primary_con_name)
    docker_container = docker_client.create_container(
        WEB_IMAGE_UUID[7:],
        name=sec_con_name,
        labels={'io.rancher.container.network': 'true'},
        host_config=host_config
        )
    sidekick_container, docker_container = start_and_wait(client,
                                                          docker_container,
                                                          docker_client,
                                                          sec_con_name)
    if network_mode is None:
        network_mode = "default"
    validate_container_network_settings_for_native_containers(
        client,
        primary_container,
        sidekick_container,
        network_mode)
    delete_all(client, [primary_container, sidekick_container])
