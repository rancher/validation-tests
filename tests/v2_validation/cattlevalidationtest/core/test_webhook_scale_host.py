from common_fixtures import *  # NOQA
import requests
import json
import string

DEFAULT_TIMEOUT = 900

# Digital Ocean configurations
do_access_key = os.environ.get('DIGITALOCEAN_KEY')

def test_construct_webhook_host(client):
	# Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == 'active'

    # Create host, get its name and add label to it
    hosts = add_digital_ocean_hosts(client, 1)
    base_host = hosts[0]
    labels = {"webhook": "scaleHost","testLabel1": "valueLabel1", "testLabel2": "valueLabel2"}
    base_host = client.wait_success(client.update(base_host, labels=labels))
    base_host_name = base_host["hostname"]

	# Create webhook to scale up hosts with labels "webhook": "scaleHost" by 2
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 2,
            "hostSelector": {"webhook": "scaleHost"},
            "min": 1,
            "max": 4
        }
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook_up = resp["url"]

    # Execute webhook_up once so 2 more hosts get created
    r = requests.post(webhook_up)
    assert r.status_code == 200
    
    hosts = client.list_host()
    host_scale_group = []
    for host in hosts:
    	if host["labels"] == labels:
    		host = client.wait_success(host, timeout=DEFAULT_MACHINE_TIMEOUT)
    		host_scale_group.append(host)

    assert len(host_scale_group) == 3
    host_scale_group = sorted(host_scale_group, key=lambda x: x["created"])

    middle_host = host_scale_group[1]
    last_host = host_scale_group[2]

    base_host_name = base_host_name.split('.')[0]
    base_host_prefix = base_host_name.rstrip('0123456789')
    base_host_suffix = base_host_name.split(base_host_prefix)[1]

    for host in host_scale_group:
    	if host["id"] == base_host["id"]:
    		continue
    	current_host_name = host["hostname"]
        current_host_name = current_host_name.split('.')[0]
        current_host_prefix = current_host_name.rstrip('0123456789')
        current_host_suffix = current_host_name.split(current_host_prefix)[1]

        assert current_host_prefix == base_host_prefix

        if base_host_suffix != "":
        	assert string.atoi(current_host_suffix) == string.atoi(base_host_suffix) + 1
        else:
        	assert current_host_suffix == "2"

        base_host_suffix = current_host_suffix

    # Create webhook to scale down hosts with labels "webhook": "scaleHost" by 1 (most recently added)
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "down",
            "amount": 1,
            "hostSelector": {"webhook": "scaleHost"},
            "deleteOption": "mostRecent",
            "min": 1,
            "max": 4
        }
    }

    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook_most_recent = resp["url"]

    # Execute webhook_most_recent once so 2 hosts remain
    r = requests.post(webhook_most_recent)
    assert r.status_code == 200

    last_host = client.reload(last_host)
    last_host = wait_for_condition(client,
                                   last_host,
                                   lambda x: x.state == 'purged',
                                   lambda x: 'Host state is ' + x.state
                                  )
    assert last_host.state == 'purged'
    assert base_host.state == 'active'
    assert middle_host.state == 'active'

    # Create webhook to scale down hosts with labels "webhook": "scaleHost" by 1 (least recently added)
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "down",
            "amount": 1,
            "hostSelector": {"webhook": "scaleHost"},
            "deleteOption": "leastRecent",
            "min": 1,
            "max": 4
        }
    }

    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook_least_recent = resp["url"]

    # Execute webhook_least_recent once so only middle host remains
    r = requests.post(webhook_least_recent)
    assert r.status_code == 200

    base_host = client.reload(base_host)
    base_host = wait_for_condition(client,
                                   base_host,
                                   lambda x: x.state == 'purged',
                                   lambda x: 'Host state is ' + x.state
                                  )
    assert base_host.state == 'purged'
    assert middle_host.state == 'active'
