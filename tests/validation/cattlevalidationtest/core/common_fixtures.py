import cattle
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
import json
from docker import Client

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

TEST_IMAGE_UUID = os.environ.get('CATTLE_TEST_AGENT_IMAGE',
                                 'docker:cattle/test-agent:v7')

SSH_HOST_IMAGE_UUID = os.environ.get('CATTLE_SSH_HOST_IMAGE',
                                     'docker:rancher/ssh-host-container:' +
                                     'v0.1.0')

SOCAT_IMAGE_UUID = os.environ.get('CATTLE_CLUSTER_SOCAT_IMAGE',
                                  'docker:rancher/socat-docker:v0.2.0')

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"
LB_HOST_ROUTING_IMAGE_UUID = "docker:sangeetha/testnewhostrouting:latest"
SSH_IMAGE_UUID_HOSTNET = "docker:sangeetha/testclient33:latest"
HOST_ACCESS_IMAGE_UUID = "docker:sangeetha/testclient44:latest"
HEALTH_CHECK_IMAGE_UUID = "docker:sangeetha/testhealthcheck:v2"
MULTIPLE_EXPOSED_PORT_UUID = "docker:sangeetha/testmultipleport:v1"
DEFAULT_TIMEOUT = 45

SSLCERT_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                              'resources/sslcerts')

PRIVATE_KEY_FILENAME = "/tmp/private_key_host_ssh"
HOST_SSH_TEST_ACCOUNT = "ranchertest"
HOST_SSH_PUBLIC_PORT = 2222

socat_container_list = []
host_container_list = []
rancher_compose_con = {"container": None, "host": None, "port": "7878"}
CONTAINER_STATES = ["running", "stopped", "stopping"]

cert_list = {}

MANAGED_NETWORK = "managed"
UNMANAGED_NETWORK = "bridge"

dns_labels = {"io.rancher.container.dns": "true",
              "io.rancher.scheduler.affinity:container_label_ne":
              "io.rancher.stack_service.name=${stack_name}/${service_name}"}


@pytest.fixture(scope='session')
def cattle_url():
    default_url = 'http://localhost:8080/v1/schemas'
    return os.environ.get('CATTLE_TEST_URL', default_url)


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
        if cred.kind == 'apiKey' and cred.publicValue == user_name:
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
        if cred.kind == 'apiKey' and cred.publicValue == access_key:
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
def super_client(accounts):
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

    wait_all_success(client, items, timeout=180)


def delete_by_id(self, type, id):
    url = self.schema.types[type].links.collection
    if url.endswith('/'):
        url = url + id
    else:
        url = '/'.join([url, id])
    return self._delete(url)


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
            logger.exception('Failed to call %s', url)
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
def glusterfs_glusterconvoy(client, super_client, request):
    catalog_url = cattle_url() + "/v1-catalog/templates/library:"

    # Deploy GlusterFS template from catalog
    r = requests.get(catalog_url + "glusterfs:0")
    template = json.loads(r.content)
    r.close()

    dockerCompose = template["dockerCompose"]
    rancherCompose = template["rancherCompose"]
    environment = {}
    questions = template["questions"]
    for question in questions:
        label = question["variable"]
        value = question["default"]
        environment[label] = value

    env = client.create_environment(name="glusterfs",
                                    dockerCompose=dockerCompose,
                                    rancherCompose=rancherCompose,
                                    environment=environment,
                                    startOnCreate=True)
    env = client.wait_success(env, timeout=300)
    assert env.state == "active"

    for service in env.services():
        wait_for_condition(
            super_client, service,
            lambda x: x.state == "active",
            lambda x: 'State is: ' + x.state,
            timeout=600)

    # Deploy ConvoyGluster template from catalog

    r = requests.get(catalog_url + "convoy-gluster:1")
    template = json.loads(r.content)
    r.close()
    dockerCompose = template["dockerCompose"]
    rancherCompose = template["rancherCompose"]
    environment = {}
    questions = template["questions"]
    print questions
    for question in questions:
        label = question["variable"]
        value = question["default"]
        environment[label] = value
    environment["GLUSTERFS_SERVICE"] = "glusterfs/glusterfs-server"
    env = client.create_environment(name="convoy-gluster",
                                    dockerCompose=dockerCompose,
                                    rancherCompose=rancherCompose,
                                    environment=environment,
                                    startOnCreate=True)
    env = client.wait_success(env, timeout=300)

    for service in env.services():
        wait_for_condition(
            super_client, service,
            lambda x: x.state == "active",
            lambda x: 'State is: ' + x.state,
            timeout=600)

    # Verify that storage pool is created
    storagepools = client.list_storage_pool(removed_null=True,
                                            include="hosts",
                                            kind="storagePool")
    print storagepools
    assert len(storagepools) == 1

    def remove():
        env1 = client.list_environment(name="glusterfs")
        assert len(env1) == 1
        env2 = client.list_environment(name="convoy-gluster")
        assert len(env2) == 1
        delete_all(client, [env1[0], env2[0]])
    request.addfinalizer(remove)


@pytest.fixture(scope='session')
def socat_containers(client, request):
    # When these tests run in the CI environment, the hosts don't expose the
    # docker daemon over tcp, so we need to create a container that binds to
    # the docker socket and exposes it on a port

    if len(socat_container_list) != 0:
        return
    hosts = client.list_host(kind='docker', removed_null=True, state='active')

    for host in hosts:
        socat_container = client.create_container(
            name='socat-%s' % random_str(),
            networkMode=MANAGED_NETWORK,
            imageUuid=SOCAT_IMAGE_UUID,
            ports='2375:2375/tcp',
            stdinOpen=False,
            tty=False,
            publishAllPorts=True,
            privileged=True,
            dataVolumes='/var/run/docker.sock:/var/run/docker.sock',
            requestedHostId=host.id)
        socat_container_list.append(socat_container)

    for socat_container in socat_container_list:
        wait_for_condition(
            client, socat_container,
            lambda x: x.state == 'running',
            lambda x: 'State is: ' + x.state)
    time.sleep(10)

    for host in hosts:
        host_container = client.create_container(
            name='host-%s' % random_str(),
            networkMode="host",
            imageUuid=HOST_ACCESS_IMAGE_UUID,
            privileged=True,
            requestedHostId=host.id)
        host_container_list.append(host_container)

    for host_container in host_container_list:
        wait_for_condition(
            client, host_container,
            lambda x: x.state in ('running', 'stopped'),
            lambda x: 'State is: ' + x.state)

    time.sleep(10)

    def remove_socat():
        delete_all(client, socat_container_list)
        delete_all(client, host_container_list)
    request.addfinalizer(remove_socat)


def get_docker_client(host):
    ip = host.ipAddresses()[0].address
    port = '2375'

    params = {}
    params['base_url'] = 'tcp://%s:%s' % (ip, port)
    api_version = os.getenv('DOCKER_API_VERSION', '1.18')
    params['version'] = api_version

    return Client(**params)


def wait_for_scale_to_adjust(super_client, service):
    service = super_client.wait_success(service)
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active",
                                                       managed=1)
    start = time.time()

    while len(instance_maps) != service.scale:
        time.sleep(.5)
        instance_maps = super_client.list_serviceExposeMap(
            serviceId=service.id, state="active")
        if time.time() - start > 30:
            raise Exception('Timed out waiting for Service Expose map to be ' +
                            'created for all instances')

    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        wait_for_condition(
            super_client, c,
            lambda x: x.state == "running",
            lambda x: 'State is: ' + x.state)


def check_service_map(super_client, service, instance, state):
    instance_service_map = super_client.\
        list_serviceExposeMap(serviceId=service.id, instanceId=instance.id,
                              state=state)
    assert len(instance_service_map) == 1


def get_container_names_list(super_client, services):
    container_names = []
    for service in services:
        containers = get_service_container_list(super_client, service)
        for c in containers:
            if c.state == "running":
                container_names.append(c.externalId[:12])
    return container_names


