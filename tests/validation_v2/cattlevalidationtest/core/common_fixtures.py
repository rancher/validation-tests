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
import pickle

TEST_IMAGE_UUID = os.environ.get('CATTLE_TEST_AGENT_IMAGE',
                                 'docker:cattle/test-agent:v7')

SSH_HOST_IMAGE_UUID = os.environ.get('CATTLE_SSH_HOST_IMAGE',
                                     'docker:rancher/ssh-host-container:' +
                                     'v0.1.0')

SOCAT_IMAGE_UUID = os.environ.get('CATTLE_CLUSTER_SOCAT_IMAGE',
                                  'docker:rancher/socat-docker:v0.2.0')
SSH_IMAGE_UUID_HOSTNET = "docker:sangeetha/testclient33:latest"

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"
LB_HOST_ROUTING_IMAGE_UUID = "docker:sangeetha/testnewhostrouting:latest"
SSH_IMAGE_UUID_HOSTNET = "docker:sangeetha/testclient33:latest"

DEFAULT_TIMEOUT = 45

PRIVATE_KEY_FILENAME = "/tmp/private_key_host_ssh"
HOST_SSH_TEST_ACCOUNT = "ranchertest"
HOST_SSH_PUBLIC_PORT = 2222


socat_container_list = []
rancher_compose_con = {"container": None, "host": None, "port": "7878"}
CONTAINER_STATES = ["running", "stopped", "stopping"]

MANAGED_NETWORK = "managed"
UNMANAGED_NETWORK = "bridge"

dns_labels = {"io.rancher.container.dns": "true",
              "io.rancher.scheduler.affinity:container_label_ne":
              "io.rancher.stack_service.name=${stack_name}/${service_name}"}

root_dir = os.environ.get('TEST_ROOT_DIR',
                          os.path.join(os.path.dirname(__file__), 'tests',
                                       'validation_v2'))
compose_template_dir = os.path.join(root_dir, 'data', 'compose')

log_dir = os.path.join(root_dir, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logfile = os.path.join(log_dir, 'test.log')
FORMAT = "\n[ %(asctime)s %(levelname)s %(filename)s:%(lineno)s " \
         "- %(funcName)20s() ] %(message)s \n"
logging.basicConfig(level=logging.INFO, format=FORMAT,
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)


def format(d, tab=4):
    s = ['{\n']
    for k, v in d.items():
        if isinstance(v, dict):
            v = format(v, tab+1)
        else:
            v = repr(v)

        s.append('%s%r: %s,\n' % ('  '*tab, k, v))
    s.append('%s}' % ('  '*tab))
    return ''.join(s)


def save(uuids, obj):
    filename = str(obj.__class__).split(".")[-1:][0]
    print "filename is:", str(filename)
    print "full path:", os.path.join(root_dir, filename)
    with open(os.path.join(root_dir, filename), 'wb') as handle:
        pickle.dump(uuids, handle)


def load(self):
    filename = str(self.__class__).split(".")[-1:][0]
    print "filename is:", str(filename)
    print "full path:", os.path.join(root_dir, filename)
    with open(os.path.join(root_dir, filename), 'rb') as handle:
        uuids = pickle.load(handle)
        os.remove(os.path.join(root_dir, filename))
        return uuids


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
    return 'test-{0}-{1}'.format(random_num(), int(time.time()))


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
    logger.info("Deleting the env: %s", items)
    wait_for = []
    for i in items:
        client.delete(i)
        wait_for.append(client.reload(i))

    wait_all_success(client, items, timeout=1800)


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


def wait_for_scale_to_adjust(super_client, service):

    service = super_client.wait_success(service)
    logger.info("service : %s", format(service))
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    start = time.time()

    while len(instance_maps) != service.scale:
        time.sleep(.5)
        instance_maps = super_client.list_serviceExposeMap(
            serviceId=service.id, state="active")
        logger.debug("instance_maps: %s", format(instance_maps))
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


def get_service_container_list(super_client, service):

    logger.debug("service is: %s", format(service))
    container = []
    all_instance_maps = \
        super_client.list_serviceExposeMap(serviceId=service.id)
    instance_maps = []
    for instance_map in all_instance_maps:
        if instance_map.state not in ("removed", "removing"):
            instance_maps.append(instance_map)
    logger.info("instance_maps : %s", instance_maps)

    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        assert c.state in CONTAINER_STATES
        containers = super_client.list_container(
            externalId=c.externalId,
            include="hosts")
        assert len(containers) == 1
        container.append(containers[0])
        logger.info("container : %s", format(containers[0]))
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
                                         services, lb_service):

    lbs = client.list_loadBalancer(serviceId=lb_service.id)
    assert len(lbs) == 1

    lb = lbs[0]

    # Wait for host maps to get created and reach "active" state
    host_maps = wait_until_host_map_created(client, lb, lb_service.scale, 60)
    assert len(host_maps) == lb_service.scale

    logger.info("host_maps - " + str(host_maps))

    # Wait for target maps to get created and reach "active" state
    all_target_count = 0
    for service in services:
        all_target_count = all_target_count + service.scale
    target_maps = wait_until_target_map_created(
        client, lb, all_target_count, 60)
    logger.info(target_maps)

    wait_for_config_propagation(super_client, lb, host_maps)
    time.sleep(5)

    lb_containers = get_service_container_list(super_client, lb_service)
    assert len(lb_containers) == lb_service.scale

    # Get haproxy config from Lb Agents
    for lb_con in lb_containers:
        host = super_client.by_id('host', lb_con.hosts[0].id)
        docker_client = get_docker_client(host)
        haproxy = docker_client.copy(
            lb_con.externalId, "/etc/haproxy/haproxy.cfg")
        print "haproxy: " + haproxy.read()


