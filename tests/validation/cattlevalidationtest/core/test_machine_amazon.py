import boto.ec2
import logging
import traceback

from common_fixtures import *  # NOQA

DEFAULT_TIMEOUT = 450
access_key = os.environ.get('AMAZON_ACCESSKEY')
secret_key = os.environ.get('AMAZON_SECRETKEY')

# Amazon settings used for instance deployment
vpc_id = "vpc-eb2d928e"
subnet_id = "subnet-5775c020"
security_group = "test"
zone = "a"
region = "us-west-2"
ami = "ami-23ebb513"
size = "32"
instance_type = "t1.micro"

# Amazon settings used for instance deployment in default region
vpc_id_in_east = "vpc-44144621"
subnet_id_in_east = "subnet-22d1bd55"


# Use amazon settings from environment variables , if set
if os.environ.get('AMAZON_VPC_ID') is not None:
    vpc_id = os.environ.get('AMAZON_VPC_ID')
if os.environ.get('AMAZON_SUBNET_ID') is not None:
    subnet_id = os.environ.get('AMAZON_SUBNET_ID')
if os.environ.get('AMAZON_SECURITY_GROUP') is not None:
    security_group = os.environ.get('AMAZON_SECURITY_GROUP')
if os.environ.get('AMAZON_ZONE') is not None:
    zone = os.environ.get('AMAZON_ZONE')
if os.environ.get('AMAZON_REGION') is not None:
    region = os.environ.get('AMAZON_REGION')
if os.environ.get('AMAZON_AMI') is not None:
    region = os.environ.get('AMAZON_AMI')
if os.environ.get('AMAZON_VPC_ID_EAST') is not None:
    vpc_id_in_east = os.environ.get('AMAZON_VPC_ID')
if os.environ.get('AMAZON_SUBNET_ID_EAST') is not None:
    subnet_id_in_east = os.environ.get('AMAZON_SUBNET_ID')


# Default values set by Docker Machine
default_image_in_west = "ami-898dd9b9"
default_image_in_east = "ami-4ae27e22"
default_security_group = "docker-machine"
default_instance_type = "t2.micro"
default_root_size = "16"
default_zone = "a"
default_region = "us-east-1"

# Amazon error message validation

error_msg_auth_failure = "code=401"


if_machine_amazon = pytest.mark.skipif(
    os.environ.get('AMAZON_ACCESSKEY') is None or
    os.environ.get('AMAZON_SECRETKEY') is None,
    reason='Amazon EC2 Accesskey/Secretkey is not set')

# Get logger
ch = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.addHandler(ch)


@pytest.fixture(scope='session', autouse=True)
def register_host(admin_client):
    test_url = cattle_url()
    start = test_url.index("//") + 2
    end = test_url.index("/", start)
    api_host = test_url[start:end]
    admin_client.create_setting(name="api.host", value=api_host)


@if_machine_amazon
def test_amazon_ec2_machine_vpcid(client):
    name = random_str()
    create_args = {"name": name,
                   "amazonec2Config": {"vpcId": vpc_id,
                                       "accessKey": access_key,
                                       "secretKey": secret_key,
                                       "region": region,
                                       "zone": zone
                                       }
                   }
    expected_values = {"vpcId": vpc_id,
                       "subnetId": subnet_id,
                       "region": region,
                       "zone": zone,
                       "securityGroup": default_security_group,
                       "instanceType": default_instance_type,
                       "rootSize": default_root_size,
                       "ami": default_image_in_west,
                       }
    try:
        amazon_ec2_machine_lifecycle(region, client, create_args,
                                     expected_values)
    finally:
        delete_host_in_amazon_ec2(region, name)


@if_machine_amazon
def test_amazon_ec2_machine_vpcid_in_default_region(client):
    name = random_str()
    create_args = {"name": name,
                   "amazonec2Config": {"vpcId": vpc_id_in_east,
                                       "accessKey": access_key,
                                       "secretKey": secret_key
                                       }
                   }
    expected_values = {"vpcId": vpc_id_in_east,
                       "subnetId": subnet_id_in_east,
                       "region": default_region,
                       "zone": default_zone,
                       "securityGroup": default_security_group,
                       "instanceType": default_instance_type,
                       "rootSize": default_root_size,
                       "ami": default_image_in_east
                       }
    try:
        amazon_ec2_machine_lifecycle(default_region, client, create_args,
                                     expected_values)
    finally:
        delete_host_in_amazon_ec2(default_region, name)


