from common_fixtures import *  # NOQA
import traceback
import logging

DEFAULT_TIMEOUT = 900

# Digital Ocean configurations
access_key = os.environ.get('DIGITALOCEAN_KEY')
image_name = "ubuntu-14-04-x64"
region = "sfo1"
size = "1gb"

# Digital Ocean default configurations
default_size = "512mb"
default_image_name = "ubuntu-14-04-x64"
default_region = "nyc3"


# Digital Ocean Error Messages
error_msg_auth_failure = "Invalid access token"

error_msg_invalid_region = "digitalocean requires a valid region"


if_machine_digocean = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY'),
    reason='DIGITALOCEAN_KEY is not set')

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


@if_machine_digocean
def test_machine_labels(client):

    name = random_str()
    labels = {"abc": "def",
              "foo": "bar",
              "spam": "eggs"}
    create_args = {"name": name,
                   "digitaloceanConfig": {"accessToken": access_key,
                                          "image": image_name,
                                          "region": region,
                                          "size": size
                                          },
                   "labels": labels
                   }

    expected_values = {"image": image_name,
                       "region": region,
                       "size": size,
                       }
    try:
        digital_ocean_machine_life_cycle(client,
                                         create_args,
                                         expected_values,
                                         labels)
    finally:
        delete_host_in_digital_ocean(name)


@if_machine_digocean
def test_digital_ocean_machine_all_params(client):

    name = random_str()
    create_args = {"name": name,
                   "digitaloceanConfig": {"accessToken": access_key,
                                          "image": image_name,
                                          "region": region,
                                          "size": size
                                          }
                   }

    expected_values = {"image": image_name,
                       "region": region,
                       "size": size
                       }
    try:
        digital_ocean_machine_life_cycle(client, create_args, expected_values)
    finally:
        delete_host_in_digital_ocean(name)


@if_machine_digocean
def test_digital_ocean_machine_accesstoken(client):

    name = random_str()
    create_args = {"name": random_str(),
                   "digitaloceanConfig": {"accessToken": access_key,
                                          }
                   }

    expected_values = {"image": default_image_name,
                       "region": default_region,
                       "size": default_size
                       }
    try:
        digital_ocean_machine_life_cycle(client, create_args, expected_values)
    finally:
        delete_host_in_digital_ocean(name)


@if_machine_digocean
def test_digital_ocean_machine_parallel(client):
    create_args = {"name": None,
                   "digitaloceanConfig": {"accessToken": access_key
                                          }
                   }
    machines = []
    try:
        # Create 2 Digital Ocean Machines in parallel
        for n in range(0, 2):
            name = random_str() + "-parallel-" + str(n)
            create_args["name"] = name
            machine = client.create_machine(**create_args)
            machines.append(machine)

        # Check if both the machine and host get to "active" state

        for machine in machines:
            machine = client.wait_success(machine, timeout=DEFAULT_TIMEOUT)
            assert machine.state == 'active'
            machine = wait_for_host(client, machine)
            host = machine.hosts()[0]
            assert host.state == 'active'

        for machine in machines:
            machine = client.wait_success(machine.remove())
            assert machine.state == 'removed'

            host = machine.hosts()[0]
            host = wait_for_condition(client, host,
                                      lambda x: x.state == 'removed',
                                      lambda x: 'State is: ' + x.state)
            assert host.state == 'removed'
            wait_for_host_destroy_in_digital_ocean(
                host.ipAddresses()[0].address)
    finally:
        for machine in machines:
            delete_host_in_digital_ocean(machine.name)


@if_machine_digocean
def test_digital_ocean_machine_invalid_access_token(client):

    name = random_str()
    create_args = {"name": name,
                   "digitaloceanConfig": {"accessToken": "1234abcdefg",
                                          "image": image_name,
                                          "region": region,
                                          "size": size
                                          }
                   }
    # Create a Digital Ocean Machine with invalid access token
    machine = client.create_machine(**create_args)
    machine = wait_for_condition(client,
                                 machine,
                                 lambda x: x.state == 'error',
                                 lambda x: 'Machine state is ' + x.state
                                 )
    assert error_msg_auth_failure in machine.transitioningMessage

    hosts = machine.hosts()
    assert len(hosts) == 0

    machine = client.wait_success(machine.remove())
    assert machine.state == 'removed'