def validate_add_service_link(super_client, service, consumedService):
    service_maps = super_client. \
        list_serviceConsumeMap(serviceId=service.id,
                               consumedServiceId=consumedService.id)
    assert len(service_maps) == 1
    service_map = service_maps[0]
    wait_for_condition(
        super_client, service_map,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state)


def validate_remove_service_link(super_client, service, consumedService):
    service_maps = super_client. \
        list_serviceConsumeMap(serviceId=service.id,
                               consumedServiceId=consumedService.id)
    assert len(service_maps) == 1
    service_map = service_maps[0]
    wait_for_condition(
        super_client, service_map,
        lambda x: x.state == "removed",
        lambda x: 'State is: ' + x.state)


def get_service_container_list(super_client, service, managed=None):

    container = []
    if managed is not None:
        all_instance_maps = \
            super_client.list_serviceExposeMap(serviceId=service.id,
                                               managed=managed)
    else:
        all_instance_maps = \
            super_client.list_serviceExposeMap(serviceId=service.id)

    instance_maps = []
    for instance_map in all_instance_maps:
        if instance_map.state not in ("removed", "removing"):
            instance_maps.append(instance_map)

    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        assert c.state in CONTAINER_STATES
        containers = super_client.list_container(
            externalId=c.externalId,
            include="hosts")
        assert len(containers) == 1
        container.append(containers[0])

    return container


def link_svc_with_port(super_client, service, linkservices, port):

    for linkservice in linkservices:
        service_link = {"serviceId": linkservice.id, "ports": [port]}
        service = service.addservicelink(serviceLink=service_link)
        validate_add_service_link(super_client, service, linkservice)
    return service


def link_svc(super_client, service, linkservices):

    for linkservice in linkservices:
        service_link = {"serviceId": linkservice.id}
        service = service.addservicelink(serviceLink=service_link)
        validate_add_service_link(super_client, service, linkservice)
    return service


def activate_svc(client, service):

    service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"
    return service


def validate_exposed_port(super_client, service, public_port):
    con_list = get_service_container_list(super_client, service)
    assert len(con_list) == service.scale
    time.sleep(5)
    for con in con_list:
        con_host = super_client.by_id('host', con.hosts[0].id)
        for port in public_port:
            response = get_http_response(con_host, port, "/service.html")
            assert response == con.externalId[:12]


def validate_exposed_port_and_container_link(super_client, con, link_name,
                                             link_port, exposed_port):
    time.sleep(10)
    # Validate that the environment variables relating to link containers are
    # set
    containers = super_client.list_container(externalId=con.externalId,
                                             include="hosts",
                                             removed_null=True)
    assert len(containers) == 1
    con = containers[0]
    host = super_client.by_id('host', con.hosts[0].id)
    docker_client = get_docker_client(host)
    inspect = docker_client.inspect_container(con.externalId)
    response = inspect["Config"]["Env"]
    logger.info(response)
    address = None
    port = None

    env_name_link_address = link_name + "_PORT_" + str(link_port) + "_TCP_ADDR"
    env_name_link_name = link_name + "_PORT_" + str(link_port) + "_TCP_PORT"

    for env_var in response:
        if env_name_link_address in env_var:
            address = env_var[env_var.index("=")+1:]
        if env_name_link_name in env_var:
            port = env_var[env_var.index("=")+1:]

    logger.info(address)
    logger.info(port)
    assert address and port is not None

    # Validate port mapping
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host.ipAddresses()[0].address, username="root",
                password="root", port=exposed_port)

    # Validate link containers
    cmd = "wget -O result.txt  --timeout=20 --tries=1 http://" + \
          address+":"+port+"/name.html" + ";cat result.txt"
    logger.info(cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)

    response = stdout.readlines()
    assert len(response) == 1
    resp = response[0].strip("\n")
    logger.info(resp)

    assert link_name == resp


def wait_for_lb_service_to_become_active(super_client, client,
                                         services, lb_service,
                                         unmanaged_con_count=None):
    wait_for_config_propagation(super_client, lb_service)
    lb_containers = get_service_container_list(super_client, lb_service)
    assert len(lb_containers) == lb_service.scale

    # Get haproxy config from Lb Agents
    for lb_con in lb_containers:
        host = super_client.by_id('host', lb_con.hosts[0].id)
        docker_client = get_docker_client(host)
        haproxy = docker_client.copy(
            lb_con.externalId, "/etc/haproxy/haproxy.cfg")
        print "haproxy: " + haproxy.read()

        # Get iptable entries from host
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host.ipAddresses()[0].address, username="root",
                    password="root", port=44)

        cmd = "iptables-save"
        logger.info(cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)

        responses = stdout.readlines()
        for response in responses:
            print response


def validate_lb_service_for_external_services(super_client, client, lb_service,
                                              port, container_list,
                                              hostheader=None, path=None):
    container_names = []
    for con in container_list:
        container_names.append(con.externalId[:12])
    validate_lb_service_con_names(super_client, client, lb_service, port,
                                  container_names, hostheader, path)


def validate_lb_service(super_client, client, lb_service, port,
                        target_services, hostheader=None, path=None,
                        domain=None, test_ssl_client_con=None,
                        unmanaged_cons=None):
    target_count = 0
    for service in target_services:
        target_count = target_count + service.scale
    container_names = get_container_names_list(super_client,
                                               target_services)
    logger.info(container_names)
    # Check that unmanaged containers for each services in present in
    # container_names
    if unmanaged_cons is not None:
        unmanaged_con_count = 0
        for service in target_services:
            if service.id in unmanaged_cons.keys():
                unmanaged_con_list = unmanaged_cons[service.id]
                unmanaged_con_count = unmanaged_con_count + 1
                for con in unmanaged_con_list:
                    if con not in container_names:
                        assert False
        assert len(container_names) == target_count + unmanaged_con_count
    else:
        assert len(container_names) == target_count

    validate_lb_service_con_names(super_client, client, lb_service, port,
                                  container_names, hostheader, path, domain,
                                  test_ssl_client_con)


def validate_lb_service_con_names(super_client, client, lb_service, port,
                                  container_names,
                                  hostheader=None, path=None, domain=None,
                                  test_ssl_client_con=None):
    lb_containers = get_service_container_list(super_client, lb_service)
    for lb_con in lb_containers:
        host = client.by_id('host', lb_con.hosts[0].id)
        if domain:
            # Validate for ssl listeners
            # wait_until_lb_is_active(host, port, is_ssl=True)
            if hostheader is not None or path is not None:
                check_round_robin_access_for_ssl(container_names, host, port,
                                                 domain, test_ssl_client_con,
                                                 hostheader, path)
            else:
                check_round_robin_access_for_ssl(container_names, host, port,
                                                 domain, test_ssl_client_con)

        else:
            wait_until_lb_is_active(host, port)
            if hostheader is not None or path is not None:
                check_round_robin_access(container_names, host, port,
                                         hostheader, path)
            else:
                check_round_robin_access(container_names, host, port)


def validate_cert_error(super_client, client, lb_service, port, domain,
                        default_domain, cert,
                        hostheader=None, path=None,
                        test_ssl_client_con=None):
    lb_containers = get_service_container_list(super_client, lb_service)
    for lb_con in lb_containers:
        host = client.by_id('host', lb_con.hosts[0].id)
        check_for_cert_error(host, port, domain, default_domain, cert,
                             test_ssl_client_con)


def wait_until_lb_is_active(host, port, timeout=30, is_ssl=False):
    start = time.time()
    while check_for_no_access(host, port, is_ssl):
        time.sleep(.5)
        print "No access yet"
        if time.time() - start > timeout:
            raise Exception('Timed out waiting for LB to become active')
    return