@if_machine_amazon
def test_amazon_ec2_machine_subnetid(client):
    name = random_str()
    create_args = {"name": name,
                   "amazonec2Config": {"subnetId": subnet_id,
                                       "accessKey": access_key,
                                       "secretKey": secret_key,
                                       "region": region,
                                       "zone": zone
                                       }
                   }
    expected_values = {"vpcId": vpc_id,
                       "subnetId": subnet_id,
                       "region": region,
                       "zone": zone,
                       "securityGroup": default_security_group,
                       "instanceType": default_instance_type,
                       "rootSize": default_root_size,
                       "ami": default_image_in_west,
                       }
    try:
        amazon_ec2_machine_lifecycle(region, client, create_args,
                                     expected_values)
    finally:
        delete_host_in_amazon_ec2(region, name)


@if_machine_amazon
def test_amazon_ec2_machine_subnetid_in_default_region(client):
    name = random_str()
    create_args = {"name": name,
                   "amazonec2Config": {"subnetId": subnet_id_in_east,
                                       "accessKey": access_key,
                                       "secretKey": secret_key
                                       }
                   }
    expected_values = {"vpcId": vpc_id_in_east,
                       "subnetId": subnet_id_in_east,
                       "region": default_region,
                       "zone": default_zone,
                       "securityGroup": default_security_group,
                       "instanceType": default_instance_type,
                       "rootSize": default_root_size,
                       "ami": default_image_in_east
                       }
    try:
        amazon_ec2_machine_lifecycle(default_region, client, create_args,
                                     expected_values)
    finally:
        delete_host_in_amazon_ec2(default_region, name)


@if_machine_amazon
def test_amazon_ec2_machine_all_params(client):
    name = random_str()
    create_args = {"name": name,
                   "amazonec2Config": {"accessKey": access_key,
                                       "secretKey": secret_key,
                                       "vpcId": vpc_id,
                                       "subnetId": subnet_id,
                                       "securityGroup": security_group,
                                       "region": region,
                                       "zone": zone,
                                       "instanceType": instance_type,
                                       "rootSize": size,
                                       "ami": ami
                                       }
                   }
    expected_values = {"vpcId": vpc_id,
                       "subnetId": subnet_id,
                       "securityGroup": security_group,
                       "region": region,
                       "zone": zone,
                       "instanceType": instance_type,
                       "rootSize": size,
                       "ami": ami
                       }
    try:
        amazon_ec2_machine_lifecycle(region, client, create_args,
                                     expected_values)
    finally:
        delete_host_in_amazon_ec2(region, name)


@if_machine_amazon
def test_amazon_ec2machine_missing_required_params(client):

    create_args = {"name": random_str(),
                   "amazonec2Config": {"accessKey": access_key,
                                       "secretKey": secret_key
                                       }
                   }

    # Create a Amazon Machine without passing vpcid or subnetid
    machine = client.create_machine(**create_args)

    machine = wait_for_condition(client,
                                 machine,
                                 lambda x: x.state == 'error',
                                 lambda x: 'Machine state is ' + x.state
                                 )
    hosts = machine.hosts()
    assert len(hosts) == 0

    machine = client.wait_success(machine.remove())
    assert machine.state == 'removed'


@if_machine_amazon
def test_amazon_ec2machine_invalid_access_token(client):

    create_args = {"name": random_str(),
                   "amazonec2Config": {"vpcId": vpc_id,
                                       "accessKey": "abc123",
                                       "secretKey": secret_key,
                                       "region": region,
                                       "zone": zone
                                       }
                   }

    # Create a Amazon Machine with invalid access token
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


