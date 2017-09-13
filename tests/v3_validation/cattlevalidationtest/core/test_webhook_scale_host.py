from common_fixtures import *  # NOQA
import requests
import json
import string

DEFAULT_TIMEOUT = 900

# Digital Ocean configurations
do_access_key = os.environ.get('DIGITALOCEAN_KEY')


# utility functions
def create_host(htId, client):
    host_name = random_str()
    host_create_args = {
        "hostname": host_name,
        "hostTemplateId": htId,
        "digitaloceanConfig": {
            "image": "ubuntu-16-04-x64",
            "region": "sfo2",
            "size": "1gb"
        }
    }
    host0 = client.wait_success(client.create_host(**host_create_args),
                                timeout=DEFAULT_MACHINE_TIMEOUT)
    return host0


def cleanup_host(host_to_remove, client):
    deactivated_host = client.wait_success(host_to_remove.deactivate())
    removed_host = client.wait_success(client.delete(deactivated_host))
    assert 'removed' == removed_host.state


# Tests start
def test_webhook_host_scale_up_down(admin_client):
    # This method tests webhook scale up and down
    # (1) scale up hosts by 2 and beyond max
    # (2) scale down with "mostRecent" and "leastRecent" action and below min

    # Use the "default" environment
    env = admin_client.list_project(uuid="adminProject")[0]
    client = client_for_project(env)

    # Create hosttemplate and host
    ht_create_args = {
        "name": random_str(),
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": do_access_key
            }
        }
    }

    ht0 = client.wait_success(client.create_hostTemplate(**ht_create_args))
    base_host = create_host(ht0.id, client)
    base_host_name = base_host["hostname"]

    # (1-1): Create webhook for scale up hosts
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 2,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_up_url = json_resp["url"]
    webhook_up_id = json_resp["id"]

    # Execute Webhook and verify that the scale is incremented by
    # the amount specified
    wh_resp = requests.post(webhook_up_url)
    assert wh_resp.status_code == 200

    hosts = client.list_host()
    host_scale_group = []
    for host in hosts:
        if host["hostTemplateId"] == ht0.id:
            host = wait_for_condition(client,
                                      host,
                                      lambda x: x.state == 'active',
                                      lambda x: 'Host state is ' + x.state,
                                      timeout=DEFAULT_MACHINE_TIMEOUT
                                      )
            host_scale_group.append(host)
    assert len(host_scale_group) == 3
    host_scale_group = sorted(host_scale_group, key=lambda x: x["created"])

    middle_host = host_scale_group[1]
    last_host = host_scale_group[2]

    # Checking the name of the hosts
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

    # (1-2): Execute Webhook again and ensure the scale
    # cannot be incremented beyond max
    wh_resp = requests.post(webhook_up_url)
    assert wh_resp.status_code == 400

    # Delete the webhook
    delete_webhook_verify(env.id, webhook_up_id)

    # (2-1): Create webhook for scale down mostRecent hosts
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "down",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "deleteOption": "mostRecent",
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_most_recent_url = json_resp["url"]
    webhook_most_recent_id = json_resp["id"]

    # Execute Webhook and verify that the scale is decremented by
    # the amount specified
    wh_resp = requests.post(webhook_most_recent_url)
    assert wh_resp.status_code == 200

    last_host = client.reload(last_host)
    last_host = wait_for_condition(client,
                                   last_host,
                                   lambda x: x.state == 'removed',
                                   lambda x: 'Host state is ' + x.state,
                                   timeout=DEFAULT_MACHINE_TIMEOUT
                                   )
    assert last_host.state == 'removed'
    assert base_host.state == 'active'
    assert middle_host.state == 'active'

    hosts = client.list_host()
    host_scale_group = []
    for host in hosts:
        if host["hostTemplateId"] == ht0.id:
            host = wait_for_condition(client,
                                      host,
                                      lambda x: x.state == 'active',
                                      lambda x: 'Host state is ' + x.state,
                                      timeout=DEFAULT_MACHINE_TIMEOUT
                                      )
            host_scale_group.append(host)
    assert len(host_scale_group) == 2

    # (2-2): Create webhook for scale down leastRecent hosts
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "down",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "deleteOption": "leastRecent",
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_least_recent_url = json_resp["url"]
    webhook_least_recent_id = json_resp["id"]

    # Execute Webhook and verify that the scale is decremented by
    # the amount specified
    wh_resp = requests.post(webhook_least_recent_url)
    assert wh_resp.status_code == 200

    base_host = client.reload(base_host)
    base_host = wait_for_condition(client,
                                   base_host,
                                   lambda x: x.state == 'removed',
                                   lambda x: 'Host state is ' + x.state,
                                   timeout=DEFAULT_MACHINE_TIMEOUT
                                   )
    assert base_host.state == 'removed'
    assert middle_host.state == 'active'

    hosts = client.list_host()
    host_scale_group = []
    for host in hosts:
        if host["hostTemplateId"] == ht0.id:
            host = wait_for_condition(client,
                                      host,
                                      lambda x: x.state == 'active',
                                      lambda x: 'Host state is ' + x.state,
                                      timeout=DEFAULT_MACHINE_TIMEOUT
                                      )
            host_scale_group.append(host)
    assert len(host_scale_group) == 1

    # (2-3) Execute Webhook again and ensure the scale
    # cannot be decremented below min
    wh_resp = requests.post(webhook_least_recent_url)
    assert wh_resp.status_code == 400

    # Delete webhook
    delete_webhook_verify(env.id, webhook_most_recent_id)
    delete_webhook_verify(env.id, webhook_least_recent_id)

    # delete hosttemplate and host
    cleanup_host(middle_host, client)
    client.wait_success(client.delete(ht0))


