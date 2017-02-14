from common_fixtures import *  # NOQA
import requests
import json

def test_construct_service_upgrade_webhook(admin_client, client, socat_containers):
    # Create Environment
    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Create 3 services
    launch_config = {"imageUuid": TEST_IMAGE_UUID, "labels": {"webhook": "testUpgradeService"}}
    services = []
    for x in range(0, 3):
        service = client.create_service(name=random_str(),
                                    stackId=env.id,
                                    launchConfig=launch_config)
        service = client.wait_success(service)
        assert service.state == "inactive"
        service = client.wait_success(service.activate())
        assert service.state == "active"
        services.append(service)

    # Create webhook for all these services
    url = base_url().split("v2-beta")[0] + "v1-webhooks/receivers?projectId="+env.accountId
    data = {
        "name": random_str(),
        "driver": "serviceUpgrade",
        "serviceUpgradeConfig": {
            "serviceSelector": {"webhook": "testUpgradeService"},
            "image": WEB_IMAGE_UUID.split("docker:")[1].split(":latest")[0],
            "tag": "latest",
            "batchSize": 1,
            "intervalMillis": 2
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200
    assert r.url is not None
    resp = json.loads(r.content)
    webhook = resp["url"]

    for service in services:
        assert service.launchConfig.imageUuid == TEST_IMAGE_UUID

    # Simulate Docker Hub response to webhook when image is pushed
    trigger_url = webhook
    data = {
        "push_data": {
            "pushed_at": 1485469949,
            "images": [
              
            ],
            "tag": "latest",
            "pusher": random_str()
        },
            "callback_url": "https://registry.hub.docker.com/",
            "repository": {
                "status": "Active",
                "description": "",
                "is_trusted": "false",
                "full_description": "",
                "repo_url": "https://hub.docker.com/r/",
                "owner": random_str(),
                "is_official": "false",
                "is_private": "false",
                "name": "rancher-catalog",
                "namespace": random_str(),
                "star_count": 0,
                "comment_count": 0,
                "date_created": 1485461838,
                "repo_name": WEB_IMAGE_UUID.split("docker:")[1].split(":latest")[0]
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    r = requests.post(webhook, data=json.dumps(data), headers=headers)
    assert r.status_code == 200


    # Check that upgraded service has the required image
    for service in services:
        service = wait_for_condition(client,
                                     service,
                                     lambda x: x.state == 'upgraded',
                                     lambda x: 'Service state is ' + x.state
                                    )
        assert service.launchConfig.imageUuid == WEB_IMAGE_UUID
	