def check_for_no_access(host, port, is_ssl=False):
    if is_ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    try:
        url = protocol+host.ipAddresses()[0].address+":"+port+"/name.html"
        requests.get(url)
        return False
    except requests.ConnectionError:
        logger.info("Connection Error - " + url)
        return True


def validate_linked_service(super_client, service, consumed_services,
                            exposed_port, exclude_instance=None,
                            exclude_instance_purged=False,
                            unmanaged_cons=None, linkName=None):
    time.sleep(5)

    containers = get_service_container_list(super_client, service)
    assert len(containers) == service.scale

    for container in containers:
        host = super_client.by_id('host', container.hosts[0].id)
        for consumed_service in consumed_services:
            expected_dns_list = []
            expected_link_response = []
            dns_response = []
            consumed_containers = get_service_container_list(super_client,
                                                             consumed_service)
            if exclude_instance_purged:
                assert len(consumed_containers) == consumed_service.scale - 1
            else:
                if unmanaged_cons is not None \
                        and consumed_service.id in unmanaged_cons.keys():
                    unmanaged_con_list = \
                        unmanaged_cons[consumed_service.id]
                    assert \
                        len(consumed_containers) == \
                        consumed_service.scale + len(unmanaged_con_list)
                    for con in unmanaged_con_list:
                        print "Checking for container : " + con.name
                        found = False
                        for consumed_con in consumed_containers:
                            if con.id == consumed_con.id:
                                found = True
                                break
                        assert found
                else:
                    assert len(consumed_containers) == consumed_service.scale

            for con in consumed_containers:
                if (exclude_instance is not None) \
                        and (con.id == exclude_instance.id):
                    logger.info("Excluded from DNS and wget list:" + con.name)
                else:
                    if con.networkMode == "host":
                        con_host = super_client.by_id('host', con.hosts[0].id)
                        expected_dns_list.append(
                            con_host.ipAddresses()[0].address)
                        expected_link_response.append(con_host.hostname)
                    else:
                        expected_dns_list.append(con.primaryIpAddress)
                        expected_link_response.append(con.externalId[:12])

            logger.info("Expected dig response List" + str(expected_dns_list))
            logger.info("Expected wget response List" +
                        str(expected_link_response))

            # Validate port mapping
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host.ipAddresses()[0].address, username="root",
                        password="root", port=int(exposed_port))

            if linkName is None:
                linkName = consumed_service.name
            # Validate link containers
            cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + \
                  linkName + ":80/name.html;cat result.txt"
            logger.info(cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            assert len(response) == 1
            resp = response[0].strip("\n")
            logger.info("Actual wget Response" + str(resp))
            assert resp in (expected_link_response)

            # Validate DNS resolution using dig
            cmd = "dig " + linkName + " +short"
            logger.info(cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            logger.info("Actual dig Response" + str(response))

            unmanaged_con_count = 0
            if (unmanaged_cons is not None) and \
                    (consumed_service.id in unmanaged_cons.keys()):
                unmanaged_con_count = len(unmanaged_cons[consumed_service.id])
            expected_entries_dig = consumed_service.scale + unmanaged_con_count

            if exclude_instance is not None:
                expected_entries_dig = expected_entries_dig - 1

            assert len(response) == expected_entries_dig

            for resp in response:
                dns_response.append(resp.strip("\n"))

            for address in expected_dns_list:
                assert address in dns_response


def validate_dns_service(super_client, service, consumed_services,
                         exposed_port, dnsname, exclude_instance=None,
                         exclude_instance_purged=False, unmanaged_cons=None):
    time.sleep(5)

    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == service.scale

    for con in service_containers:
        host = super_client.by_id('host', con.hosts[0].id)
        containers = []
        expected_dns_list = []
        expected_link_response = []
        dns_response = []

        for consumed_service in consumed_services:
            cons = get_service_container_list(super_client, consumed_service)
            if exclude_instance_purged:
                assert len(cons) == consumed_service.scale - 1
            else:
                if unmanaged_cons is not None \
                        and consumed_service.id in unmanaged_cons.keys():
                    unmanaged_con_list = unmanaged_cons[consumed_service.id]
                    if unmanaged_con_list is not None:
                        assert len(cons) == \
                            consumed_service.scale + \
                            len(unmanaged_con_list)
                    for con in unmanaged_con_list:
                        print "Checking for container : " + con.name
                        found = False
                        for consumed_con in cons:
                            if con.id == consumed_con.id:
                                found = True
                                break
                        assert found
                else:
                    assert len(cons) == consumed_service.scale
            containers = containers + cons
        for con in containers:
            if (exclude_instance is not None) \
                    and (con.id == exclude_instance.id):
                logger.info("Excluded from DNS and wget list:" + con.name)
            else:
                if con.networkMode == "host":
                    con_host = super_client.by_id('host', con.hosts[0].id)
                    expected_dns_list.append(con_host.ipAddresses()[0].address)
                    expected_link_response.append(con_host.hostname)
                else:
                    expected_dns_list.append(con.primaryIpAddress)
                    expected_link_response.append(con.externalId[:12])

        logger.info("Expected dig response List" + str(expected_dns_list))
        logger.info("Expected wget response List" +
                    str(expected_link_response))

        # Validate port mapping
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host.ipAddresses()[0].address, username="root",
                    password="root", port=int(exposed_port))

        # Validate link containers
        cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + dnsname + \
              ":80/name.html;cat result.txt"
        logger.info(cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        assert len(response) == 1
        resp = response[0].strip("\n")
        logger.info("Actual wget Response" + str(resp))
        assert resp in (expected_link_response)

        # Validate DNS resolution using dig
        cmd = "dig " + dnsname + " +short"
        logger.info(cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        logger.info("Actual dig Response" + str(response))
        assert len(response) == len(expected_dns_list)

        for resp in response:
            dns_response.append(resp.strip("\n"))

        for address in expected_dns_list:
            assert address in dns_response


def validate_external_service(super_client, service, ext_services,
                              exposed_port, container_list,
                              exclude_instance=None,
                              exclude_instance_purged=False):
    time.sleep(5)

    containers = get_service_container_list(super_client, service)
    assert len(containers) == service.scale
    for container in containers:
        print "Validation for container -" + str(container.name)
        host = super_client.by_id('host', container.hosts[0].id)
        for ext_service in ext_services:
            expected_dns_list = []
            expected_link_response = []
            dns_response = []
            for con in container_list:
                if (exclude_instance is not None) \
                        and (con.id == exclude_instance.id):
                    print "Excluded from DNS and wget list:" + con.name
                else:
                    expected_dns_list.append(con.primaryIpAddress)
                    expected_link_response.append(con.externalId[:12])

            print "Expected dig response List" + str(expected_dns_list)
            print "Expected wget response List" + str(expected_link_response)

            # Validate port mapping
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host.ipAddresses()[0].address, username="root",
                        password="root", port=int(exposed_port))

            # Validate link containers
            cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + \
                  ext_service.name + ":80/name.html;cat result.txt"
            print cmd
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            assert len(response) == 1
            resp = response[0].strip("\n")
            print "Actual wget Response" + str(resp)
            assert resp in (expected_link_response)

            # Validate DNS resolution using dig
            cmd = "dig " + ext_service.name + " +short"
            print cmd
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            print "Actual dig Response" + str(response)

            expected_entries_dig = len(container_list)
            if exclude_instance is not None:
                expected_entries_dig = expected_entries_dig - 1

            assert len(response) == expected_entries_dig

            for resp in response:
                dns_response.append(resp.strip("\n"))

            for address in expected_dns_list:
                assert address in dns_response


def validate_external_service_for_hostname(super_client, service, ext_services,
                                           exposed_port):

    time.sleep(5)

    containers = get_service_container_list(super_client, service)
    assert len(containers) == service.scale
    for container in containers:
        print "Validation for container -" + str(container.name)
        host = super_client.by_id('host', container.hosts[0].id)
        for ext_service in ext_services:
            # Validate port mapping
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host.ipAddresses()[0].address, username="root",
                        password="root", port=int(exposed_port))
            cmd = "ping -c 2 " + ext_service.name + \
                  "> result.txt;cat result.txt"
            print cmd
            stdin, stdout, stderr = ssh.exec_command(cmd)
            response = stdout.readlines()
            print "Actual wget Response" + str(response)
            assert ext_service.hostname in str(response) and \
                "0% packet loss" in str(response)


@pytest.fixture(scope='session')
def rancher_compose_container(admin_client, client, request):
    if rancher_compose_con["container"] is not None:
        return
    setting = admin_client.by_id_setting(
        "default.cattle.rancher.compose.linux.url")
    rancher_compose_url = setting.value
    cmd1 = \
        "wget " + rancher_compose_url
    compose_file = rancher_compose_url.split("/")[-1]
#   cmd2 = "tar xvf rancher-compose-linux-amd64.tar.gz"
    cmd2 = "tar xvf " + compose_file

    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    assert len(hosts) > 0
    host = hosts[0]
    port = rancher_compose_con["port"]
    c = client.create_container(name="rancher-compose-client",
                                networkMode=MANAGED_NETWORK,
                                imageUuid="docker:sangeetha/testclient",
                                ports=[port+":22/tcp"],
                                requestedHostId=host.id
                                )

    c = client.wait_success(c, 120)
    assert c.state == "running"
    time.sleep(5)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host.ipAddresses()[0].address, username="root",
                password="root", port=int(port))
    cmd = cmd1+";"+cmd2
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    found = False
    for resp in response:
        if "/rancher-compose" in resp:
            found = True
    assert found
    rancher_compose_con["container"] = c
    rancher_compose_con["host"] = host

    def remove_rancher_compose_container():
        delete_all(client, [rancher_compose_con["container"]])
    request.addfinalizer(remove_rancher_compose_container)


