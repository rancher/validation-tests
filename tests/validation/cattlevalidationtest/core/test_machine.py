from common_fixtures import *  # NOQA

DEFAULT_TIMEOUT = 300

if_machine_digocean = pytest.mark.skipif(
    os.environ.get('DIGITALOCEAN_KEY') is None,
    reason='DIGITALOCEAN_KEY is not set')

if_machine_virtualbox = pytest.mark.skipif(
    os.environ.get('TEST_VIRTUALBOX') != "true",
    reason='TEST_VIRTUALBOX is not set to "true"')


@if_machine_digocean
def test_digital_ocean(client):
    access_key = os.environ.get('DIGITALOCEAN_KEY')
    name = random_str()
    create_args = {"name": name,
                   "digitaloceanConfig": {
                       "accessToken": access_key
                   }}
    lifecycle(client, create_args)


@if_machine_virtualbox
def test_virtualbox(client):
    name = random_str()
    create_args = {"name": name, "virtualboxConfig": {}}
    lifecycle(client, create_args)


def lifecycle(client, create_args):
    machine = None
    try:
        machine = client.create_machine(**create_args)

        machine = client.wait_success(machine, timeout=DEFAULT_TIMEOUT)
        assert machine.state == 'active'

        # Wait until host shows up with same physicalHostId
        machine = wait_for_host(client, machine)

        hosts = machine.hosts()
        assert len(hosts) == 1
        host = hosts[0]
        client.wait_success(host, timeout=DEFAULT_TIMEOUT)
        assert host.state == 'active'
        assert machine.accountId == host.accountId

        machine = client.reload(machine)
        machine = client.wait_success(machine.remove(),
                                      timeout=DEFAULT_TIMEOUT)
        assert machine.state == 'removed'

        host = client.wait_success(client.reload(host),
                                   timeout=DEFAULT_TIMEOUT)
        assert host.state == 'removed'

    finally:
        if machine and machine.state != "removed":
            machine = client.reload(machine)
            machine = client.wait_success(machine.remove(),
                                          timeout=DEFAULT_TIMEOUT)
            assert machine.state == 'removed'


def wait_for_host(client, machine, timeout=DEFAULT_TIMEOUT):
    start = time.time()
    machine = client.reload(machine)
    while len(machine.hosts()) < 1:
        time.sleep(1)
        machine = client.reload(machine)
        if time.time() - start > timeout:
            raise Exception('Timeout waiting for host to be created.')

    return machine
