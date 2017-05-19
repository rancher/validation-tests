from common_fixtures import *  # NOQA
import requests
import websocket as ws
import base64


def test_sibling_pinging(client, one_per_host):
    instances = one_per_host
    hosts = {}
    hostnames = set()

    for i in instances:
        port = i.ports_link()[0]

        host = port.publicIpAddress().address
        port = port.publicPort
        base_url = 'http://{}:{}'.format(host, port)
        pong = requests.get(base_url + '/ping').text
        hostname = requests.get(base_url + '/hostname').text

        assert pong == 'pong'
        assert hostname not in hostnames

        hostnames.add(hostname)
        hosts[hostname] = base_url

    count = 0
    for hostname, base_url in hosts.items():
        url = base_url + '/get'
        for other_hostname, other_url in hosts.items():
            if other_hostname == hostname:
                continue

            test_hostname = requests.get(url, params={
                'url': other_url + '/hostname'
            }).text

            count += 1
            assert other_hostname == test_hostname

    assert count == len(instances) * (len(instances) - 1)
    delete_all(client, instances)


def test_dynamic_port(client, test_name):
    c = client.create_container(name=test_name,
                                networkMode=MANAGED_NETWORK,
                                imageUuid=TEST_IMAGE_UUID)
    c = client.wait_success(c)

    ports = c.ports_link()
    assert len(ports) == 1

    port = ports[0]

    assert port.publicPort is None

    port = client.wait_success(client.update(port, publicPort=3001))

    assert port.publicPort == 3001
    ping_port(port)

    port = client.wait_success(client.update(port, publicPort=3002))

    assert port.publicPort == 3002
    ping_port(port)

    delete_all(client, [c])


def test_linking(admin_client, client, test_name):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 2

    random_val = random_str()
    random_val2 = random_str()

    link_server = client.create_container(name=test_name + '-server',
                                          imageUuid=TEST_IMAGE_UUID,
                                          networkMode=MANAGED_NETWORK,
                                          hostname=test_name + '-server',
                                          environment={
                                              'VALUE': random_val
                                          },
                                          requestedHostId=hosts[2].id)
    link_server2 = client.create_container(name=test_name + '-server2',
                                           imageUuid=TEST_IMAGE_UUID,
                                           networkMode=MANAGED_NETWORK,
                                           hostname=test_name + '-server2',
                                           environment={
                                               'VALUE': random_val2
                                           },
                                           requestedHostId=hosts[1].id)
    link_client = client.create_container(name=test_name + '-client',
                                          imageUuid=TEST_IMAGE_UUID,
                                          networkMode=MANAGED_NETWORK,
                                          ports=['3000:3000'],
                                          hostname=test_name + '-client1',
                                          instanceLinks={
                                              'client': link_server.id
                                          },
                                          requestedHostId=hosts[0].id)

    link_client = client.wait_success(link_client)
    link_client = admin_client.reload(link_client)
    link_server = client.wait_success(link_server)
    link_server = admin_client.reload(link_server)

    ping_link(link_client, 'client', var='VALUE', value=random_val)

    link_server2 = client.wait_success(link_server2)

    link = link_client.instanceLinks()[0]
    link = client.update(link, targetInstanceId=link_server2.id)
    client.wait_success(link)

    ping_link(link_client, 'client', var='VALUE', value=random_val2)

    delete_all(client, [link_client, link_server, link_server2])


def test_ip_inject(client, test_name):
    cleanup_items = []
    try:
        cmd = ['/bin/bash', '-c', 'sleep 5; ip addr show eth0']
        container = client.create_container(name=test_name,
                                            imageUuid=TEST_IMAGE_UUID,
                                            networkMode=MANAGED_NETWORK,
                                            command=cmd)
        cleanup_items.append(container)
        container = client.wait_success(container)

        assert_ip_inject(container)
    finally:
        delete_all(client, cleanup_items)


def assert_ip_inject(container):
    ip = container.primaryIpAddress
    logs = container.logs()
    conn = ws.create_connection(logs.url + '?token=' + logs.token)
    count = 0
    found_ip = False
    while count <= 100:
        count += 1
        try:
            result = conn.recv()
            if ip in result:
                found_ip = True
                break
        except ws.WebSocketConnectionClosedException:
            break
    assert found_ip


def test_container_execute(client, test_name):
    cleanup_items = []
    try:
        container = client.create_container(name=test_name,
                                            imageUuid=TEST_IMAGE_UUID,
                                            networkMode=MANAGED_NETWORK,
                                            attachStdin=True,
                                            attachStdout=True,
                                            tty=True,
                                            command='/bin/bash')
        cleanup_items.append(container)
        container = client.wait_success(container)
        test_msg = 'EXEC_WORKS'
        assert_execute(container, test_msg)
    finally:
        delete_all(client, cleanup_items)


def assert_execute(container, test_msg):
    execute = container.execute(attachStdin=True,
                                attachStdout=True,
                                command=['/bin/bash', '-c',
                                         'echo ' + test_msg],
                                tty=True)
    conn = ws.create_connection(execute.url + '?token=' + execute.token,
                                timeout=10)

    # Python is weird about closures
    closure_wrapper = {
        'result': ''
    }

    def exec_check():
        msg = conn.recv()
        closure_wrapper['result'] += base64.b64decode(msg)
        return test_msg == closure_wrapper['result'].rstrip()

    wait_for(exec_check,
             'Timeout waiting for exec msg %s' % test_msg)


def test_container_stats(client, test_name):
    cleanup_items = []
    try:
        container = client.create_container(name=test_name,
                                            imageUuid=TEST_IMAGE_UUID,
                                            networkMode=MANAGED_NETWORK,
                                            attachStdin=True,
                                            attachStdout=True,
                                            tty=True,
                                            command='/bin/bash')
        cleanup_items.append(container)
        container = client.wait_success(container)

        assert_stats(container)
    finally:
        delete_all(client, cleanup_items)


def assert_stats(container):
    stats = container.stats()
    conn = ws.create_connection(stats.url + '?token=' + stats.token,
                                timeout=10)
    result = conn.recv()
    assert 'per_cpu_usage' in result
