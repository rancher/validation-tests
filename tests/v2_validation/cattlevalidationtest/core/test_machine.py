from common_fixtures import *  # NOQA
import traceback
import logging

DEFAULT_TIMEOUT = 900

# Digital Ocean configurations
access_key = os.environ.get('DIGITALOCEAN_KEY')
image_name = "ubuntu-16-04-x64"
region = "sfo1"
size = "1gb"

# Digital Ocean default configurations
default_size = "512mb"
default_image_name = "ubuntu-16-04-x64"
default_region = "nyc3"


# Digital Ocean Error Messages
error_msg_auth_failure = "Invalid access token"

error_msg_invalid_region = "digitalocean requires a valid region"


if_machine_digocean = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY'),
    reason='DIGITALOCEAN_KEY is not set')

# Get logger
logger = logging.getLogger(__name__)


@if_machine_digocean
def test_machine_labels(client):

    name = random_str()
    labels = {"abc": "def",
              "foo": "bar",
              "spam": "eggs"}
    create_args = {"hostname": name,
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
    create_args = {"hostname": name,
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
    create_args = {"hostname": random_str(),
                   "digitaloceanConfig": {"accessToken": access_key
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
    create_args = {"hostname": None,
                   "digitaloceanConfig": {"accessToken": access_key,
                                          "image": image_name
                                          }
                   }
    hosts = []
    try:
        # Create 2 Digital Ocean Machines in parallel
        for n in range(0, 2):
            name = random_str() + "-parallel-" + str(n)
            create_args["hostname"] = name
            host = client.create_host(**create_args)
            hosts.append(host)

        # Check if both the machine and host get to "active" state

        for host in hosts:
            host = client.wait_success(host, timeout=DEFAULT_TIMEOUT)
            assert host.state == 'active'

        for host in hosts:
            host = client.wait_success(host.deactivate())
            assert host.state == "inactive"
            host = client.wait_success(client.delete(host))
            assert host.state == 'removed'
            wait_for_host_destroy_in_digital_ocean(
                host.ipAddresses()[0].address)
    finally:
        for host in hosts:
            hostname = host.hostname
            index = host.hostname.find(".")
            if index != -1:
                hostname = host.hostname[0:index]
            delete_host_in_digital_ocean(hostname)


@if_machine_digocean
def test_digital_ocean_machine_invalid_access_token(client):

    name = random_str()
    create_args = {"hostname": name,
                   "digitaloceanConfig": {"accessToken": "1234abcdefg",
                                          "image": image_name,
                                          "region": region,
                                          "size": size
                                          }
                   }
    # Create a Digital Ocean Machine with invalid access token
    host = client.create_host(**create_args)

    host = wait_for_condition(client,
                              host,
                              lambda x: x.state == 'error',
                              lambda x: 'Machine state is ' + x.state
                              )
    assert error_msg_auth_failure in host.transitioningMessage
    host = client.wait_success(client.delete(host))
    assert host.state == 'removed'


@if_machine_digocean
def test_digital_ocean_machine_invalid_region(client):

    name = random_str()
    create_args = {"hostname": name,
                   "digitaloceanConfig": {"accessToken": access_key,
                                          "image": image_name,
                                          "region": "abc",
                                          "size": size
                                          }
                   }
    # Create a Digital Ocean Machine with invalid access token
    host = client.create_host(**create_args)
    host = wait_for_condition(client,
                              host,
                              lambda x: x.state == 'error',
                              lambda x: 'Machine state is ' + x.state
                              )
    assert error_msg_invalid_region in host.transitioningMessage
    host = client.wait_success(client.delete(host))
    assert host.state == 'removed'


def digital_ocean_machine_life_cycle(client, configs, expected_values,
                                     labels=None):
    # Create a Digital Ocean Machine
    host = client.create_host(**configs)
    host = client.wait_success(host, timeout=DEFAULT_TIMEOUT)
    assert host.state == 'active'

    # Check that the droplet that is being created in Digital Ocean has the
    # correct configurations

    droplet = check_host_in_digital_ocean(host.ipAddresses()[0].address)

    if labels is not None:
        for label in host.hostLabels():
            if not label.key.startswith("io.rancher"):
                assert label.key in labels
                assert labels[label.key] == label.value

    assert droplet is not None
    index = host.hostname.find(".")
    if index != -1:
        hostname = host.hostname[0:index]
    assert droplet["name"] == hostname
    assert droplet["image"]["slug"] == expected_values["image"]
    assert droplet["size_slug"] == expected_values["size"]
    assert droplet["region"]["slug"] == expected_values["region"]

    # Remove the host
    host = client.wait_success(host.deactivate())
    assert host.state == "inactive"
    host = client.wait_success(client.delete(host))
    assert host.state == 'removed'
    wait_for_host_destroy_in_digital_ocean(host.ipAddresses()[0].address)


def get_droplet_page(url):
    headers = {'Authorization': "Bearer " + access_key}
    r = requests.get(url, headers=headers)
    response = r.json()
    r.close()
    return response


def get_droplets():
    url = 'https://api.digitalocean.com/v2/droplets?per_page=200'
    response = get_droplet_page(url)
    droplets = []
    for droplet in response['droplets']:
        droplets.append(droplet)
    try:
        next = response['links']['pages']['next']
    except KeyError:
        return droplets
    while True:
        response = get_droplet_page(next)
        for droplet in response['droplets']:
            droplets.append(droplet)
        try:
            next = response['links']['pages']['next']
        except KeyError:
            return droplets


def check_host_in_digital_ocean(ipaddress):
    droplet_list = get_droplets()
    matched_droplet = None

    for droplet in droplet_list:
        if droplet["networks"]["v4"][0]["ip_address"] == ipaddress:
            matched_droplet = droplet
            break

    return matched_droplet


def delete_host_in_digital_ocean(name):
    try:
        droplet_list = get_droplets()

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


def get_dropletid_for_ha_hosts():
    droplet_ids = {}
    droplet_list = get_droplets()
    for host in ha_host_list:
        for droplet in droplet_list:
            if droplet["name"] == host.hostname:
                droplet_ids[host.hostname] = droplet["id"]
    return droplet_ids


def action_on_digital_ocean_machine(dropletId, action):
    try:
        url = 'https://api.digitalocean.com/v2/droplets/' + \
              str(dropletId) + "/actions"
        headers = {'Authorization': "Bearer " + access_key,
                   "Content-Type": "application/json"}
        data = {'type': action}
        print url
        r = requests.post(url, data=json.dumps(data), headers=headers)
    except Exception:
        error_msg = "Error encountered when trying to " \
                    + action+" machine - " + str(dropletId)
        print error_msg
        logger.error(msg=error_msg)
        logger.error(msg=traceback.format_exc())
    finally:
        r.close()


def wait_for_host_destroy_in_digital_ocean(ipaddress, timeout=300):
    start = time.time()
    time_elapsed = 0
    host = check_host_in_digital_ocean(ipaddress)
    while host is not None:
        time.sleep(2)
        host = check_host_in_digital_ocean(ipaddress)
        time_elapsed = time.time() - start
        if time_elapsed > timeout:
            time_elapsed_msg = "Timeout waiting for host to be deleted " \
                               "- str(time_elapsed)" + " seconds"
            logger.error(msg=time_elapsed_msg)
            raise Exception(time_elapsed_msg)