def launch_rancher_compose(client, env):
    compose_configs = env.exportconfig()
    docker_compose = compose_configs["dockerComposeConfig"]
    rancher_compose = compose_configs["rancherComposeConfig"]
    execute_rancher_compose(client, env.name + "rancher",
                            docker_compose, rancher_compose,
                            "up -d", "Creating stack")


def execute_rancher_compose(client, env_name, docker_compose,
                            rancher_compose, command, expected_resp):
    access_key = client._access_key
    secret_key = client._secret_key
    docker_filename = env_name + "-docker-compose.yml"
    rancher_filename = env_name + "-rancher-compose.yml"
    project_name = env_name

    cmd1 = "export RANCHER_URL=" + cattle_url()
    cmd2 = "export RANCHER_ACCESS_KEY=" + access_key
    cmd3 = "export RANCHER_SECRET_KEY=" + secret_key
    cmd4 = "cd rancher-compose-v*"
    cmd5 = "echo '" + docker_compose + "' > " + docker_filename
    if rancher_compose is not None:
        rcmd = "echo '" + rancher_compose + "' > " + rancher_filename + ";"
        cmd6 = rcmd + "./rancher-compose -p " + project_name + " -f " \
            + docker_filename + " -r " + rancher_filename + \
            " " + command
    else:
        cmd6 = "./rancher-compose -p " + project_name + \
               " -f " + docker_filename + " " + command

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        rancher_compose_con["host"].ipAddresses()[0].address, username="root",
        password="root", port=int(rancher_compose_con["port"]))
    cmd = cmd1+";"+cmd2+";"+cmd3+";"+cmd4+";"+cmd5+";"+cmd6
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    print str(response)
    found = False
    for resp in response:
        if expected_resp in resp:
            found = True
    assert found


def launch_rancher_compose_from_file(client, subdir, docker_compose,
                                     env_name, command, response,
                                     rancher_compose=None):
    docker_compose = readDataFile(subdir, docker_compose)
    if rancher_compose is not None:
        rancher_compose = readDataFile(subdir, rancher_compose)
    execute_rancher_compose(client, env_name, docker_compose,
                            rancher_compose, command, response)


def create_env_with_svc_and_lb(client, scale_svc, scale_lb, port,
                               internal=False, lb_config=None):

    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}

    if internal:
        launch_config_lb = {"expose": [port+":80"]}
    else:
        launch_config_lb = {"ports": [port+":80"]}

    # Create Environment
    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    # Create LB Service
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=scale_lb,
        loadBalancerConfig=lb_config)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    return env, service, lb_service


def create_env_with_ext_svc_and_lb(client, scale_lb, port):

    launch_config_lb = {"ports": [port+":80"]}

    env, service, ext_service, con_list = create_env_with_ext_svc(
        client, 1, port)

    # Create LB Service
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=scale_lb)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    return env, lb_service, ext_service, con_list


def create_env_with_2_svc(client, scale_svc, scale_consumed_svc, port):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    # Create Environment
    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    # Create Consumed Service
    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service = client.wait_success(consumed_service)
    assert consumed_service.state == "inactive"

    return env, service, consumed_service


