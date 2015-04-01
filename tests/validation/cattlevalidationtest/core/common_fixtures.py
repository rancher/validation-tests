from cattle import from_env
import pytest
import random
import requests
import os
import time
import logging
import paramiko
import inspect

log = logging.getLogger()

TEST_IMAGE_UUID = os.environ.get('CATTLE_TEST_AGENT_IMAGE',
                                 'docker:cattle/test-agent:v7')

SSH_HOST_IMAGE_UUID = os.environ.get('CATTLE_SSH_HOST_IMAGE',
                                     'docker:rancher/ssh-host-container:' +
                                     'v0.1.0')
DEFAULT_TIMEOUT = 45

PRIVATE_KEY_FILENAME = "/tmp/private_key_host_ssh"
HOST_SSH_TEST_ACCOUNT = "ranchertest"
HOST_SSH_PUBLIC_PORT = 2222


@pytest.fixture(scope='session')
def cattle_url():
    default_url = 'http://localhost:8080/v1/schemas'
    return os.environ.get('CATTLE_TEST_URL', default_url)


@pytest.fixture(autouse=True, scope='session')
def cleanup(client):
    to_delete = []
    for i in client.list_instance(state='running'):
        try:
            if i.name.startswith('test-'):
                to_delete.append(i)
        except AttributeError:
            pass

    delete_all(client, to_delete)


def _admin_client():
    return from_env(url=cattle_url(),
                           cache=False,
                           access_key='admin',
                           secret_key='adminpass')


def _client_for_user(name, accounts):
    return from_env(url=cattle_url(),
                           cache=False,
                           access_key=accounts[name][0],
                           secret_key=accounts[name][1])


def create_user(admin_client, user_name, kind=None):
    if kind is None:
        kind = user_name

    password = user_name + 'pass'
    account = create_type_by_uuid(admin_client, 'account', user_name,
                                  kind=user_name,
                                  name=user_name)

    active_cred = None
    for cred in account.credentials():
        if cred.kind == 'apiKey' and cred.publicValue == user_name \
                and cred.secretValue == password:
            active_cred = cred
            break

    if active_cred is None:
        active_cred = admin_client.create_api_key({
            'accountId': account.id,
            'publicValue': user_name,
            'secretValue': password
        })

    active_cred = wait_success(admin_client, active_cred)
    if active_cred.state != 'active':
        wait_success(admin_client, active_cred.activate())

    return [user_name, password, account]


def wait_success(client, obj, timeout=DEFAULT_TIMEOUT):
    return client.wait_success(obj, timeout=timeout)


def create_type_by_uuid(admin_client, type, uuid, activate=True, validate=True,
                        **kw):
    opts = dict(kw)
    opts['uuid'] = uuid

    objs = admin_client.list(type, uuid=uuid)
    obj = None
    if len(objs) == 0:
        obj = admin_client.create(type, **opts)
    else:
        obj = objs[0]

    obj = wait_success(admin_client, obj)
    if activate and obj.state == 'inactive':
        obj.activate()
        obj = wait_success(admin_client, obj)

    if validate:
        for k, v in opts.items():
            assert getattr(obj, k) == v

    return obj

@pytest.fixture(scope='session')
def accounts():
    result = {}
    admin_client = _admin_client()
    for user_name in ['admin', 'agent', 'user', 'agentRegister', 'test',
                      'readAdmin', 'token', 'superadmin', 'service']:
        result[user_name] = create_user(admin_client,
                                        user_name,
                                        kind=user_name)

    result['admin'] = create_user(admin_client, 'admin')
    system_account = admin_client.list_account(kind='system', uuid='system')[0]
    result['system'] = [None, None, system_account]

    return result


@pytest.fixture(scope='session')
def client(cattle_url):
    client = from_env(url=cattle_url)
    assert client.valid()
    return client


@pytest.fixture(scope='session')
def admin_client(cattle_url):
    admin_client = from_env(url=cattle_url)
    assert admin_client.valid()
    return admin_client

@pytest.fixture(scope='session')
def super_client(request, accounts):
    ret = _client_for_user('superadmin', accounts)
    return ret


@pytest.fixture
def test_name():
    return random_str()


@pytest.fixture
def random_str():
    return 'test-{0}'.format(random_num())


@pytest.fixture
def random_num():
    return random.randint(0, 1000000)


def wait_all_success(client, items, timeout=DEFAULT_TIMEOUT):
    result = []
    for item in items:
        item = client.wait_success(item, timeout=timeout)
        result.append(item)

    return result


@pytest.fixture
def managed_network(client):
    networks = client.list_network(uuid='managed-docker0')
    assert len(networks) == 1

    return networks[0]