def test_host_scale_up_with_only_hosttemplate_exist(admin_client):
    # Use the "default" environment
    env = admin_client.list_project(uuid="adminProject")[0]
    client = client_for_project(env)

    # Create hosttemplate and host
    ht_create_args = {
        "name": random_str(),
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": do_access_key
            }
        }
    }

    ht0 = client.wait_success(client.create_hostTemplate(**ht_create_args))

    # (1-3): Scale up hosts using webhook created from existing hosttemplate
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 3,
            "hostTemplateId": ht0.id,  # using hosttemplate's id
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_up_url = json_resp["url"]
    webhook_up_id = json_resp["id"]

    # Execute Webhook and verify that the scale is incremented by
    # the amount specified
    wh_resp = requests.post(webhook_up_url)
    assert wh_resp.status_code == 200

    hosts = client.list_host()
    host_scale_group = []
    for host in hosts:
        if host["hostTemplateId"] == ht0.id:
            host = wait_for_condition(client,
                                      host,
                                      lambda x: x.state == 'active',
                                      lambda x: 'Host state is ' + x.state,
                                      timeout=DEFAULT_MACHINE_TIMEOUT
                                      )
            host_scale_group.append(host)
    assert len(host_scale_group) == 3

    host_scale_group = sorted(host_scale_group, key=lambda x: x["created"])

    base_host = host_scale_group[0]
    middle_host = host_scale_group[1]
    last_host = host_scale_group[2]

    base_host_name = base_host["hostname"]
    # Checking the name of the hosts
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

        assert string.atoi(current_host_suffix) == string.atoi(base_host_suffix) + 1

        base_host_suffix = current_host_suffix

    # Delete the webhook
    delete_webhook_verify(env.id, webhook_up_id)

    # Delete the hosttemplate and host
    client.wait_success(client.delete(ht0))
    cleanup_host(base_host, client)
    cleanup_host(middle_host, client)
    cleanup_host(last_host, client)