def validate_lb_service_for_external_services(super_client, client, lb_service,
                                              port, container_list,
                                              hostheader=None, path=None):
    container_names = []
    for con in container_list:
        container_names.append(con.externalId[:12])
    validate_lb_service_con_names(super_client, client, lb_service, port,
                                  container_names, hostheader, path)


def validate_lb_service(super_client, client, lb_service, port,
                        target_services, hostheader=None, path=None):
    target_count = 0
    for service in target_services:
        target_count = target_count + service.scale
    container_names = get_container_names_list(super_client,
                                               target_services)
    logger.info(container_names)
    assert len(container_names) == target_count
    validate_lb_service_con_names(super_client, client, lb_service, port,
                                  container_names, hostheader, path)


def validate_lb_service_con_names(super_client, client, lb_service, port,
                                  container_names,
                                  hostheader=None, path=None):
    lbs = client.list_loadBalancer(serviceId=lb_service.id)
    assert len(lbs) == 1

    lb = lbs[0]
    print "\n\n\n lb is:", lb
    host_maps = client.list_loadBalancerHostMap(loadBalancerId=lb.id,
                                                removed_null=True,
                                                state="active")
    print "\n\n\n host_maps is:", host_maps
    print "\n\n\n length of host_maps is:", len(host_maps)
    print "\n\n\n Expected lb service scale is:", lb_service.scale
    assert len(host_maps) == lb_service.scale
    lb_hosts = []

    for host_map in host_maps:
        host = client.by_id('host', host_map.hostId)
        lb_hosts.append(host)
        logger.info("host: " + host.name)

    for host in lb_hosts:
        wait_until_lb_is_active(host, port)
        if hostheader is not None or path is not None:
            check_round_robin_access(container_names, host, port,
                                     hostheader, path)
        else:
            check_round_robin_access(container_names, host, port)


def wait_until_target_map_created(client, lb, count, timeout=30):
    start = time.time()
    target_maps = client.list_loadBalancerTarget(loadBalancerId=lb.id,
                                                 removed_null=True,
                                                 state="active")
    while len(target_maps) != count:
        time.sleep(.5)
        target_maps = client. \
            list_loadBalancerTarget(loadBalancerId=lb.id, removed_null=True,
                                    state="active")
        if time.time() - start > timeout:
            raise Exception('Timed out waiting for target map creation')
    return target_maps


def wait_until_host_map_created(client, lb, count, timeout=30):
    start = time.time()
    host_maps = client.list_loadBalancerHostMap(loadBalancerId=lb.id,
                                                removed_null=True,
                                                state="active")
    while len(host_maps) != count:
        time.sleep(.5)
        host_maps = client. \
            list_loadBalancerHostMap(loadBalancerId=lb.id, removed_null=True,
                                     state="active")
        if time.time() - start > timeout:
            raise Exception('Timed out waiting for host map creation')
    return host_maps