@if_machine_digocean
def test_digital_ocean_machine_invalid_region(client):

    name = random_str()
    create_args = {"name": name,
                   "digitaloceanConfig": {"accessToken": access_key,
                                          "image": image_name,
                                          "region": "abc",
                                          "size": size
                                          }
                   }
    # Create a Digital Ocean Machine with invalid access token
    machine = client.create_machine(**create_args)

    machine = wait_for_condition(client,
                                 machine,
                                 lambda x: x.state == 'error',
                                 lambda x: 'Machine state is ' + x.state
                                 )

    assert error_msg_invalid_region in machine.transitioningMessage

    hosts = machine.hosts()
    assert len(hosts) == 0

    machine = client.wait_success(machine.remove())
    assert machine.state == 'removed'


def digital_ocean_machine_life_cycle(client, configs, expected_values,
                                     labels=None):
    # Create a Digital Ocean Machine
    machine = client.create_machine(**configs)

    machine = client.wait_success(machine, timeout=DEFAULT_TIMEOUT)
    assert machine.state == 'active'

    # Wait until host shows up with some physicalHostId
    machine = wait_for_host(client, machine)
    host = machine.hosts()[0]
    assert host.state == 'active'
    assert machine.accountId == host.accountId

    # Check that the droplet that is being created in Digital Ocean has the
    # correct configurations

    droplet = check_host_in_digital_ocean(host.ipAddresses()[0].address)

    if labels is not None:
        for label in host.hostLabels():
            assert label.key in labels
            assert labels[label.key] == label.value

    assert droplet is not None
    assert droplet["name"] == machine.name
    assert droplet["image"]["slug"] == expected_values["image"]
    assert droplet["size_slug"] == expected_values["size"]
    assert droplet["region"]["slug"] == expected_values["region"]

    # Remove the machine and make sure that the host
    # and the machine get removed

    machine = client.wait_success(machine.remove())
    assert machine.state == 'removed'

    host = client.reload(machine.hosts()[0])
    host = wait_for_condition(client, host,
                              lambda x: x.state == 'removed',
                              lambda x: 'State is: ' + x.state)
    assert host.state == 'removed'

    wait_for_host_destroy_in_digital_ocean(host.ipAddresses()[0].address)


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


def check_host_in_digital_ocean(ipaddress):
    url = 'https://api.digitalocean.com/v2/droplets'
    headers = {'Authorization': "Bearer " + access_key}
    r = requests.get(url, headers=headers)
    response = r.json()
    r.close()
    droplet_list = response["droplets"]
    matched_droplet = None

    for droplet in droplet_list:
        if droplet["networks"]["v4"][0]["ip_address"] == ipaddress:
            matched_droplet = droplet
            break

    return matched_droplet


def delete_host_in_digital_ocean(name):
    try:
        url = 'https://api.digitalocean.com/v2/droplets'
        headers = {'Authorization': "Bearer " + access_key}
        r = requests.get(url, headers=headers)
        response = r.json()
        r.close()
        droplet_list = response["droplets"]

        for droplet in droplet_list:
            if droplet["name"] == name:
                url = 'https://api.digitalocean.com/v2/droplets/' + \
                      str(droplet["id"])
                headers = {'Authorization': "Bearer " + access_key}
                try:
                    r = requests.delete(url, headers=headers)
                finally:
                    r.close()
    except Exception:
        error_msg = "Error encountered when trying to delete machine - " + name
        logger.error(msg=error_msg)
        logger.error(msg=traceback.format_exc())


def wait_for_host_destroy_in_digital_ocean(ipaddress, timeout=300):
    start = time.time()
    time_elapsed = 0
    host = check_host_in_digital_ocean(ipaddress)
    while host is not None:
        assert host["locked"] is True
        time.sleep(2)
        host = check_host_in_digital_ocean(ipaddress)
        time_elapsed = time.time() - start
        if time_elapsed > timeout:
            time_elapsed_msg = "Timeout waiting for host to be created " \
                               "- str(time_elapsed)" + " seconds"
            logger.error(msg=time_elapsed_msg)
            raise Exception(time_elapsed_msg)
