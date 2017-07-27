from common_fixtures import *  # NOQA
from test_machine import get_droplets
import gdapi
import logging
import machine
import time

DEFAULT_TIMEOUT = 900

# Digital Ocean configurations
access_token = os.environ.get('DIGITALOCEAN_KEY')
image_name = "ubuntu-16-04-x64"
region = "sfo1"
size = "1gb"

# Amazon EC2 configurations
access_key = os.environ.get('AMAZON_ACCESSKEY')
secret_key = os.environ.get('AMAZON_SECRETKEY')

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
if_machine_amazon = pytest.mark.skipif(
    not os.environ.get('AMAZON_ACCESSKEY') or
    not os.environ.get('AMAZON_SECRETKEY'),
    reason='Amazon EC2 Accesskey/Secretkey is not set')

# Get logger
logger = logging.getLogger(__name__)


def create_ht(ht_create_args, client):
    ht_list = client.list_hostTemplate()
    len_ht_list = len(ht_list.data)

    ht0 = client.wait_success(client.create_hostTemplate(**ht_create_args))

    assert ht_create_args["name"] == ht0.name
    assert ht0.id is not None and ht0.id != ""
    ht_list = client.list_hostTemplate()
    assert len(ht_list.data) == len_ht_list + 1
    assert len(filter(lambda ht: ht.id == ht0.id, ht_list.data)) == 1
    return ht0


def cleanupht(ht_to_remove, client):
    removed_ht = client.wait_success(client.delete(ht_to_remove))
    assert 'removed' == removed_ht.state
    assert 0 == len(filter(lambda ht: ht.id == removed_ht.id,
                    client.list_hostTemplate().data))

@if_machine_digocean
def test_create_delete_do(client):
    create_args = {
        "name": "test-do-ht1",
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        }
    }
    ht1 = create_ht(create_args, client)
    cleanupht(ht1, client)

@if_machine_amazon
def test_create_delete_aws(client):
    create_args = {
        "name": "test-aws-ht1",
        "driver": "amazonec2",
        "secretValues": {
            "amazonec2Config": {
                "accessKey": access_key,
                "secretKey": secret_key
            }
        }
    }
    ht1 = create_ht(create_args, client)
    cleanupht(ht1, client)

@if_machine_amazon
@if_machine_digocean
def test_single_provider_only():
    create_args = [{
        "name": random_str(),
        "secretValues": {
            "amazonec2Config": {
                "accessKey": access_key,
                "secretKey": secret_key
            },
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        }
    }, {
        "name": random_str(),
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        },
        "publicValues": {
            "amazonec2Config": {
                "ami": "ami-7caa341c",
                "instanceType": "t2.micro",
                "region": "us-west-2",
                "rootSize": "16",
                "securityGroup": [
                    "rancher-machine",
                ],
                "sshUser": "rancher",
                "subnetId": "subnet-e9fcc78d",
                "volumeType": "gp2",
                "vpcId": "vpc-08d7c46c",
                "zone": "a"
            }
        }
    }, {
        "name": random_str(),
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        },
        "publicValues": {
            "digitaloceanConfig": {
                "image": "ubuntu-17-04-x64",
                "region": "sfo2",
                "size": "1gb"
            },
            "amazonec2Config": {
                "ami": "ami-7caa341c",
                "instanceType": "t2.micro",
                "region": "us-west-2",
                "rootSize": "16",
                "securityGroup": [
                    "rancher-machine",
                ],
                "sshUser": "rancher",
                "subnetId": "subnet-e9fcc78d",
                "volumeType": "gp2",
                "vpcId": "vpc-08d7c46c",
                "zone": "a"
            }
        }
    }]

    hts = []
    for ht_args in create_args:
        try:
            hts.append(create_ht(ht_args, client))
        except:
            pass

    assert [] == hts

@if_machine_digocean
def test_unique_name(client):
    create_args = {
        "name": "test-do-ht1",
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        }
    }
    ht0 = create_ht(create_args, client)

    ht1 = None
    try:
        ht1 = client.create_hostTemplate(**create_args)
    except:
        cleanupht(ht0, client)
    try:
        assert ht1 is None
    finally:
        if ht1 is not None:
            cleanupht(ht1, client)

@if_machine_digocean
def test_update(client):
    create_args = {
        "name": "test-do-ht1",
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        },
        "publicValues": {
            "digitaloceanConfig": {
                "image": "ubuntu-17-04-x64",
                "region": "sfo2",
                "size": "1gb"
            }
        }
    }
    ht0 = create_ht(create_args, client)
    ht0.publicValues.digitaloceanConfig.size = "2gb"
    new_name = random_str()
    new_description = random_str()
    ht0.name = new_name
    ht0.description = new_description
    ht1 = client.update(ht0, ht0)

    assert ht1.name == new_name
    assert ht1.description == new_description
    assert ht1.publicValues.digitaloceanConfig.size == "1gb"
    cleanupht(ht1, client)


def hosts_in_do(name):
    return [d for d in get_droplets() if d["name"] == name]