@if_machine_amazon
def test_amazon_ec2machine_parallel(client):
    create_args = {"amazonec2Config": {"vpcId": vpc_id,
                                       "accessKey": access_key,
                                       "secretKey": secret_key,
                                       "region": region,
                                       "zone": zone
                                       }
                   }
    machines = []
    try:
        # Create 2 Amazon Ec2 Machines in parallel
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
            assert host.state == 'removed'
            wait_for_host_to_destroy_in_amazon(region, machine.name)

    finally:
        for machine in machines:
            delete_host_in_amazon_ec2(region, machine.name)


@if_machine_amazon
def amazon_ec2_machine_lifecycle(ec2_region, client, configs, expected_values):

    machine = client.create_machine(**configs)

    machine = client.wait_success(machine, timeout=DEFAULT_TIMEOUT)
    assert machine.state == 'active'

    # Wait until host shows up with some physicalHostId
    machine = wait_for_host(client, machine)

    hosts = machine.hosts()
    assert len(hosts) == 1
    host = hosts[0]
    assert host.state == 'active'
    assert machine.accountId == host.accountId

    # Check that the droplet that is being created in Amazon Ec2 and has the
    # correct configurations

    ec2_instance = check_host_in_amazon(ec2_region,
                                        host.ipAddresses()[0].address)

    instance_root_size = str(get_instance_volume_size(ec2_region,
                                                      ec2_instance))

    assert ec2_instance is not None
    assert ec2_instance.key_name == machine.name
    assert ec2_instance.state == "running"
    assert ec2_instance.vpc_id == expected_values["vpcId"]
    assert ec2_instance.groups[0].name == expected_values["securityGroup"]
    assert ec2_instance.placement == ec2_region + expected_values["zone"]
    assert ec2_instance.image_id == expected_values["ami"]
    assert ec2_instance.subnet_id == expected_values["subnetId"]
    assert instance_root_size == expected_values["rootSize"]

    # Removing the machine and make sure that the host
    # and the machine get removed

    machine = client.wait_success(machine.remove())
    assert machine.state == 'removed'

    host = client.reload(host)
    assert host.state == 'removed'

    wait_for_host_to_destroy_in_amazon(ec2_region, machine.name)


def wait_for_host(client, machine, timeout=DEFAULT_TIMEOUT):

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


def check_host_in_amazon(ec2_region, ipaddress=None, name=None):

    conn = boto.ec2.connect_to_region(ec2_region,
                                      aws_access_key_id=access_key,
                                      aws_secret_access_key=secret_key)

    matched_instance = None
    reservations = conn.get_all_reservations()
    for r in reservations:
        instances = r.instances
        for i in instances:
            if ipaddress is not None:
                if i.ip_address == ipaddress:
                    matched_instance = i
                    break
            else:
                if name is not None:
                    if i.tags['Name'] == name:
                        matched_instance = i
                        break

    return matched_instance


def wait_for_host_to_destroy_in_amazon(ec2_region, name, timeout=180):

    start = time.time()
    time_elapsed = 0
    host = check_host_in_amazon(ec2_region, name=name)
    print host.state

    while host.state != "terminated":
        time.sleep(2)
        host = check_host_in_amazon(ec2_region, name=name)
        print host.state
        time_elapsed = time.time() - start
        if time_elapsed > timeout:
            time_elapsed_msg = "Timeout waiting for host to be destroyed in " \
                               "seconds " \
                               + str(time_elapsed)
            logger.error(msg=time_elapsed_msg)
            raise Exception(time_elapsed_msg)


def get_instance_volume_size(ec2_region, instance):
    conn = boto.ec2.connect_to_region(ec2_region,
                                      aws_access_key_id=access_key,
                                      aws_secret_access_key=secret_key)
    volumes = conn.get_all_volumes(filters={'attachment.instance-id':
                                            instance.id})
    assert volumes is not None
    assert len(volumes) > 0
    return volumes[0].size


def delete_host_in_amazon_ec2(ec2_region, name):
    try:
        conn = boto.ec2.connect_to_region(ec2_region,
                                          aws_access_key_id=access_key,
                                          aws_secret_access_key=secret_key)
        instance = check_host_in_amazon(ec2_region, name=name)
        if instance is not None:
            conn.terminate_instances(instance_ids=[instance.id])
    except Exception:
        error_msg = "Error encountered when trying to delete machine - " + name
        logger.error(msg=error_msg)
        logger.error(msg=traceback.format_exc())