def wait_until_target_maps_removed(super_client, lb, consumed_service):
    instance_maps = super_client.list_serviceExposeMap(
        serviceId=consumed_service.id)
    for instance_map in instance_maps:
        target_maps = super_client.list_loadBalancerTarget(
            loadBalancerId=lb.id, instanceId=instance_map.instanceId)
        assert len(target_maps) == 1
        target_map = target_maps[0]
        wait_for_condition(
            super_client, target_map,
            lambda x: x.state == "removed",
            lambda x: 'State is: ' + x.state)


def wait_until_lb_is_active(host, port, timeout=30):
    start = time.time()
    while check_for_no_access(host, port):
        time.sleep(.5)
        print "No access yet"
        if time.time() - start > timeout:
            raise Exception('Timed out waiting for LB to become active')
    return


def check_for_no_access(host, port):
    try:
        url = "http://" + host.ipAddresses()[0].address + ":" +\
              port + "/name.html"
        requests.get(url)
        return False
    except requests.ConnectionError:
        logger.info("Connection Error - " + url)
        return True


def validate_linked_service(super_client, service, consumed_services,
                            exposed_port, exclude_instance=None,
                            exclude_instance_purged=False):
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
                        expected_link_response.append(con_host.name)
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
            cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + \
                  consumed_service.name + ":80/name.html;cat result.txt"
            logger.info(cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            assert len(response) == 1
            resp = response[0].strip("\n")
            logger.info("Actual wget Response" + str(resp))
            assert resp in (expected_link_response)

            # Validate DNS resolution using dig
            cmd = "dig " + consumed_service.name + " +short"
            logger.info(cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd)

            response = stdout.readlines()
            logger.info("Actual dig Response" + str(response))

            expected_entries_dig = consumed_service.scale
            if exclude_instance is not None:
                expected_entries_dig = expected_entries_dig - 1

            assert len(response) == expected_entries_dig

            for resp in response:
                dns_response.append(resp.strip("\n"))

            for address in expected_dns_list:
                assert address in dns_response


def validate_dns_service(super_client, service, consumed_services,
                         exposed_port, dnsname, exclude_instance=None,
                         exclude_instance_purged=False):
    time.sleep(5)

    service_containers = get_service_container_list(super_client, service)
    assert len(service_containers) == service.scale

    for con in service_containers:
        logger.info("service container is: %s", con)
        host = super_client.by_id('host', con.hosts[0].id)
        logger.info("host is: %s", format(host))
        containers = []
        expected_dns_list = []
        expected_link_response = []
        dns_response = []

        for consumed_service in consumed_services:
            logger.info("consumed service is %s", format(consumed_service))
            cons = get_service_container_list(super_client, consumed_service)
            logger.info("cons : %s", cons)
            logger.info("containers length is %s", len(cons))
            if exclude_instance_purged:
                assert len(cons) == consumed_service.scale - 1
            else:
                assert len(cons) == consumed_service.scale
            containers = containers + cons
        logger.info("containers length is: %s", len(containers))

        for con in containers:
            logger.info("con is %s", format(con))
            if (exclude_instance is not None) \
                    and (con.id == exclude_instance.id):
                logger.info("Excluded from DNS and wget list:" + con.name)
            else:
                if con.networkMode == "host":
                    con_host = super_client.by_id('host', con.hosts[0].id)
                    expected_dns_list.append(con_host.ipAddresses()[0].address)
                    expected_link_response.append(con_host.name)
                else:
                    expected_dns_list.append(con.primaryIpAddress)
                    expected_link_response.append(con.externalId[:12])

        logger.info("Expected dig response List" + str(expected_dns_list))
        logger.info("Expected wget response List" +
                    str(expected_link_response))

        # Validate port mapping
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info("Host ipAddresses: %s", format(host.ipAddresses()))
        logger.info("Host ip is: %s", format(host.ipAddresses()[0]))
        logger.info("Exposed port is: %s", exposed_port)
        os.system("ssh-copy-id root@"+host.ipAddresses()[0].address)
        ssh.connect(host.ipAddresses()[0].address, username="root",
                    password="root", port=int(exposed_port))

        # Validate link containers
        logger.info("dnsname is: %s", dnsname)
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
            expected_link_response = "About Google"

            # Validate port mapping
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host.ipAddresses()[0].address, username="root",
                        password="root", port=int(exposed_port))
            cmd = "wget -O result.txt --timeout=20 --tries=1 http://" + \
                  ext_service.name + ";cat result.txt"
            print cmd

            # Validate link containers mutliple times
            for i in range(0, 10):
                stdin, stdout, stderr = ssh.exec_command(cmd)
                response = stdout.readlines()
                print "Actual wget Response" + str(response)
                assert expected_link_response in str(response)


