from common_fixtures import *  # NOQA
import requests
import json

def test_construct_webhook_min_max(client):
    # Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Create Service of scale 1
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service = client.create_service(name=random_str(),
                                    stackId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate())
    assert service.state == "active"

    # Create webhook to scale up service by 2
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 2,
            "serviceId": service.id,
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

    # Create webhook to scale down service by 2
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "down",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 4
        }
    }
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook_down = resp["url"]

    # Execute webhook_up once so scale of service becomes 3
    r = requests.post(webhook_up)
    assert r.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 3

    # Execute webhook_up again, new calculated scale will be 5, but that's more than 'max'
    r = requests.post(webhook_up)
    assert r.status_code == 400

    # Execute webhook_down once so scale of service becomes 1, allowed since min is 1
    r = requests.post(webhook_down)
    assert r.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 1

    # Execute webhook_down again, new calculated scale becomes 0, but that's less than 'min'
    r = requests.post(webhook_down)
    assert r.status_code == 400

    # Create webhook without min/max fields
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "down",
            "amount": 2,
            "serviceId": service.id
        }
    }
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 400

    # Create webhook with invalid min/max fields
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "down",
            "amount": 2,
            "serviceId": service.id,
            "min": -1,
            "max": -1
        }
    }
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 400

    # Create webhook with min > max
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "down",
            "amount": 2,
            "serviceId": service.id,
            "min": 11,
            "max": 4
        }
    }
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 400

    # Create webhook with min = max
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "down",
            "amount": 2,
            "serviceId": service.id,
            "min": 4,
            "max": 4
        }
    }
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 400


def test_webhook_deleted_service(client):
    # Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Create Service of scale 1
    service_name = random_str()

    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service = client.create_service(name=service_name,
                                    stackId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate())
    assert service.state == "active"

    # Create webhook to scale up service by 1
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook = resp["url"]

    # Execute webhook once
    r = requests.post(webhook)
    service = client.wait_success(service)
    assert r.status_code == 200
    assert service.scale == 2

    # Delete the service
    service = client.wait_success(client.delete(service))

    # Execute webhook again, this time error message should be seen in logs
    r = requests.post(webhook)
    assert r.status_code == 400


def test_validate_service_type(client):
    # Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Create loadBalancerService of scale 1
    service_name = random_str()

    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service = client.create_loadBalancerService(name=service_name,
                                                stackId=env.id,
                                                launchConfig=launch_config,
                                                lbConfig={})

    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate())
    assert service.state == "active"

    # Create webhook to scale up lb by 1
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None

    # Create externalService
    service_name = random_str()
    service = client.create_externalService(name=service_name,
                                            stackId=env.id,
                                            externalIpAddresses=[])

    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate())
    assert service.state == "active"

    # Create webhook to scale up externalService by 1
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 400


def test_delete_webhook(client):
    # Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Try deleting admin account instead of webhook
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers/1a1?projectId="+env.accountId
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.delete(url, headers=headers)
    assert r.status_code == 405  

     # Create Service of scale 1
    service_name = random_str()

    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service = client.create_service(name=service_name,
                                    stackId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate())
    assert service.state == "active"

    # Create a webhook
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook_id = resp["id"]

    # Deleting this webhook should pass
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers/"+webhook_id+"?projectId="+env.accountId
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.delete(url, headers=headers)
    assert r.status_code == 204

    # Delete the webhook again, should return 404
    r = requests.delete(url, headers=headers)
    assert r.status_code == 204


def test_invalid_token(client):
    # Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Create Service of scale 1
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    service = client.create_service(name=random_str(),
                                    stackId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate())
    assert service.state == "active"

    # Create webhook to scale up service by 2
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 4
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook = resp["url"]

    # Provide invalid token to execute
    webhook = webhook + random_str()
    r = requests.post(webhook)
    assert r.status_code == 400