def check_digitalocean_cleaned_up(host_name):
    for i in range(5):
        hosts = hosts_in_do(host_name)
        if len(hosts) == 0:
            break
        time.sleep(2 ** i)
    try:
        assert 0 == len(hosts)
    finally:
        headers = {'Authorization': "Bearer " + access_token}
        for droplet in hosts:
            url = 'https://api.digitalocean.com/v2/droplets/' + \
                  str(droplet["id"])
            try:
                r = requests.delete(url, headers=headers)
            finally:
                r.close()


def create_host(host_create_args, client):
    host0 = client.wait_success(client.create_host(**host_create_args),
                                timeout=600)
    assert host_create_args["hostname"] == host0.hostname
    assert host0.id is not None and host0.id != ""
    return host0


def cleanuphost(host_to_remove, client):
    deactivated_host = client.wait_success(host_to_remove.deactivate())
    removed_host = client.wait_success(client.delete(deactivated_host))
    assert 'removed' == removed_host.state
    check_digitalocean_cleaned_up(removed_host.hostname)

@if_machine_amazon
@if_machine_digocean
def test_create_host_wrong_provider(client):
    create_args = {
        "name": "test-aws-ht1",
        "driver": "amazonec2",
        "secretValues": {
            "amazonec2Config": {
                "accessKey": access_key,
                "secretKey": secret_key
            }
        }
    }
    ht0 = create_ht(create_args, client)
    host_name = random_str()
    host_create_args = {
        "hostname": host_name,
        "hostTemplateId": ht0.id,
        "digitaloceanConfig": {
            "image": "ubuntu-16-04-x64",
            "region": "sfo2",
            "size": "1gb"
        }
    }
    try:
        create_host(host_create_args, client)
    except gdapi.ClientApiError as err:
        assert err.message.find(
            "requires the --digitalocean-access-token") != -1
    finally:
        cleanupht(ht0, client)

@if_machine_digocean
def test_create_host_nonexistent_hosttemplate(client):
    host_name = random_str()
    hosttemplate_id = random_str()
    host_create_args = {
        "hostname": host_name,
        "hostTemplateId": hosttemplate_id,
        "digitaloceanConfig": {
            "image": "ubuntu-16-04-x64",
            "region": "sfo2",
            "size": "1gb"
        }
    }
    try:
        create_host(host_create_args, client)
    except gdapi.ApiError as err:
        assert err.args[1].find("InvalidReference") != -1

@if_machine_digocean
def test_create_host(client):
    ht_create_args = {
        "name": "test-do-ht1",
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        }
    }
    ht0 = create_ht(ht_create_args, client)

    host_name = random_str()
    host_create_args = {
        "hostname": host_name,
        "hostTemplateId": ht0.id,
        "digitaloceanConfig": {
            "image": "ubuntu-16-04-x64",
            "region": "sfo2",
            "size": "1gb"
        }
    }

    host0 = create_host(host_create_args, client)

    conf = machine.config(client, host0)
    digitalocean_config = host_create_args["digitaloceanConfig"]

    assert "digitalocean" == host0.driver
    assert digitalocean_config["image"] == conf["Driver"]["Image"]
    assert digitalocean_config["region"] == conf["Driver"]["Region"]
    assert digitalocean_config["size"] == conf["Driver"]["Size"]
    assert host_create_args["hostname"] == conf["Driver"]["MachineName"]

    cnt_name = random_str()
    cnt_create_args = {
        "stdinOpen": True,
        "tty": True,
        "requestedHostId": host0.id,
        "imageUuid": "docker:alpine",
        "name": cnt_name,
        "command": ["sh"],
        "networkMode": "bridge"
    }
    cnt0 = client.wait_success(client.create_container(cnt_create_args))
    assert 'running' == cnt0.state
    assert host0.id == cnt0.hostId
    cleanuphost(host0, client)
    cleanupht(ht0, client)

@if_machine_digocean
def test_create_host_ht_only(client):
    ht_create_args = {
        "name": "test-do-ht1",
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": access_token
            }
        },
        "publicValues": {
            "digitaloceanConfig": {
                "image": "ubuntu-17-04-x64",
                "region": "sfo2",
                "size": "1gb"
            }
        }
    }
    ht0 = create_ht(ht_create_args, client)

    host_name = random_str()
    host_create_args = {
        "hostname": host_name,
        "hostTemplateId": ht0.id,
    }

    host0 = create_host(host_create_args, client)

    conf = machine.config(client, host0)
    digitalocean_config = ht_create_args["publicValues"]["digitaloceanConfig"]

    assert "digitalocean" == host0.driver
    assert digitalocean_config["image"] == conf["Driver"]["Image"]
    assert digitalocean_config["region"] == conf["Driver"]["Region"]
    assert digitalocean_config["size"] == conf["Driver"]["Size"]
    assert host_create_args["hostname"] == conf["Driver"]["MachineName"]

    cnt_name = random_str()
    cnt_create_args = {
        "stdinOpen": True,
        "tty": True,
        "requestedHostId": host0.id,
        "imageUuid": "docker:alpine",
        "name": cnt_name,
        "command": ["sh"],
        "networkMode": "bridge"
    }
    cnt0 = client.wait_success(client.create_container(cnt_create_args))
    assert 'running' == cnt0.state
    assert host0.id == cnt0.hostId
    cleanuphost(host0, client)
    cleanupht(ht0, client)

