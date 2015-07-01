import logging

from common_fixtures import *  # NOQA

DEFAULT_TIMEOUT = 900

subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')
subscription_cert = os.environ.get('AZURE_SUBSCRIPTION_CERT')

# Use azure settings from environment variables , if set
i = 'b39f27a8b8c64d52b05eac6a62ebad85__'
i = i + 'Ubuntu-14_04_1-LTS-amd64-server-20140927-en-us-30GB'
image = os.environ.get('AZURE_IMAGE', i)
location = os.environ.get('AZURE_LOCATION', "West US")
username = os.environ.get('AZURE_USERNAME', "")
password = os.environ.get('AZURE_PASSWORD', "")
size = os.environ.get('AZURE_SIZE', "Small")

if_machine_azure = pytest.mark.skipif(
    not os.environ.get('AZURE_SUBSCRIPTION_ID') or
    not os.environ.get('AZURE_SUBSCRIPTION_CERT'),
    reason='Azure SubscriptionId/SubscriptionCert/AuthToken is not set')


# Get logger
logger = logging.getLogger(__name__)


@pytest.fixture(scope='session', autouse=True)
def register_host(admin_client):
    setting = admin_client.by_id_setting("api.host")
    if setting.value is None or len(setting.value) == 0:
        test_url = cattle_url()
        start = test_url.index("//") + 2
        api_host = test_url[start:]
        admin_client.create_setting(name="api.host", value=api_host)
        time.sleep(15)


@if_machine_azure
def test_azure_machine_all_params(client):
    name = random_str()
    create_args = {"name": name,
                   "azureConfig": {"subscriptionId": subscription_id,
                                   "subscriptionCert": subscription_cert,
                                   "image": image,
                                   "location": location,
                                   "username": username,
                                   "password": password,
                                   "size": size}}
    expected_values = {"subscriptionId": subscription_id,
                       "subscriptionCert": subscription_cert,
                       "image": image,
                       "location": location,
                       "username": username,
                       "password": password,
                       "size": size}
    azure_machine_life_cycle(client, create_args, expected_values)


def azure_machine_life_cycle(client, configs, expected_values):
    machine = client.create_machine(**configs)

    machine = client.wait_success(machine, timeout=DEFAULT_TIMEOUT)
    assert machine.state == 'active'

    # Wait until host shows up with some physicalHostId
    machine = wait_for_host(client, machine)
    host = machine.hosts()[0]
    assert host.state == 'active'
    assert machine.accountId == host.accountId
    # Remove the machine and make sure that the host
    # and the machine get removed

    machine = client.wait_success(machine.remove())
    assert machine.state == 'removed'

    host = client.reload(machine.hosts()[0])
    assert host.state == 'removed'


def wait_for_host(client, machine):
    wait_for_condition(client,
                       machine,
                       lambda x: len(x.hosts()) == 1,
                       lambda x: 'Number of hosts associated with machine ' +
                                 str(len(x.hosts())),
                       DEFAULT_TIMEOUT)

    host = machine.hosts()[0]
    host = wait_for_condition(client,
                              host,
                              lambda x: x.state == 'active',
                              lambda x: 'Host state is ' + x.state
                              )
    return machine