def create_env_with_2_svc_dns(client, scale_svc, scale_consumed_svc, port,
                              cross_linking=False):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    # Create Environment for dns service and client service
    env = create_env(client)

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    # Create Consumed Service1
    if cross_linking:
        env_id = create_env(client).id
    else:
        env_id = env.id

    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service = client.create_service(
        name=service_name, environmentId=env_id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service = client.wait_success(consumed_service)
    assert consumed_service.state == "inactive"

    # Create Consumed Service2
    if cross_linking:
        env_id = create_env(client).id
    else:
        env_id = env.id

    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service1 = client.create_service(
        name=service_name, environmentId=env_id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "inactive"

    # Create DNS service

    dns = client.create_dnsService(name='WEB1',
                                   environmentId=env.id)
    dns = client.wait_success(dns)

    return env, service, consumed_service, consumed_service1, dns


def create_env_with_ext_svc(client, scale_svc, port, hostname=False):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    # Create Environment
    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    con_list = None

    # Create external Service
    random_name = random_str()
    ext_service_name = random_name.replace("-", "")

    if not hostname:
        # Create 2 containers which would be the applications that need to be
        # serviced by the external service

        c1 = client.create_container(name=random_str(),
                                     imageUuid=WEB_IMAGE_UUID)
        c2 = client.create_container(name=random_str(),
                                     imageUuid=WEB_IMAGE_UUID)

        c1 = client.wait_success(c1, 120)
        assert c1.state == "running"
        c2 = client.wait_success(c2, 120)
        assert c2.state == "running"

        con_list = [c1, c2]
        ips = [c1.primaryIpAddress, c2.primaryIpAddress]

        ext_service = client.create_externalService(
            name=ext_service_name, environmentId=env.id,
            externalIpAddresses=ips)

    else:
        ext_service = client.create_externalService(
            name=ext_service_name, environmentId=env.id, hostname="google.com")

    ext_service = client.wait_success(ext_service)
    assert ext_service.state == "inactive"

    return env, service, ext_service, con_list


def create_env_and_svc(client, launch_config, scale, retainIp=False):

    env = create_env(client)
    service = create_svc(client, env, launch_config, scale, retainIp)
    return service, env


def check_container_in_service(super_client, service):

    container_list = get_service_container_list(super_client, service,
                                                managed=1)
    assert len(container_list) == service.scale

    for container in container_list:
        assert container.state == "running"
        containers = super_client.list_container(
            externalId=container.externalId,
            include="hosts",
            removed_null=True)
        docker_client = get_docker_client(containers[0].hosts[0])
        inspect = docker_client.inspect_container(container.externalId)
        logger.info("Checked for containers running - " + container.name)
        assert inspect["State"]["Running"]


def create_svc(client, env, launch_config, scale, retainIp=False):

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config,
                                    scale=scale,
                                    retainIp=retainIp)

    service = client.wait_success(service)
    assert service.state == "inactive"
    return service


def wait_until_instances_get_stopped(super_client, service, timeout=60):
    stopped_count = 0
    start = time.time()
    while stopped_count != service.scale:
        time.sleep(.5)
        container_list = get_service_container_list(super_client, service)
        stopped_count = 0
        for con in container_list:
            if con.state == "stopped":
                stopped_count = stopped_count + 1
        if time.time() - start > timeout:
            raise Exception(
                'Timed out waiting for instances to get to stopped state')


def get_service_containers_with_name(
        super_client, service, name, managed=None):

    nameformat = re.compile(name + "_[0-9]{1,2}")
    start = time.time()
    instance_list = []

    while len(instance_list) != service.scale:
        instance_list = []
        print "sleep for .5 sec"
        time.sleep(.5)
        if managed is not None:
            all_instance_maps = \
                super_client.list_serviceExposeMap(serviceId=service.id,
                                                   managed=managed)
        else:
            all_instance_maps = \
                super_client.list_serviceExposeMap(serviceId=service.id)
        for instance_map in all_instance_maps:
            if instance_map.state == "active":
                c = super_client.by_id('container', instance_map.instanceId)
                if nameformat.match(c.name) \
                        and c.state in ("running", "stopped"):
                    instance_list.append(c)
                    print c.name
        if time.time() - start > 30:
            raise Exception('Timed out waiting for Service Expose map to be ' +
                            'created for all instances')
    container = []
    for instance in instance_list:
        assert instance.externalId is not None
        containers = super_client.list_container(
            externalId=instance.externalId,
            include="hosts")
        assert len(containers) == 1
        container.append(containers[0])
    return container


def wait_until_instances_get_stopped_for_service_with_sec_launch_configs(
        super_client, service, timeout=60):
    stopped_count = 0
    start = time.time()
    container_count = service.scale*(len(service.secondaryLaunchConfigs)+1)
    while stopped_count != container_count:
        time.sleep(.5)
        container_list = get_service_container_list(super_client, service)
        stopped_count = 0
        for con in container_list:
            if con.state == "stopped":
                stopped_count = stopped_count + 1
        if time.time() - start > timeout:
            raise Exception(
                'Timed out waiting for instances to get to stopped state')


def validate_lb_service_for_no_access(super_client, lb_service, port,
                                      hostheader, path):

    lb_containers = get_service_container_list(super_client, lb_service)
    for lb_con in lb_containers:
        host = super_client.by_id('host', lb_con.hosts[0].id)
        wait_until_lb_is_active(host, port)
        check_for_service_unavailable(host, port, hostheader, path)


def check_for_service_unavailable(host, port, hostheader, path):

    url = "http://" + host.ipAddresses()[0].address +\
          ":" + port + path
    logger.info(url)

    headers = {"host": hostheader}

    logger.info(headers)
    r = requests.get(url, headers=headers)
    response = r.text.strip("\n")
    logger.info(response)
    r.close()
    assert "503 Service Unavailable" in response


def get_http_response(host, port, path):

    url = "http://" + host.ipAddresses()[0].address +\
          ":" + str(port) + path
    logger.info(url)

    r = requests.get(url)
    response = r.text.strip("\n")
    logger.info(response)
    r.close()
    return response


def check_round_robin_access(container_names, host, port,
                             hostheader=None, path="/name.html"):

    con_hostname = container_names[:]
    con_hostname_ordered = []

    url = "http://" + host.ipAddresses()[0].address +\
          ":" + port + path

    logger.info(url)

    headers = None
    if hostheader is not None:
        headers = {"host": hostheader}

    logger.info(headers)

    for n in range(0, len(con_hostname)):
        if headers is not None:
            r = requests.get(url, headers=headers)
        else:
            r = requests.get(url)
        response = r.text.strip("\n")
        logger.info(response)
        r.close()
        assert response in con_hostname
        con_hostname.remove(response)
        con_hostname_ordered.append(response)

    logger.info(con_hostname_ordered)

    i = 0
    for n in range(0, 10):
        if headers is not None:
            r = requests.get(url, headers=headers)
        else:
            r = requests.get(url)
        response = r.text.strip("\n")
        r.close()
        logger.info("Response received-" + response)
        assert response == con_hostname_ordered[i]
        i = i + 1
        if i == len(con_hostname_ordered):
            i = 0


def check_cert_using_openssl(host, port, domain, test_ssl_client_con):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        test_ssl_client_con["host"].ipAddresses()[0].address, username="root",
        password="root", port=int(test_ssl_client_con["port"]))

    cmd = "openssl s_client" + \
          " -connect " + host.ipAddresses()[0].address + ":" + port + \
          " -servername " + domain + "</dev/null > result.out;cat result.out"
    logger.info(cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    logger.info(response)
    responseLen = len(response)
    assert responseLen > 3
    assert "CN="+domain in response[3]


def check_round_robin_access_for_ssl(container_names, host, port, domain,
                                     test_ssl_client_con,
                                     hostheader=None, path="/name.html"):

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        test_ssl_client_con["host"].ipAddresses()[0].address, username="root",
        password="root", port=int(test_ssl_client_con["port"]))

    cmd = "echo '" + host.ipAddresses()[0].address + \
          " " + domain + "'> /etc/hosts;grep " + domain + " /etc/hosts"
    response = execute_command(ssh, cmd)
    logger.info(response)

    domain_cert = domain + ".crt "
    cert_str = " --ca-certificate=" + domain_cert
    host_header_str = "--header=host:" + hostheader + " "
    url_str = " https://" + domain + ":" + port + path
    cmd = "wget -O result.txt --timeout=20 --tries=1" + \
          cert_str + host_header_str + url_str + ";cat result.txt"

    con_hostname = container_names[:]
    con_hostname_ordered = []

    for n in range(0, len(con_hostname)):
        response = execute_command(ssh, cmd)
        assert response in con_hostname
        con_hostname.remove(response)
        con_hostname_ordered.append(response)

    logger.info(con_hostname_ordered)

    i = 0
    for n in range(0, 5):
        response = execute_command(ssh, cmd)
        logger.info(response)
        assert response == con_hostname_ordered[i]
        i = i + 1
        if i == len(con_hostname_ordered):
            i = 0


def check_for_cert_error(host, port, domain, default_domain, cert,
                         test_ssl_client_con, path="/name.html"):

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        test_ssl_client_con["host"].ipAddresses()[0].address, username="root",
        password="root", port=int(test_ssl_client_con["port"]))

    cmd = "echo '" + host.ipAddresses()[0].address + \
          " " + domain + "'> /etc/hosts;grep " + domain + " /etc/hosts"
    response = execute_command(ssh, cmd)
    logger.info(response)

    domain_cert = cert + ".crt "
    cert_str = " --ca-certificate=" + domain_cert
    url_str = " https://" + domain + ":" + port + path
    cmd = "wget -O result.txt --timeout=20 --tries=1" + \
          cert_str + url_str + ";cat result.txt"

    error_string = "ERROR: cannot verify " + domain + "'s certificate"

    stdin, stdout, stderr = ssh.exec_command(cmd)
    errors = stderr.readlines()
    logger.info(errors)
    found_error = False
    for error in errors:
        if error_string in error:
            found_error = True
    assert found_error