@if_machine_amazon
def test_create_host_aws(client):
    ht_create_args = {
        "name": "test-aws-ht1",
        "driver": "amazonec2",
        "secretValues": {
            "amazonec2Config": {
                "accessKey": access_key,
                "secretKey": secret_key
            }
        }
    }
    ht0 = create_ht(ht_create_args, client)

    host_name = random_str()
    host_create_args = {
        "hostname": host_name,
        "hostTemplateId": ht0.id,
        "amazonec2Config": {
            "ami": "ami-7caa341c",
            "instanceType": "t2.micro",
            "region": "us-west-2",
            "rootSize": "16",
            "securityGroup": [
                "rancher-machine",
            ],
            "sshUser": "rancher",
            "subnetId": "subnet-e9fcc78d",
            "volumeType": "gp2",
            "vpcId": "vpc-08d7c46c",
            "zone": "a"
        }
    }

    host0 = create_host(host_create_args, client)

    conf = machine.config(client, host0)
    amazonec2_config = host_create_args["amazonec2Config"]

    assert "amazonec2" == host0.driver
    assert amazonec2_config["ami"] == conf["Driver"]["AMI"]
    assert amazonec2_config["instanceType"] == conf["Driver"]["InstanceType"]
    assert amazonec2_config["region"] == conf["Driver"]["Region"]
    assert amazonec2_config["rootSize"] == str(conf["Driver"]["RootSize"])
    assert amazonec2_config["sshUser"] == conf["Driver"]["SSHUser"]
    assert amazonec2_config["subnetId"] == conf["Driver"]["SubnetId"]
    assert amazonec2_config["volumeType"] == conf["Driver"]["VolumeType"]
    assert amazonec2_config["vpcId"] == conf["Driver"]["VpcId"]
    assert amazonec2_config["zone"] == conf["Driver"]["Zone"]

    assert host_create_args["hostname"] == conf["Driver"]["MachineName"]

    cnt_name = random_str()
    cnt_create_args = {
        "stdinOpen": True,
        "tty": True,
        "requestedHostId": host0.id,
        "imageUuid": "docker:alpine",
        "name": cnt_name,
        "command": ["sh"],
        "networkMode": "bridge"
    }
    cnt0 = client.wait_success(client.create_container(cnt_create_args))
    assert 'running' == cnt0.state
    assert host0.id == cnt0.hostId
    cleanuphost(host0, client)
    cleanupht(ht0, client)

@if_machine_amazon
def test_create_host_aws_ht_only(client):
    ht_create_args = {
        "name": "test-aws-ht1",
        "driver": "amazonec2",
        "secretValues": {
            "amazonec2Config": {
                "accessKey": access_key,
                "secretKey": secret_key
            }
        },
        "publicValues": {
            "amazonec2Config": {
                "ami": "ami-7caa341c",
                "instanceType": "t2.micro",
                "region": "us-west-2",
                "rootSize": "16",
                "securityGroup": [
                    "rancher-machine",
                ],
                "sshUser": "rancher",
                "subnetId": "subnet-e9fcc78d",
                "volumeType": "gp2",
                "vpcId": "vpc-08d7c46c",
                "zone": "a"
            }
        }
    }
    ht0 = create_ht(ht_create_args, client)

    host_name = random_str()
    host_create_args = {
        "hostname": host_name,
        "hostTemplateId": ht0.id,
    }

    host0 = create_host(host_create_args, client)

    conf = machine.config(client, host0)
    amazonec2_config = ht_create_args["publicValues"]["amazonec2Config"]

    assert "amazonec2" == host0.driver
    assert amazonec2_config["ami"] == conf["Driver"]["AMI"]
    assert amazonec2_config["instanceType"] == conf["Driver"]["InstanceType"]
    assert amazonec2_config["region"] == conf["Driver"]["Region"]
    assert amazonec2_config["rootSize"] == str(conf["Driver"]["RootSize"])
    assert amazonec2_config["sshUser"] == conf["Driver"]["SSHUser"]
    assert amazonec2_config["subnetId"] == conf["Driver"]["SubnetId"]
    assert amazonec2_config["volumeType"] == conf["Driver"]["VolumeType"]
    assert amazonec2_config["vpcId"] == conf["Driver"]["VpcId"]
    assert amazonec2_config["zone"] == conf["Driver"]["Zone"]

    assert host_create_args["hostname"] == conf["Driver"]["MachineName"]

    cnt_name = random_str()
    cnt_create_args = {
        "stdinOpen": True,
        "tty": True,
        "requestedHostId": host0.id,
        "imageUuid": "docker:alpine",
        "name": cnt_name,
        "command": ["sh"],
        "networkMode": "bridge"
    }
    cnt0 = client.wait_success(client.create_container(cnt_create_args))
    assert 'running' == cnt0.state
    assert host0.id == cnt0.hostId
    cleanuphost(host0, client)
    cleanupht(ht0, client)