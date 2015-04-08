from common_fixtures import *  # NOQA
from docker import Client, tls

TEST_IMAGE = 'ibuildthecloud/helloworld'


def _native_doc_check():
    return os.environ.get('DOCKER_HOST') is None or os.environ.get(
        'DOCKER_TEST') == 'false'


if_native_docker = pytest.mark.skipif(_native_doc_check(),
                                      reason='Environment not configured for '
                                             'native docker tests.')


@pytest.fixture(scope='module')
def docker_client():
    host = os.getenv('DOCKER_HOST')
    cert_path = os.getenv('DOCKER_CERT_PATH')
    tls_verify = os.getenv('DOCKER_TLS_VERIFY')
    api_version = os.getenv('DOCKER_API_VERSION', '1.15')

    params = {}
    if host:
        params['base_url'] = (host.replace('tcp://', 'https://')
                              if tls_verify else host)
    if host and tls_verify and cert_path:
        params['tls'] = tls.TLSConfig(
            client_cert=(os.path.join(cert_path, 'cert.pem'),
                         os.path.join(cert_path, 'key.pem')),
            ca_cert=os.path.join(cert_path, 'ca.pem'),
            verify=True,
            assert_hostname=False)

    if not params:
        raise Exception("Can't configure docker client. No DOCKER_HOST set.")

    params['version'] = api_version

    return Client(**params)


@pytest.fixture(scope='module')
def pull_images(docker_client):
    image = (TEST_IMAGE, 'latest')
    images = docker_client.images(image[0])
    if not images:
        docker_client.pull(image[0], image[1])


@if_native_docker
def test_native_unmanaged_network(docker_client, admin_client, pull_images):
    name = 'native-%s' % random_str()
    d_container = docker_client.create_container(TEST_IMAGE,
                                                 name=name)
    docker_client.start(d_container)
    inspect = docker_client.inspect_container(d_container)

    def check():
        containers = admin_client.list_container(name=name)
        return len(containers) > 0

    wait_for(check)

    r_containers = admin_client.list_container(name=name)
    assert len(r_containers) == 1
    c = r_containers[0]
    c = admin_client.wait_success(c)

    assert c.externalId == d_container['Id']
    assert c.state == 'running'
    assert c.primaryIpAddress == inspect['NetworkSettings']['IPAddress']


@if_native_docker
def test_native_managed_network(docker_client, admin_client, super_client,
                                pull_images):
    name = 'native-%s' % random_str()
    d_container = docker_client.create_container(TEST_IMAGE,
                                                 name=name,
                                                 environment=[
                                                     'RANCHER_NETWORK=true'])
    docker_client.start(d_container)
    inspect = docker_client.inspect_container(d_container)

    def check():
        containers = admin_client.list_container(name=name)
        return len(containers) > 0

    wait_for(check)

    r_containers = admin_client.list_container(name=name)
    assert len(r_containers) == 1
    c = r_containers[0]
    c = admin_client.wait_success(c)

    assert c.externalId == d_container['Id']
    assert c.state == 'running'
    assert c.primaryIpAddress != inspect['NetworkSettings']['IPAddress']
    nics = super_client.reload(c).nics()
    assert len(nics) == 1
    assert c.primaryIpAddress == nics.data[0].ipAddresses().data[0].address

    # Let's test more of the life cycle
    c = admin_client.wait_success(c.stop(timeout=0))
    assert c.state == 'stopped'

    c = admin_client.wait_success(c.start(timeout=0))
    assert c.state == 'running'

    c = admin_client.wait_success(c.restart(timeout=0))
    assert c.state == 'running'

    c = admin_client.wait_success(c.stop(timeout=0))
    assert c.state == 'stopped'

    c = admin_client.wait_success(c.remove(timeout=0))
    assert c.state == 'removed'

    c = admin_client.wait_success(c.purge(timeout=0))
    assert c.state == 'purged'


@if_native_docker
def test_native_not_started(docker_client, admin_client, super_client,
                            pull_images):
    name = 'native-%s' % random_str()
    d_container = docker_client.create_container(TEST_IMAGE,
                                                 name=name,
                                                 environment=[
                                                     'RANCHER_NETWORK=true'])

    def check():
        containers = admin_client.list_container(name=name)
        return len(containers) > 0

    wait_for(check)

    r_containers = admin_client.list_container(name=name)
    assert len(r_containers) == 1
    c = r_containers[0]
    c = admin_client.wait_success(c)
    c_id = c.id

    assert c.externalId == d_container['Id']
    assert c.state == 'running'

    def stopped_check():
        c = admin_client.by_id_container(c_id)
        return c.state == 'stopped'

    wait_for(stopped_check)

    nics = super_client.reload(c).nics()
    assert len(nics) == 1
    assert c.primaryIpAddress == nics.data[0].ipAddresses().data[0].address


@if_native_docker
def test_native_removed(docker_client, admin_client, pull_images):
    name = 'native-%s' % random_str()
    d_container = docker_client.create_container(TEST_IMAGE,
                                                 name=name)
    docker_client.remove_container(d_container)

    def check():
        containers = admin_client.list_container(name=name)
        return len(containers) > 0

    wait_for(check)

    r_containers = admin_client.list_container(name=name)
    assert len(r_containers) == 1
    rc = r_containers[0]
    rc = admin_client.wait_success(rc)

    assert rc.externalId == d_container['Id']
