from cattle import from_env
import pytest
import random
import requests
import os
import time
import logging
import paramiko
import inspect
import re
from docker import Client

logging.basicConfig()
log = logging.getLogger()

TEST_IMAGE_UUID = os.environ.get('CATTLE_TEST_AGENT_IMAGE',
                                 'docker:cattle/test-agent:v7')

SSH_HOST_IMAGE_UUID = os.environ.get('CATTLE_SSH_HOST_IMAGE',
                                     'docker:rancher/ssh-host-container:' +
                                     'v0.1.0')

SOCAT_IMAGE_UUID = os.environ.get('CATTLE_CLUSTER_SOCAT_IMAGE',
                                  'docker:rancher/socat-docker:v0.2.0')

DEFAULT_TIMEOUT = 45

PRIVATE_KEY_FILENAME = "/tmp/private_key_host_ssh"
HOST_SSH_TEST_ACCOUNT = "ranchertest"
HOST_SSH_PUBLIC_PORT = 2222

socat_container_list = []

MANAGED_NETWORK = "managed"
UNMANAGED_NETWORK = "bridge"


@pytest.fixture(scope='session')
def cattle_url():
    default_url = 'http://localhost:8080/v1/schemas'
    return os.environ.get('CATTLE_TEST_URL', default_url)


@pytest.fixture(autouse=True, scope='session')
def cleanup(super_client):
    to_delete = []

    instance_name_format = re.compile('test-[0-9]{6}')
    env_name_format = re.compile('test[0-9]{6}')

    for i in super_client.list_instance(state='running'):
        try:
            if instance_name_format.match(i.name):

                to_delete.append(i)
        except AttributeError:
            pass

    delete_all(super_client, to_delete)

    to_delete_env = []
    for i in super_client.list_environment(state='active'):
        try:
            if env_name_format.match(i.name):
                to_delete_env.append(i)
        except AttributeError:
            pass

    delete_all(super_client, to_delete_env)


def _admin_client():
    access_key = os.environ.get("CATTLE_ACCESS_KEY", 'admin')
    secret_key = os.environ.get("CATTLE_SECRET_KEY", 'adminpass')
    return from_env(url=cattle_url(),
                    cache=False,
                    access_key=access_key,
                    secret_key=secret_key)


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


def acc_id(client):
    obj = client.list_api_key()[0]
    return obj.account().id


def client_for_project(project):
    access_key = random_str()
    secret_key = random_str()
    admin_client = _admin_client()
    active_cred = None
    account = project
    for cred in account.credentials():
        if cred.kind == 'apiKey' and cred.publicValue == access_key\
                and cred.secretValue == secret_key:
            active_cred = cred
            break

    if active_cred is None:
        active_cred = admin_client.create_api_key({
            'accountId': account.id,
            'publicValue': access_key,
            'secretValue': secret_key
        })

    active_cred = wait_success(admin_client, active_cred)
    if active_cred.state != 'active':
        wait_success(admin_client, active_cred.activate())

    return from_env(url=cattle_url(),
                    cache=False,
                    access_key=access_key,
                    secret_key=secret_key)


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
def client(admin_client):
    client = client_for_project(
        admin_client.list_project(uuid="adminProject")[0])
    assert client.valid()
    return client


@pytest.fixture(scope='session')
def admin_client():
    admin_client = _admin_client()
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


@pytest.fixture(scope='session')
def unmanaged_network(client):
    networks = client.list_network(uuid='unmanaged')
    assert len(networks) == 1

    return networks[0]


@pytest.fixture
def one_per_host(client, test_name):
    instances = []
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 2

    for host in hosts:
        c = client.create_container(name=test_name,
                                    ports=['3000:3000'],
                                    networkMode=MANAGED_NETWORK,
                                    imageUuid=TEST_IMAGE_UUID,
                                    requestedHostId=host.id)
        instances.append(c)

    instances = wait_all_success(client, instances, timeout=120)

    for i in instances:
        ports = i.ports_link()
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
    src_port = src.ports_link()[0]
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

    ssh_containers = []
    for host in hosts:
        env_var = {"SSH_KEY": keys[1]}
        docker_vol_value = ["/usr/bin/docker:/usr/bin/docker",
                            "/var/run/docker.sock:/var/run/docker.sock"
                            ]
        c = client.create_container(name="host_ssh_container",
                                    networkMode=MANAGED_NETWORK,
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


def wait_for(callback, timeout=DEFAULT_TIMEOUT, timeout_message=None):
    start = time.time()
    ret = callback()
    while ret is None or ret is False:
        time.sleep(.5)
        if time.time() - start > timeout:
            if timeout_message:
                raise Exception(timeout_message)
            else:
                raise Exception('Timeout waiting for condition')
        ret = callback()
    return ret


@pytest.fixture(scope='session')
def socat_containers(client, request):
    # When these tests run in the CI environment, the hosts don't expose the
    # docker daemon over tcp, so we need to create a container that binds to
    # the docker socket and exposes it on a port

    if len(socat_container_list) != 0:
        return
    hosts = client.list_host(kind='docker', removed_null=True)

    for host in hosts:
        socat_container = client.create_container(
            name='socat-%s' % random_str(),
            networkMode=MANAGED_NETWORK,
            imageUuid=SOCAT_IMAGE_UUID,
            ports='2375:2375/tcp',
            stdinOpen=False,
            tty=False,
            publishAllPorts=True,
            dataVolumes='/var/run/docker.sock:/var/run/docker.sock',
            requestedHostId=host.id)
        socat_container_list.append(socat_container)

    for socat_container in socat_container_list:
        wait_for_condition(
            client, socat_container,
            lambda x: x.state == 'running',
            lambda x: 'State is: ' + x.state)

    def remove_socat():
        delete_all(client, socat_container_list)

    request.addfinalizer(remove_socat)


def get_docker_client(host):
    ip = host.ipAddresses()[0].address
    port = '2375'

    params = {}
    params['base_url'] = 'tcp://%s:%s' % (ip, port)
    api_version = os.getenv('DOCKER_API_VERSION', '1.18')
    params['version'] = api_version

    return Client(**params)