def test_webhook_invalid_cases(admin_client):
    # This method tests (3) invalid configs for webhook and invalid webhook url

    # Use the "default" environment
    env = admin_client.list_project(uuid="adminProject")[0]
    client = client_for_project(env)

    # Create hosttemplate and host
    ht_create_args = {
        "name": random_str(),
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": do_access_key
            }
        }
    }

    ht0 = client.wait_success(client.create_hostTemplate(**ht_create_args))

    # (3-1) invalid action, e.g. "updown"
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "updown",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 400

    # (3-2) invalid deleteOption, e.g. "none"
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "down",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "deleteOption": "none",
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 400

    # (3-3) invalid hosttemplateid, e.g. "xyz"
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": "xyz",
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 400

    # (3-4) invalid zero amount
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 0,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    # Create Webhook and verify zero amount cannot be specified
    r = create_webhook(env.id, data)
    assert r.status_code == 400
    assert r.url is not None

    # (3-5) invalid negative amount
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": -1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    r = create_webhook(env.id, data)
    assert r.status_code == 400
    assert r.url is not None

    # (3-6) invalid zero min
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 0,
            "max": 4
        }
    }

    r = create_webhook(env.id, data)
    assert r.status_code == 400
    assert r.url is not None

    # (3-7) invalid negative min
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": -1,
            "max": 4
        }
    }

    r = create_webhook(env.id, data)
    assert r.status_code == 400
    assert r.url is not None

    # (3-8) invalid zero max
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 0
        }
    }

    r = create_webhook(env.id, data)
    assert r.status_code == 400
    assert r.url is not None

    # (3-9) invalid negative max
    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": -1
        }
    }

    r = create_webhook(env.id, data)
    assert r.status_code == 400
    assert r.url is not None

    # (3-10) duplicate webhook name
    data = {
        "name": "duplicatenametest",
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    # Create Webhook
    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_id = json_resp["id"]

    resp = create_webhook(env.id, data)
    assert resp.status_code == 400

    # Delete the Webhook
    delete_webhook_verify(env.id, webhook_id)

    # (3-11) invalid driver, e.g. "scaleHostupDown"
    data = {
        "name": "invaliddrivertest",
        "driver": "scaleHostupDown",
        "scaleHostConfig": {
            "action": "up",
            "amount": 2,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    resp = create_webhook(env.id, data)
    assert resp.status_code == 400

    # (3-12) invalid webhook url: url missing projectId
    data = {
        "name": "missingprojectidtest",
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    # Create Webhook
    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    # Remove the project id (last three characters) from the URL
    webhook_url = webhook_url[:-3]

    # Execute webhook with missing project Id and verify that it gives
    # an "Invalid" error message
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 400

    # Delete the Webhook
    delete_webhook_verify(env.id, webhook_id)

    # (3-13) invalid webhook url: invalid projectId
    data = {
        "name": "invalidprojectidtest",
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    # Create Webhook
    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    webhook_url_split = webhook_url.split("projectId=")
    invalid_projectId = "1e1000"

    # Use the invalid project id "1e1000" in the URL
    webhook_url_with_invalid_projectId = webhook_url_split[0] + \
                                         "projectId=" + invalid_projectId

    # Execute webhook with invalid project Id and
    # verify that it gives an error message
    wh_resp = requests.post(webhook_url_with_invalid_projectId)
    assert wh_resp.status_code == 500

    # Delete the Webhook
    delete_webhook_verify(env.id, webhook_id)

    # (3-14) invalid webhook url: invalid token
    data = {
        "name": "invalidtokentest",
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 1,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    # Create Webhook
    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    webhook_url_split = webhook_url.split("key=")
    key = webhook_url_split[1]
    # Create invalid key by removing first 3 characters of the key
    modified_key = key[3:]

    # Use the invalid key in the URL
    webhook_url_with_invalid_token = webhook_url_split[0] + "key=" \
                                     + modified_key

    # Execute webhook with invalid key/token and verify that it gives
    # an error message
    wh_resp = requests.post(webhook_url_with_invalid_token)
    assert wh_resp.status_code == 403

    # Delete the Webhook
    delete_webhook_verify(env.id, webhook_id)

    # delete hosttemplate and host
    client.wait_success(client.delete(ht0))


def test_nonexisting_webhook_or_hosttemplate(admin_client):
    # This method is the test for (4) non-existing webhook/hosttemplate

    # Use the "default" environment
    env = admin_client.list_project(uuid="adminProject")[0]
    client = client_for_project(env)

    # Create hosttemplate and host
    ht_create_args = {
        "name": random_str(),
        "driver": "digitalocean",
        "secretValues": {
            "digitaloceanConfig": {
                "accessToken": do_access_key
            }
        }
    }

    ht0 = client.wait_success(client.create_hostTemplate(**ht_create_args))

    data = {
        "name": random_str(),
        "driver": "scaleHost",
        "scaleHostConfig": {
            "action": "up",
            "amount": 2,
            "hostTemplateId": ht0.id,
            "min": 1,
            "max": 4
        }
    }

    # (4-1) Execute deleted webhook
    # Create Webhook
    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    # Execute Webhook and verify that the scale is incremented by
    # the amount specified
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200

    hosts = client.list_host()
    host_scale_group = []
    for host in hosts:
        if host["hostTemplateId"] == ht0.id:
            host = wait_for_condition(client,
                                      host,
                                      lambda x: x.state == 'active',
                                      lambda x: 'Host state is ' + x.state,
                                      timeout=DEFAULT_MACHINE_TIMEOUT
                                      )
            host_scale_group.append(host)
    assert len(host_scale_group) == 2

    host_scale_group = sorted(host_scale_group, key=lambda x: x["created"])

    base_host = host_scale_group[0]
    middle_host = host_scale_group[1]

    # Delete the Webhook
    delete_webhook_verify(env.id, webhook_id)
    # Delete hosts
    cleanup_host(base_host, client)
    cleanup_host(middle_host, client)

    # Execute the deleted webhook and verify that it gives an error message
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 403

    # (4-2) Execute webhook with deleted hosttemplate
    # Create Webhook
    resp = create_webhook(env.id, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    # delete hosttemplate
    removed_ht = client.wait_success(client.delete(ht0))
    assert 'removed' == removed_ht.state

    # Execute the webhook with deleted hosttemplate and verify that it gives an error message
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 400

    # Delete the Webhook
    delete_webhook_verify(env.id, webhook_id)

    # (4-3) Create webhook with deleted hosttemplate
    resp = create_webhook(env.id, data)
    assert resp.status_code == 400