@pytest.fixture(scope='session')
def rancher_compose_container(admin_client, client, request):
    if rancher_compose_con["container"] is not None:
        return
    setting = admin_client.by_id_setting(
        "default.cattle.rancher.compose.linux.url")
    rancher_compose_url = setting.value
    cmd1 = \
        "wget " + rancher_compose_url
    cmd2 = "tar xvf rancher-compose-linux-amd64.tar.gz"

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


def launch_rancher_compose(client, env, testname):
    compose_configs = env.exportconfig()
    docker_compose = compose_configs["dockerComposeConfig"]
    rancher_compose = compose_configs["rancherComposeConfig"]

    access_key = client._access_key
    secret_key = client._secret_key
    docker_filename = testname + "-docker-compose.yml"
    rancher_filename = testname + "-rancher-compose.yml"
    project_name = env.name
    cmd1 = "export RANCHER_URL=" + cattle_url()
    cmd2 = "export RANCHER_ACCESS_KEY=" + access_key
    cmd3 = "export RANCHER_SECRET_KEY=" + secret_key
    cmd4 = "cd rancher-compose-v*"
    cmd5 = "echo '" + docker_compose + "' > " + docker_filename
    cmd6 = "echo '" + rancher_compose + "' > " + rancher_filename
    cmd7 = "./rancher-compose -p " + project_name + " -f " + docker_filename\
           + " -r " + rancher_filename + " up -d"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        rancher_compose_con["host"].ipAddresses()[0].address, username="root",
        password="root", port=int(rancher_compose_con["port"]))
    cmd = cmd1+";"+cmd2+";"+cmd3+";"+cmd4+";"+cmd5+";"+cmd6+";"+cmd7
    print cmd
    stdin, stdout, stderr = ssh.exec_command(cmd)
    response = stdout.readlines()
    print "\n\n\n response is:", str(response)
    expected_resp = "Creating stack " + project_name
    found = False
    for resp in response:
        if expected_resp in resp:
            found = True
    assert found


def create_env_with_svc_and_lb(testname, client, scale_svc, scale_lb, port,
                               internal=False):

    launch_config_svc = {"imageUuid": WEB_IMAGE_UUID}

    if internal:
        launch_config_lb = {"expose": [port+":80"]}
    else:
        launch_config_lb = {"ports": [port+":80"]}

    # Create Environment
    env = create_env(testname, client)

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
    service_name = random_name.replace("-", "") + "-LB"

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=scale_lb)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    return env, service, lb_service


def create_env_with_ext_svc_and_lb(testname, client, scale_lb, port):

    launch_config_lb = {"ports": [port+":80"]}

    env, service, ext_service, con_list = create_env_with_ext_svc(
        testname, client, 1, port)

    # Create LB Service
    random_name = random_str()
    service_name = random_name.replace("-", "") + "-LB"

    lb_service = client.create_loadBalancerService(
        name=service_name,
        environmentId=env.id,
        launchConfig=launch_config_lb,
        scale=scale_lb)

    lb_service = client.wait_success(lb_service)
    assert lb_service.state == "inactive"

    return env, lb_service, ext_service, con_list


def create_env_with_2_svc(testname, client, scale_svc, scale_consumed_svc,
                          port):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    # Create Environment
    env = create_env(testname, client)

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