def execute_command(ssh, cmd):
    logger.info(cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    logger.info(response)
    assert len(response) == 1
    resp = response[0].strip("\n")
    logger.info("Response" + str(resp))
    return resp


def create_env_with_multiple_svc_and_lb(client, scale_svc, scale_lb,
                                        ports, count, crosslinking=False):

    target_port = ["80", "81"]
    launch_config_svc = \
        {"imageUuid": LB_HOST_ROUTING_IMAGE_UUID}

    assert len(ports) in (1, 2)

    launch_port = []
    for i in range(0, len(ports)):
        listening_port = ports[i]+":"+target_port[i]
        if "/" in ports[i]:
            port_mode = ports[i].split("/")
            listening_port = port_mode[0]+":"+target_port[i]+"/"+port_mode[1]
        launch_port.append(listening_port)

    launch_config_lb = {"ports": launch_port}

    services = []
    # Create Environment
    env = create_env(client)

    # Create Service
    for i in range(0, count):
        random_name = random_str()
        service_name = random_name.replace("-", "")
        if crosslinking:
            env_serv = create_env(client)
            env_id = env_serv.id
        else:
            env_id = env.id
        service = client.create_service(name=service_name,
                                        environmentId=env_id,
                                        launchConfig=launch_config_svc,
                                        scale=scale_svc)

        service = client.wait_success(service)
        assert service.state == "inactive"
        services.append(service)

    # Create LB Service
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=scale_lb)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    env = env.activateservices()
    env = client.wait_success(env, 120)

    if not crosslinking:
        for service in services:
            service = client.wait_success(service, 120)
            assert service.state == "active"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    return env, services, lb_service


def create_env_with_multiple_svc_and_ssl_lb(client, scale_svc, scale_lb,
                                            ports, count, ssl_ports,
                                            default_cert, certs=[]):
    target_port = ["80", "81"]
    launch_config_svc = \
        {"imageUuid": LB_HOST_ROUTING_IMAGE_UUID}

    assert len(ports) in (1, 2)

    launch_port = []
    for i in range(0, len(ports)):
        listening_port = ports[i]+":"+target_port[i]
        if "/" in ports[i]:
            port_mode = ports[i].split("/")
            listening_port = port_mode[0]+":"+target_port[i]+"/"+port_mode[1]
        launch_port.append(listening_port)

    launch_config_lb = {"ports": launch_port,
                        "labels":
                            {'io.rancher.loadbalancer.ssl.ports': ssl_ports}}

    services = []
    # Create Environment
    env = create_env(client)

    # Create Service
    for i in range(0, count):
        random_name = random_str()
        service_name = random_name.replace("-", "")
        service = client.create_service(name=service_name,
                                        environmentId=env.id,
                                        launchConfig=launch_config_svc,
                                        scale=scale_svc)

        service = client.wait_success(service)
        assert service.state == "inactive"
        services.append(service)

    # Create LB Service
    random_name = random_str()
    service_name = "LB-" + random_name.replace("-", "")

    supported_cert_list = []
    for cert in certs:
        supported_cert_list.append(cert.id)
    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=scale_lb,
        certificateIds=supported_cert_list,
        defaultCertificateId=default_cert.id)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    env = env.activateservices()
    env = client.wait_success(env, 120)

    for service in services:
        service = client.wait_success(service, 120)
        assert service.state == "active"

    lb_service = client.wait_success(lb_service, 120)
    assert lb_service.state == "active"
    return env, services, lb_service


def wait_for_config_propagation(super_client, lb_service, timeout=30):
    lb_instances = get_service_container_list(super_client, lb_service)
    assert len(lb_instances) == lb_service.scale
    for lb_instance in lb_instances:
        agentId = lb_instance.agentId
        agent = super_client.by_id('agent', agentId)
        assert agent is not None
        item = get_config_item(agent, "haproxy")
        start = time.time()
        print "requested_version " + str(item.requestedVersion)
        print "applied_version " + str(item.appliedVersion)
        while item.requestedVersion != item.appliedVersion:
            print "requested_version " + str(item.requestedVersion)
            print "applied_version " + str(item.appliedVersion)
            time.sleep(.1)
            agent = super_client.reload(agent)
            item = get_config_item(agent, "haproxy")
            if time.time() - start > timeout:
                raise Exception('Timed out waiting for config propagation')


def wait_for_metadata_propagation(super_client, timeout=30):
    networkAgents = super_client.list_container(
        name='Network Agent', removed_null=True)
    assert len(networkAgents) == len(super_client.list_host(kind='docker',
                                                            removed_null=True))
    for networkAgent in networkAgents:
        agentId = networkAgent.agentId
        agent = super_client.by_id('agent', agentId)
        assert agent is not None
        item = get_config_item(agent, "hosts")
        start = time.time()
        print "agent_id " + str(agentId)
        print "requested_version " + str(item.requestedVersion)
        print "applied_version " + str(item.appliedVersion)
        while item.requestedVersion != item.appliedVersion:
            print "requested_version " + str(item.requestedVersion)
            print "applied_version " + str(item.appliedVersion)
            time.sleep(.1)
            agent = super_client.reload(agent)
            item = get_config_item(agent, "hosts")
            if time.time() - start > timeout:
                raise Exception('Timed out waiting for config propagation')


def get_config_item(agent, config_name):
    item = None
    for config_items in agent.configItemStatuses():
        if config_items.name == config_name:
            item = config_items
            break
    assert item is not None
    return item


def get_plain_id(admin_client, obj=None):
    if obj is None:
        obj = admin_client
        admin_client = super_client(None)

    ret = admin_client.list(obj.type, uuid=obj.uuid, _plainId='true')
    assert len(ret) == 1
    return ret[0].id


def create_env(client):
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"
    return env


def get_env(super_client, service):
    e = super_client.by_id('environment', service.environmentId)
    return e


def get_service_container_with_label(super_client, service, name, label):

    containers = []
    found = False
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    nameformat = re.compile(name + "_[0-9]{1,2}")
    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        if nameformat.match(c.name) \
                and c.labels["io.rancher.service.deployment.unit"] == label:
            containers = super_client.list_container(
                externalId=c.externalId,
                include="hosts")
            assert len(containers) == 1
            found = True
            break
    assert found
    return containers[0]


def get_side_kick_container(super_client, container, service, service_name):
    label = container.labels["io.rancher.service.deployment.unit"]
    print container.name + " - " + label
    secondary_con = get_service_container_with_label(
        super_client, service, service_name, label)
    return secondary_con


def validate_internal_lb(super_client, lb_service, services,
                         host, con_port, lb_port):
    # Access each of the LB Agent from the client container
    lb_containers = get_service_container_list(super_client, lb_service)
    assert len(lb_containers) == lb_service.scale
    for lb_con in lb_containers:
        lb_ip = lb_con.primaryIpAddress
        target_count = 0
        for service in services:
            target_count = target_count + service.scale
        expected_lb_response = get_container_names_list(super_client,
                                                        services)
        assert len(expected_lb_response) == target_count
        # Validate port mapping
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host.ipAddresses()[0].address, username="root",
                    password="root", port=int(con_port))

        # Validate lb service from this container using LB agent's ip address
        cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + lb_ip + \
              ":"+lb_port+"/name.html;cat result.txt"
        logger.info(cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)

        response = stdout.readlines()
        assert len(response) == 1
        resp = response[0].strip("\n")
        logger.info("Actual wget Response" + str(resp))
        assert resp in (expected_lb_response)


def create_env_with_2_svc_hostnetwork(
        client, scale_svc, scale_consumed_svc, port, sshport,
        isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=False):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID_HOSTNET}
    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    if isnetworkModeHost_svc:
        launch_config_svc["networkMode"] = "host"
        launch_config_svc["labels"] = dns_labels
    else:
        launch_config_svc["ports"] = [port+":"+sshport+"/tcp"]
    if isnetworkModeHost_consumed_svc:
        launch_config_consumed_svc["networkMode"] = "host"
        launch_config_consumed_svc["labels"] = dns_labels
        launch_config_consumed_svc["ports"] = []
    # Create Environment
    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    # Create Consumed Service
    random_name = random_str()
    service_name = random_name.replace("-", "")

    consumed_service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service = client.wait_success(consumed_service)
    assert consumed_service.state == "inactive"

    return env, service, consumed_service