@pytest.fixture
def unmanaged_network(client):
    networks = client.list_network(uuid='unmanaged')
    assert len(networks) == 1

    return networks[0]


@pytest.fixture
def one_per_host(client, test_name, managed_network):
    instances = []
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 2

    for host in hosts:
        c = client.create_container(name=test_name,
                                    ports=['3000:3000'],
                                    networkIds=managed_network.id,
                                    imageUuid=TEST_IMAGE_UUID,
                                    requestedHostId=host.id)
        instances.append(c)

    instances = wait_all_success(client, instances, timeout=120)

    for i in instances:
        ports = i.ports()
        assert len(ports) == 1
        port = ports[0]

        assert port.privatePort == 3000
        assert port.publicPort == 3000

        ping_port(port)

    return instances


def delete_all(client, items):
    wait_for = []
    for i in items:
        client.delete(i)
        wait_for.append(client.reload(i))

    wait_all_success(client, items)


def get_port_content(port, path, params={}):
    assert port.publicPort is not None
    assert port.publicIpAddressId is not None

    url = 'http://{}:{}/{}'.format(port.publicIpAddress().address,
                                   port.publicPort,
                                   path)

    e = None
    for i in range(60):
        try:
            return requests.get(url, params=params, timeout=5).text
        except Exception as e1:
            e = e1
            log.exception('Failed to call %s', url)
            time.sleep(1)
            pass

    if e is not None:
        raise e

    raise Exception('failed to call url {0} for port'.format(url))


def ping_port(port):
    pong = get_port_content(port, 'ping')
    assert pong == 'pong'


def ping_link(src, link_name, var=None, value=None):
    src_port = src.ports()[0]
    links = src.instanceLinks()

    assert len(links) == 1
    assert len(links[0].ports) == 1
    assert links[0].linkName == link_name

    for i in range(3):
        from_link = get_port_content(src_port, 'get', params={
            'link': link_name,
            'path': 'env?var=' + var,
            'port': links[0].ports[0].privatePort
        })

        if from_link == value:
            continue
        else:
            time.sleep(1)

    assert from_link == value


def generate_RSA(bits=2048):
    '''
    Generate an RSA keypair
    '''
    from Crypto.PublicKey import RSA
    new_key = RSA.generate(bits)
    public_key = new_key.publickey().exportKey('OpenSSH')
    private_key = new_key.exportKey()
    return private_key, public_key


@pytest.fixture(scope='session')
def host_ssh_containers(request, client):

    keys = generate_RSA()
    host_key = keys[0]
    os.system("echo '" + host_key + "' >" + PRIVATE_KEY_FILENAME)

    hosts = client.list_host(kind='docker', removed_null=True)

    managed_network = client.list_network(uuid='managed-docker0')[0]

    ssh_containers = []
    for host in hosts:
        env_var = {"SSH_KEY": keys[1]}
        docker_vol_value = ["/usr/bin/docker:/usr/bin/docker",
                            "/var/run/docker.sock:/var/run/docker.sock"
                            ]
        c = client.create_container(name="host_ssh_container",
                                    networkIds=[managed_network.id],
                                    imageUuid=SSH_HOST_IMAGE_UUID,
                                    requestedHostId=host.id,
                                    dataVolumes=docker_vol_value,
                                    environment=env_var,
                                    ports=[str(HOST_SSH_PUBLIC_PORT)+":22"]
                                    )
        ssh_containers.append(c)

    for c in ssh_containers:
        c = client.wait_success(c, 180)
        assert c.state == "running"

    def fin():

        for c in ssh_containers:
            client.delete(c)
        os.system("rm " + PRIVATE_KEY_FILENAME)

    request.addfinalizer(fin)


def get_ssh_to_host_ssh_container(host):

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(host.ipAddresses()[0].address, username=HOST_SSH_TEST_ACCOUNT,
                key_filename=PRIVATE_KEY_FILENAME, port=HOST_SSH_PUBLIC_PORT)

    return ssh


@pytest.fixture
def wait_for_condition(client, resource, check_function, fail_handler=None,
                       timeout=180):
    start = time.time()
    resource = client.reload(resource)
    while not check_function(resource):
        if time.time() - start > timeout:
            exceptionMsg = 'Timeout waiting for ' + resource.kind + \
                ' to satisfy condition: ' + \
                inspect.getsource(check_function)
            if (fail_handler):
                exceptionMsg = exceptionMsg + fail_handler(resource)
            raise Exception(exceptionMsg)

        time.sleep(.5)
        resource = client.reload(resource)

    return resource