def create_env_with_2_svc_dns(testname, client, scale_svc, scale_consumed_svc,
                              port,
                              cross_linking=False):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    launch_config_consumed_svc = {"imageUuid": WEB_IMAGE_UUID}

    # Create Environment for dns service and client service
    env = create_env(testname, client)

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
        env_id = create_env(testname, client).id
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
        env_id = create_env(testname, client).id
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


def create_env_with_ext_svc(testname, client, scale_svc, port, hostname=False):

    launch_config_svc = {"imageUuid": SSH_IMAGE_UUID,
                         "ports": [port+":22/tcp"]}

    # Create Environment
    env = create_env(testname, client)

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


def create_env_and_svc(testname, client, launch_config, scale):

    env = create_env(testname, client)
    service = create_svc(client, env, launch_config, scale)
    return service, env


def check_container_in_service(super_client, service):

    container_list = get_service_container_list(super_client, service)
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


def create_svc(client, env, launch_config, scale):

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(name=service_name,
                                    environmentId=env.id,
                                    launchConfig=launch_config,
                                    scale=scale)

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


def get_service_containers_with_name(super_client, service, name):

    container = []
    all_instance_maps = \
        super_client.list_serviceExposeMap(serviceId=service.id)
    instance_maps = []
    for instance_map in all_instance_maps:
        if instance_map.state not in ("removed", "removing"):
            instance_maps.append(instance_map)

    nameformat = re.compile(name + "_[0-9]{1,2}")
    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        print c.name
        if nameformat.match(c.name):
            containers = super_client.list_container(
                externalId=c.externalId,
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


def validate_lb_service_for_no_access(client, lb_service, port,
                                      hostheader, path):

    lbs = client.list_loadBalancer(serviceId=lb_service.id)
    assert len(lbs) == 1

    lb = lbs[0]
    host_maps = wait_until_host_map_created(client, lb, lb_service.scale)
    assert len(host_maps) == lb_service.scale

    lb_hosts = []

    for host_map in host_maps:
        host = client.by_id('host', host_map.hostId)
        lb_hosts.append(host)
        logger.info("host: " + host.name)

    for host in lb_hosts:
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
        logger.info(response)
        assert response == con_hostname_ordered[i]
        i = i + 1
        if i == len(con_hostname_ordered):
            i = 0


def create_env_with_multiple_svc_and_lb(testname, client, scale_svc, scale_lb,
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
    env = create_env(testname, client)

    # Create Service
    for i in range(0, count):
        random_name = random_str()
        service_name = random_name.replace("-", "")
        if crosslinking:
            env_serv = create_env(testname, client)
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
    service_name = random_name.replace("-", "") + "-LB"

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


def wait_for_config_propagation(super_client, lb, host_maps, timeout=30):
    for host_map in host_maps:
        uri = 'delegate:///?lbId={}&hostMapId={}'.\
            format(get_plain_id(super_client, lb),
                   get_plain_id(super_client, host_map))
        agents = super_client.list_agent(uri=uri)
        assert len(agents) == 1
        agent = agents[0]
        assert agent is not None
        item = get_config_item(agent, "haproxy")
        start = time.time()
        print "requested_version " + str(item.requestedVersion)
        print "applied_version " + str(item.appliedVersion)
        while item.requestedVersion != item.appliedVersion:
            print "requested_version " + str(item.requestedVersion)
            print "applied_version " + str(item.appliedVersion)
            time.sleep(.5)
            agent = super_client.reload(agent)
            item = get_config_item(agent, "haproxy")
            if time.time() - start > timeout:
                raise Exception('Timed out waiting for config propagation')
            return


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


def create_env(testname, client):
    # random_name = random_str()
    # env_name = testname + "-" + random_name.replace("-", "")
    env = client.create_environment(name=testname)
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
        testname, client, scale_svc, scale_consumed_svc, port, sshport,
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
    env = create_env(testname, client)

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
        testname, client, scale_svc, scale_consumed_svc, port,
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
    env = create_env(testname, client)

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
        env_id = create_env(testname, client).id
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
        env_id = create_env(testname, client).id
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


def base_url():
    base_url = cattle_url()
    if (base_url.endswith('/v1/schemas')):
        base_url = base_url[:-7]
    elif (not base_url.endswith('/v1/')):
        base_url = base_url + '/v1/'
    return base_url