def create_env_with_2_svc_dns_hostnetwork(
        client, scale_svc, scale_consumed_svc, port,
        cross_linking=False, isnetworkModeHost_svc=False,
        isnetworkModeHost_consumed_svc=False):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID_HOSTNET}
    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    if isnetworkModeHost_svc:
        launch_config_svc["networkMode"] = "host"
        launch_config_svc["labels"] = dns_labels
    else:
        launch_config_svc["ports"] = [port+":33/tcp"]
    if isnetworkModeHost_consumed_svc:
        launch_config_consumed_svc["networkMode"] = "host"
        launch_config_consumed_svc["labels"] = dns_labels
        launch_config_consumed_svc["ports"] = []

    # Create Environment for dns service and client service
    env = create_env(client)

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config_svc,
                                    scale=scale_svc)

    service = client.wait_success(service)
    assert service.state == "inactive"

    # Force containers of 2 different services to be in different hosts
    hosts = client.list_host(kind='docker', removed_null=True, state='active')
    assert len(hosts) > 1
    # Create Consumed Service1
    if cross_linking:
        env_id = create_env(client).id
    else:
        env_id = env.id

    random_name = random_str()
    service_name = random_name.replace("-", "")

    launch_config_consumed_svc["requestedHostId"] = hosts[0].id
    consumed_service = client.create_service(
        name=service_name, environmentId=env_id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service = client.wait_success(consumed_service)
    assert consumed_service.state == "inactive"

    # Create Consumed Service2
    if cross_linking:
        env_id = create_env(client).id
    else:
        env_id = env.id

    random_name = random_str()
    service_name = random_name.replace("-", "")
    launch_config_consumed_svc["requestedHostId"] = hosts[1].id
    consumed_service1 = client.create_service(
        name=service_name, environmentId=env_id,
        launchConfig=launch_config_consumed_svc, scale=scale_consumed_svc)

    consumed_service1 = client.wait_success(consumed_service1)
    assert consumed_service1.state == "inactive"

    # Create DNS service

    dns = client.create_dnsService(name='WEB1',
                                   environmentId=env.id)
    dns = client.wait_success(dns)

    return env, service, consumed_service, consumed_service1, dns


def cleanup_images(client, delete_images):
    hosts = client.list_host(kind='docker', removed_null=True, state='active')
    print "To delete" + delete_images[0]
    for host in hosts:
        docker_client = get_docker_client(host)
        images = docker_client.images()
        for image in images:
            print image["RepoTags"][0]
            if image["RepoTags"][0] in delete_images:
                print "Found Match"
                docker_client.remove_image(image, True)
        images = docker_client.images()
        for image in images:
            assert ["RepoTags"][0] not in delete_images


@pytest.fixture(scope='session')
def certs(client, super_client, request):

    if len(cert_list.keys()) > 0:
        return

    domain_list = get_domains()
    print domain_list
    for domain in domain_list:
        cert = create_cert(client, domain)
        cert_list[domain] = cert

    def remove_certs():
        delete_all(client, cert_list.values())
    request.addfinalizer(remove_certs)


def get_cert(domain):
    return cert_list[domain]


def create_client_container_for_ssh(client, port):
    test_client_con = {}
    domain_list = get_domains()
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    assert len(hosts) > 0
    host = hosts[0]
    c = client.create_container(name="lb-test-client" + port,
                                networkMode=MANAGED_NETWORK,
                                imageUuid="docker:sangeetha/testclient",
                                ports=[port+":22/tcp"],
                                requestedHostId=host.id
                                )

    c = client.wait_success(c, 120)
    assert c.state == "running"
    time.sleep(5)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host.ipAddresses()[0].address, username="root",
                password="root", port=int(port))
    cmd = ""
    for domain in domain_list:
        cert, key, certChain = get_cert_for_domain(domain)
        if certChain:
            cp_cmd_cert = "echo '"+cert+"' > "+domain+"_chain.crt;"
        else:
            cp_cmd_cert = "echo '"+cert+"' >  "+domain+".crt;"

        cmd = cmd + cp_cmd_cert
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    print response
    test_client_con["container"] = c
    test_client_con["host"] = host
    test_client_con["port"] = port
    return test_client_con


def create_cert(client, name):
    cert, key, certChain = get_cert_for_domain(name)
    cert1 = client. \
        create_certificate(name=random_str(),
                           cert=cert,
                           key=key,
                           certChain=certChain)
    cert1 = client.wait_success(cert1)
    assert cert1.state == 'active'
    return cert1


def get_cert_for_domain(name):
    cert = readDataFile(SSLCERT_SUBDIR, name+".crt")
    key = readDataFile(SSLCERT_SUBDIR, name+".key")
    certChain = None
    if os.path.isfile(os.path.join(SSLCERT_SUBDIR, name + "_chain.crt")):
        certChain = readDataFile(SSLCERT_SUBDIR, name+"_chain.crt")
    return cert, key, certChain


def get_domains():
    domain_list_str = readDataFile(SSLCERT_SUBDIR, "certlist.txt").rstrip()
    domain_list = domain_list_str.split(",")
    return domain_list


def base_url():
    base_url = cattle_url()
    if (base_url.endswith('/v1/schemas')):
        base_url = base_url[:-7]
    elif (not base_url.endswith('/v1/')):
        if (not base_url.endswith('/')):
            base_url = base_url + '/v1/'
        else:
            base_url = base_url + 'v1/'
    return base_url


def readDataFile(data_dir, name):
    fname = os.path.join(data_dir, name)
    print fname
    is_file = os.path.isfile(fname)
    assert is_file
    with open(fname) as f:
        return f.read()


def get_env_service_by_name(client, env_name, service_name):
    env = client.list_environment(name=env_name)
    assert len(env) == 1
    service = client.list_service(name=service_name,
                                  environmentId=env[0].id,
                                  removed_null=True)
    assert len(service) == 1
    return env[0], service[0]


def check_for_appcookie_policy(super_client, client, lb_service, port,
                               target_services, cookie_name):
    container_names = get_container_names_list(super_client,
                                               target_services)
    lb_containers = get_service_container_list(super_client, lb_service)
    for lb_con in lb_containers:
        host = client.by_id('host', lb_con.hosts[0].id)

        url = "http://" + host.ipAddresses()[0].address + \
              ":" + port + "/name.html"
        headers = {"Cookie": cookie_name + "=test123"}

        check_for_stickiness(url, container_names, headers=headers)


def check_for_lbcookie_policy(super_client, client, lb_service, port,
                              target_services):
    container_names = get_container_names_list(super_client,
                                               target_services)
    lb_containers = get_service_container_list(super_client, lb_service)
    for lb_con in lb_containers:
        host = client.by_id('host', lb_con.hosts[0].id)

        url = "http://" + host.ipAddresses()[0].address + \
              ":" + port + "/name.html"

        session = requests.Session()
        r = session.get(url)
        sticky_response = r.text.strip("\n")
        logger.info("request: " + url)
        logger.info(sticky_response)
        r.close()
        assert sticky_response in container_names

        for n in range(0, 10):
            r = session.get(url)
            response = r.text.strip("\n")
            r.close()
            logger.info("request: " + url)
            logger.info(response)
            assert response == sticky_response


def check_for_balancer_first(super_client, client, lb_service, port,
                             target_services):
    container_names = get_container_names_list(super_client,
                                               target_services)
    lb_containers = get_service_container_list(super_client, lb_service)
    for lb_con in lb_containers:
        host = client.by_id('host', lb_con.hosts[0].id)

        url = "http://" + host.ipAddresses()[0].address + \
              ":" + port + "/name.html"
        check_for_stickiness(url, container_names)


