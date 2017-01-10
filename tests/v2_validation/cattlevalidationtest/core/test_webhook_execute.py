from common_fixtures import *  # NOQA
import requests
from requests.auth import AuthBase
import json

access_key = os.environ.get("CATTLE_ACCESS_KEY", 'admin')
secret_key = os.environ.get("CATTLE_SECRET_KEY", 'admin')

def test_construct_webhook_test_max(client):
    # Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Create Service of scale 1
    service_name = random_str()

    image_uuid = TEST_IMAGE_UUID
    launch_config = {"imageUuid": image_uuid}
    service = client.create_service(name=service_name,
    	                            stackId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service.activate()
    service = client.wait_success(service)
    assert service.state == "active"

    # Create webhook to scale up service by 1
    url = "http://localhost:8080/v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": "newservice 1 up-2",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    # r = requests.post(url, auth=(env.access_key, env.secret_key), data=json.dumps(data), headers=headers)
    r = requests.post(url, data=json.dumps(data), headers=headers)
    r.json()
    assert r.status_code == 200

    if r.status_code != 200:
        assert r.content is not None
        return

    assert r.url is not None
    resp = json.loads(r.content)
    webhookToken = resp["url"]

    # Execute webhookToken once
    r = requests.post(webhookToken)
    service = client.wait_success(service)
    assert r.status_code == 200
    assert service.scale == 2

    # Delete the service
    service = client.wait_success(client.delete(service))

    # Execute webhook again, this time error message should be seen in logs
    r = requests.post(webhookToken)
    assert r.status_code == 400