def check_for_stickiness(url, expected_responses, headers=None):
        r = requests.get(url, headers=headers)
        sticky_response = r.text.strip("\n")
        logger.info(sticky_response)
        r.close()
        assert sticky_response in expected_responses

        for n in range(0, 10):
            r = requests.get(url, headers=headers)
            response = r.text.strip("\n")
            r.close()
            logger.info("request: " + url + " Header -" + str(headers))
            logger.info(response)
            assert response == sticky_response


class Context(object):
    def __init__(self, account=None, project=None, user_client=None,
                 client=None, host=None, agent_client=None, agent=None):
        self.account = account
        self.project = project
        self.agent = agent
        self.user_client = user_client
        self.agent_client = agent_client
        self.client = client
        self.host = host
        self.image_uuid = 'sim:{}'.format(random_str())
        self.nsp = self._get_nsp()
        self.host_ip = self._get_host_ip()

    def _get_nsp(self):
        if self.client is None:
            return None

        networks = filter(lambda x: x.kind == 'hostOnlyNetwork' and
                          x.accountId == self.project.id,
                          self.client.list_network(kind='hostOnlyNetwork'))
        assert len(networks) == 1
        nsps = super_client(None).reload(networks[0]).networkServiceProviders()
        assert len(nsps) == 1
        return nsps[0]

    def _get_host_ip(self):
        if self.host is None:
            return None

        ips = self.host.ipAddresses()
        assert len(ips) == 1
        return ips[0]

    def create_container(self, *args, **kw):
        c = self.create_container_no_success(*args, **kw)
        c = self.client.wait_success(c)
        try:
            if not kw['startOnCreate']:
                assert c.state == 'stopped'
                return c
        except KeyError:
            pass
        assert c.state == 'running'
        return c

    def create_container_no_success(self, *args, **kw):
        return self._create_container(self.client, *args, **kw)

    def _create_container(self, client, *args, **kw):
        if 'imageUuid' not in kw:
            kw['imageUuid'] = self.image_uuid
        c = client.create_container(*args, **kw)
        # Make sure it's waited for and reloaded w/ project client
        return self.client.wait_transitioning(c)

    def super_create_container(self, *args, **kw):
        c = self.super_create_container_no_success(*args, **kw)
        return self.client.wait_success(c)

    def super_create_container_no_success(self, *args, **kw):
        kw['accountId'] = self.project.id
        return self._create_container(super_client(None), *args, **kw)

    def delete(self, obj):
        if obj is None:
            return
        self.client.delete(obj)
        self.client.wait_success(obj)

    def wait_for_state(self, obj, state):
        obj = self.client.wait_success(obj)
        assert obj.state == state
        return obj


def create_context(admin_user_client, create_project=False, add_host=False,
                   kind=None, name=None):
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    if name is None:
        name = 'Integration Test User {}'.format(now)
        project_name = 'Integration Test Project {}'.format(now)
    else:
        project_name = name + '\'s Project {}'.format(now)

    if kind is None:
        kind = 'user'

    account = admin_user_client.create_account(name=name, kind=kind)
    account = admin_user_client.wait_success(account)
    key = admin_user_client.create_api_key(accountId=account.id)
    admin_user_client.wait_success(key)
    user_client = api_client(key.publicValue, key.secretValue)
    try:
        account = user_client.reload(account)
    except KeyError:
        # The account type can't see the account obj
        pass

    project = None
    project_client = None
    agent_client = None
    agent = None

    if create_project:
        project = user_client.create_project(name=project_name, members=[{
            'role': 'owner',
            'externalId': acc_id(user_client),
            'externalIdType': 'rancher_id'
        }])
        project = user_client.wait_success(project)
        # This is not proper yet because basic auth can't be used w/ Projects
        project_key = admin_user_client.create_api_key(accountId=project.id)
        admin_user_client.wait_success(project_key)
        project_client = api_client(project_key.publicValue,
                                    project_key.secretValue)
        project = project_client.reload(project)

    if create_project and add_host:
        host, agent, agent_client = \
            register_simulated_host(project_client, return_agent=True)
    else:
        host = None

    return Context(account=account, project=project, user_client=user_client,
                   client=project_client, host=host,
                   agent_client=agent_client, agent=agent)




def api_client(access_key, secret_key):
    return cattle.from_env(url=cattle_url(),
                           cache=False,
                           access_key=access_key,
                           secret_key=secret_key)


def one(method, *args, **kw):
    ret = method(*args, **kw)
    assert len(ret) == 1
    return ret[0]


def register_simulated_host(client_or_context, return_agent=False):
    client = client_or_context
    if isinstance(client_or_context, Context):
        client = client_or_context.client

    def do_ping():
        ping = one(super_client(None).list_task, name='agent.ping')
        ping.execute()

    def check():
        hosts = super_client(None).list_host(agentId=agents[0].id)
        if len(hosts) > 0:
            return hosts[0]
        do_ping()

    tokens = client.list_registration_token()
    if len(tokens) == 0:
        token = client.wait_success(client.create_registration_token())
    else:
        token = tokens[0]

    c = api_client('registrationToken', token.token)
    key = random_str()

    # Now this where we hack things up to make it a simulator
    s = super_client(None)
    register = s.create_register(key=key,
                                 accountId=token.accountId,
                                 agentUriFormat='sim://%s')
    # End hacking...

    register = c.wait_success(register)
    register = c.list_register(key=key)[0]

    c = api_client(register.accessKey, register.secretKey)
    agents = c.list_agent()

    keys = s.list_credential(publicValue=register.accessKey)
    assert len(keys) == 1

    assert len(agents) == 1

    s.update(agents[0], uri='sim://{}'.format(key))

    host = wait_for(check)
    host = client.wait_success(host)
    s.wait_success(agents[0])

    if return_agent:
        return host, keys[0].account(), c
    else:
        return host


def auth_check(schema, id, access, props=None):
    type = schema.types[id]
    access_actual = set()

    try:
        if 'GET' in type.collectionMethods:
            access_actual.add('r')
    except AttributeError:
        pass

    try:
        if 'GET' in type.resourceMethods:
            access_actual.add('r')
    except AttributeError:
        pass

    try:
        if 'POST' in type.collectionMethods:
            access_actual.add('c')
    except AttributeError:
        pass

    try:
        if 'DELETE' in type.resourceMethods:
            access_actual.add('d')
    except AttributeError:
        pass

    try:
        if 'PUT' in type.resourceMethods:
            access_actual.add('u')
    except AttributeError:
        pass

    assert access_actual == set(access)

    if props is None:
        return 1

    for i in ['name', 'description']:
        if i not in props and i in type.resourceFields:
            acl = set('r')
            if 'c' in access_actual:
                acl.add('c')
            if 'u' in access_actual:
                acl.add('u')
            props[i] = ''.join(acl)

    for i in ['created', 'removed', 'transitioning', 'transitioningProgress',
              'removeTime', 'transitioningMessage', 'id', 'uuid', 'kind',
              'state']:
        if i not in props and i in type.resourceFields:
            props[i] = 'r'

    prop = set(props.keys())
    prop_actual = set(type.resourceFields.keys())

    assert prop_actual == prop

    for name, field in type.resourceFields.items():
        assert name in props

        prop = set(props[name])
        prop_actual = set('r')

        prop.add(name)
        prop_actual.add(name)

        if field.create and 'c' in access_actual:
            prop_actual.add('c')
        if field.update and 'u' in access_actual:
            prop_actual.add('u')
        if field.readOnCreateOnly:
            prop_actual.add('o')

        assert prop_actual == prop

    return 1


@pytest.fixture(scope='session')
def admin_user_client(super_client):
    admin_account = super_client.list_account(kind='admin', uuid='admin')[0]
    key = super_client.create_api_key(accountId=admin_account.id)
    super_client.wait_success(key)

    client = api_client(key.publicValue, key.secretValue)
    return client


def resource_action_check(schema, id, actions):
    action_keys = set(actions)
    keys_received = set(schema.types[id].resourceActions.keys())
    assert keys_received == action_keys

