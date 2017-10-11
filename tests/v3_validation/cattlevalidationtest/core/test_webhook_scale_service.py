from common_fixtures import *  # NOQA


def test_webhook_scaleup(client):

    # This method tests the service scale up using webhook token

    launch_config = {"image": TEST_IMAGE_UUID}

    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "servicescaleuptest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    # Execute Webhook and verify that the scale is incremented by
    # the amount specified
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 3

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_scaleup_beyond_max(client):

    # This method tests the service scale up beyond the maximum allowed scale

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "servicescaleupbeyondmaxtest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 3,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)

    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    # Execute Webhook
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 3

    # Execute webhook again and ensure the scale
    # cannot be incremented beyond max scale
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 400
    service = client.reload(service)
    assert service.scale == 3
    json_resp = json.loads(wh_resp.content)
    print json_resp

    expected_response = "Error Cannot scale above provided max " \
                        "scale value in executing driver for scaleService"
    assert json_resp['message'] == expected_response

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_scaleup_beyond_max_1(client):

    # This method tests the service scale cannot got up beyond the max scale
    # when the initial request to scale up itself is beyond the max scale

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, 2)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 2

    data = {
        "name": "servicescaleupbeyondmaxtest_1",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 3,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    # Execute webhook and ensure the scale cannot be
    # incremented beyond max scale
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 400
    service = client.reload(service)
    assert service.scale == 2
    json_resp = json.loads(wh_resp.content)
    print "Json response is"
    print json_resp

    expected_response = "Error Cannot scale above provided max " \
                        "scale value in executing driver for scaleService"
    assert json_resp['message'] == expected_response

    # Scale down service to 1
    service = client.update(service, name=service.name, scale=1)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == 1

    # Execute the webhook generated earlier and ensure service scale up
    # is successful
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.reload(service)
    assert service.scale == 4

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_scaledown(client):

    # This method tests the service scale down using webhook token

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, scale=3)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 3

    data = {
        "name": "servicescaledowntest",
        "driver": "scaleService",
        "scaleServiceConfig": {
             "action": "down",
             "amount": 2,
             "serviceId": service.id,
             "min": 1,
             "max": 4,
        }
    }
    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is" + repr(webhook_url)
    print "Id is" + repr(webhook_id)

    # Execute Webhook and ensure the scale is decremented
    # by the amount specified
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 1

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_scaledown_below_min(client):

    # This method tests the service scale down below the minimum allowed scale

    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, scale=3)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 3

    data = {
        "name": "servicescaledownbelowmintest",
        "driver": "scaleService",
        "scaleServiceConfig": {
             "action": "down",
             "amount": 2,
             "serviceId": service.id,
             "min": 1,
             "max": 4,
        }
    }
    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is" + repr(webhook_url)
    print "Id is" + repr(webhook_id)

    # Execute Webhook
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 1

    # Execute Webhook and ensure scale cannot be
    # decremented beyond the min value
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 400
    service = client.reload(service)
    assert service.scale == 1
    json_resp = json.loads(wh_resp.content)
    print json_resp

    expected_response = "Error Cannot scale below provided min " \
                        "scale value in executing driver for scaleService"
    assert json_resp['message'] == expected_response

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_scaledown_below_min_1(client):

    # This method tests the service scale cannot go down below the min scale
    # when the initial request to scale down itself is below the min scale

    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config, scale=4)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 4

    data = {
        "name": "servicescaledownbelowmintest_1",
        "driver": "scaleService",
        "scaleServiceConfig": {
             "action": "down",
             "amount": 3,
             "serviceId": service.id,
             "min": 2,
             "max": 4,
        }
    }
    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is" + repr(webhook_url)
    print "Id is" + repr(webhook_id)

    # Execute Webhook and ensure scale cannot be
    # decremented below the min value
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 400
    service = client.reload(service)
    assert service.scale == 4
    json_resp = json.loads(wh_resp.content)
    print json_resp

    expected_response = "Error Cannot scale below provided min " \
                        "scale value in executing driver for scaleService"
    assert json_resp['message'] == expected_response

    # Scale up service to 5
    service = client.update(service, name=service.name, scale=5)
    service = client.wait_success(service, 300)
    assert service.state == "active"
    assert service.scale == 5

    # Execute the webhook generated earlier and ensure service scale down
    # is successful
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.reload(service)
    assert service.scale == 2

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_invalid_scale_action(client):

    # This method tests the use of invalid scale action

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "invalidactiontest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "updown",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }
    # Create Webhook and verify invalid action cannot be specified
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 400
    json_resp = json.loads(resp.content)
    print "JSON response is:"
    print json_resp
    expected_response = "Invalid action updown"
    assert json_resp['message'] == expected_response

    delete_all(client, [env])


def test_webhook_invalid_service_id(client):

    # This method tests the use of invalid service id

    env = client.create_stack(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    # Provide an invalid service for the serviceId field
    data = {
        "name": "invalidserviceidtest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "down",
            "amount": 2,
            "serviceId": "1s1000a",
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook and verify invalid service id cannot be specified
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 400
    json_resp = json.loads(resp.content)
    print "JSON response is:"
    print json_resp
    expected_response = "Invalid service 1s1000a"
    assert json_resp['message'] == expected_response

    delete_all(client, [env])


def test_webhook_scaleup_invalid_zero_amount(client):

    # This method tests the scale amount of zero

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"

    data = {
        "name": "zeroamounttest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 0,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }
    # Create Webhook and verify zero amount cannot be specified
    r = create_webhook(env.accountId, data)
    assert r.status_code == 400
    assert r.url is not None
    resp = json.loads(r.content)
    print resp

    expected_message = "Invalid amount: 0"
    assert resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_scaleup_invalid_negative_amount(client):

    # This method tests the negative value for scale amount

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "negativeamounttest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": -1,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }
    # Create Webhook and verify negative amount cannot be specified
    r = create_webhook(env.accountId, data)
    assert r.status_code == 400
    assert r.url is not None
    resp = json.loads(r.content)
    print resp

    expected_message = "Invalid amount: -1"
    assert resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_scaleup_invalid_zero_min(client):

    # This method tests the zero value for min scale

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "zeromintest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 0,
            "max": 4,
        }
    }
    # Create Webhook and verify zero min scale cannot be specified
    r = create_webhook(env.accountId, data)
    assert r.status_code == 400
    assert r.url is not None
    resp = json.loads(r.content)
    print resp
    print resp['message']

    expected_message = "Minimum scale not provided/invalid"
    assert resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_scaleup_invalid_negative_min(client):

    # This method tests the negative value for min scale

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "negativemintest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": -1,
            "max": 4,
        }
    }
    # Create Webhook and verify negative min scale cannot be specified
    r = create_webhook(env.accountId, data)
    assert r.status_code == 400
    assert r.url is not None
    resp = json.loads(r.content)
    print resp

    expected_message = "Minimum scale not provided/invalid"
    assert resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_scaleup_invalid_zero_max(client):

    # This method tests the zero value for max scale

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "zeromaxtest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 0,
        }
    }
    # Create Webhook and verify zero max scale cannot be specified
    r = create_webhook(env.accountId, data)
    assert r.status_code == 400
    assert r.url is not None
    resp = json.loads(r.content)
    print resp
    print resp['message']

    expected_message = "Maximum scale not provided/invalid"
    assert resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_scaleup_invalid_negative_max(client):

    # This method tests the negative value for max scale

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "negativemaxtest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": -1,
        }
    }
    # Create Webhook and verify negative max scale cannot be specified
    r = create_webhook(env.accountId, data)
    assert r.status_code == 400
    assert r.url is not None
    resp = json.loads(r.content)
    print resp
    print resp['message']
    expected_message = "Maximum scale not provided/invalid"
    assert resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_duplicatename(client):

    # This method tests that a duplicate webhook cannot be generated

    launch_config = {"image": TEST_IMAGE_UUID}

    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "duplicatenametest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 400
    json_resp = json.loads(resp.content)
    print json_resp
    expected_message = "Cannot have duplicate webhook name, webhook " \
                       + data["name"] + " already exists"
    assert json_resp['message'] == expected_message

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_external_service(client):

    # This method tests that an external service cannot be
    # scaled up/down using webhook

    env = create_env(client)
    random_name = random_str()
    ext_service_name = random_name.replace("-", "")

    ext_service = client.create_externalService(
        name=ext_service_name, stackId=env.id, hostname="google.com")

    ext_service = client.wait_success(ext_service, 90)
    assert ext_service.state == "inactive"

    activate_svc(client, ext_service)
    assert ext_service.state

    data = {
        "name": "extservicetest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": ext_service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 400
    json_resp = json.loads(resp.content)
    print json_resp
    expected_message = "Can only create webhooks for Services. " \
                       "The supplied service is of type externalService"
    assert json_resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_global_service(client):

    # This method tests that a global service cannot be
    # scaled up/down using webhook

    launch_config = {"image": TEST_IMAGE_UUID}
    launch_config["labels"] = {"io.rancher.scheduler.global": "true"}

    service, env = create_env_and_svc(
        client, launch_config, scale=None)

    service = client.wait_success(service.activate(), 90)

    assert service.state == "active"

    data = {
        "name": "globalservicetest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 400
    json_resp = json.loads(resp.content)
    print json_resp
    expected_message = "Cannot create webhook for global service " + service.id
    assert json_resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_service_no_image(client):

    # This method tests that a service with no image
    # cannot be scaled up/down using webhook

    launch_config = {"image": "docker:rancher/none"}

    env = create_env(client)

    # Create Service
    random_name = random_str()
    service_name = random_name.replace("-", "")

    service = client.create_service(
        name=service_name, stackId=env.id,
        launchConfig=launch_config, scale=0,
        selectorContainer="test=none")

    service = client.wait_success(service)
    assert service.state == "inactive"
    service.activate()
    service = client.wait_success(service)
    assert service.state == "active"

    data = {
        "name": "servicewithnoimagetest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 400
    json_resp = json.loads(resp.content)
    print json_resp
    expected_message = "Cannot create webhook for service " \
                       "with no image " + service.id
    assert json_resp['message'] == expected_message

    delete_all(client, [env])


def test_webhook_missing_projectid(client):

    # This method tests that executing a webhook with missing
    # project id gives an error message

    launch_config = {"image": TEST_IMAGE_UUID}

    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "missingprojectidtest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    # Remove the project id (last three characters) from the URL
    webhook_url = webhook_url[:-3]
    print webhook_url

    # Execute webhook with missing project Id and verify that it gives
    # an "Invalid" error message
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 400

    json_resp = json.loads(wh_resp.content)
    print "JSON Response is"
    print json_resp
    expected_keyword = "Invalid"
    jsonstrresponse = str(json_resp['message'])
    if jsonstrresponse.find(expected_keyword) == -1:
        assert False

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_invalid_projectid(client):

    # This method tests that executing a webhook with an invalid
    # project id gives an error message

    launch_config = {"image": TEST_IMAGE_UUID}

    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "invalidprojectidtest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    webhook_url_split = webhook_url.split("projectId=")
    print webhook_url_split
    projectId = webhook_url_split[1]
    print projectId
    invalid_projectId = "1e1000"
    print webhook_url

    # Use the invalid project id "1e1000" in the URL
    webhook_url_with_invalid_projectId = webhook_url_split[0] + \
        "projectId=" + invalid_projectId
    print "Webhook URL with invalid project id:"
    print webhook_url_with_invalid_projectId

    # Execute webhook with invalid project Id and
    # verify that it gives an error message
    wh_resp = requests.post(webhook_url_with_invalid_projectId)
    print "Response is : "
    print wh_resp
    assert wh_resp.status_code == 500

    json_resp = json.loads(wh_resp.content)
    print "JSON Response is"
    print json_resp
    expected_keyword = "Error"
    jsonstrresponse = str(json_resp['message'])
    if jsonstrresponse.find(expected_keyword) == -1:
        assert False

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_invalid_token(client):

    # This method tests that executing a webhook with an
    # invalid token gives an error message

    launch_config = {"image": TEST_IMAGE_UUID}

    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "invalidtokentest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    webhook_url_split = webhook_url.split("key=")
    key = webhook_url_split[1]
    # Create invalid key by removing first 3 characters of the key
    modified_key = key[3:]
    print "Modified key"
    print modified_key
    print webhook_url

    # Use the invalid key in the URL
    webhook_url_with_invalid_token = webhook_url_split[0] + "key=" \
        + modified_key
    print "Webhook URL with Invalid token:"
    print webhook_url_with_invalid_token

    # Execute webhook with invalid key/token and verify that it gives
    # an error message
    wh_resp = requests.post(webhook_url_with_invalid_token)
    print wh_resp
    assert wh_resp.status_code == 403

    json_resp = json.loads(wh_resp.content)
    print "JSON Response is"
    print json_resp
    expected_keyword = "revoked"
    jsonstrresponse = str(json_resp['message'])
    if jsonstrresponse.find(expected_keyword) == -1:
        assert False

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])


def test_webhook_execute_deleted_webhook(client):

    # This method tests that executing a deleted webhook gives
    # the appropriate error message

    launch_config = {"image": TEST_IMAGE_UUID}

    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "executedeletedwebhooktest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 1,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    # Execute Webhook and verify that the scale is incremented by
    # the amount specified
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 2

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    # Execute the deleted webhook and verify that it gives an error message
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 403

    json_resp = json.loads(wh_resp.content)
    print "JSON Response is"
    print json_resp

    expected_message = "Requested webhook has been revoked"
    jsonstrresponse = str(json_resp['message'])
    if jsonstrresponse.find(expected_message) == -1:
        assert False

    delete_all(client, [env])


def test_webhook_invalid_driver(client):

    # This method tests the use of invalid  driver

    launch_config = {"image": TEST_IMAGE_UUID}
    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "invaliddrivertest",
        "driver": "scaleServiceupDown",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }
    # Create Webhook and verify invalid action cannot be specified
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 400
    json_resp = json.loads(resp.content)
    print "JSON response is:"
    print json_resp
    expected_response = "Invalid driver " + data['driver']
    assert json_resp['message'] == expected_response

    delete_all(client, [env])


def test_webhook_list_single_webhook(client):

    # This method test lists a single webhook

    launch_config = {"image": TEST_IMAGE_UUID}

    service, env = create_env_and_svc(client, launch_config)
    assert service.state == "inactive"
    service = client.wait_success(service.activate(), 90)
    assert service.state == "active"
    assert service.scale == 1

    data = {
        "name": "listsinglewebhooktest",
        "driver": "scaleService",
        "scaleServiceConfig": {
            "action": "up",
            "amount": 2,
            "serviceId": service.id,
            "min": 1,
            "max": 4,
        }
    }

    # Create Webhook
    resp = create_webhook(env.accountId, data)
    assert resp.status_code == 200
    assert resp.url is not None
    json_resp = json.loads(resp.content)
    webhook_url = json_resp["url"]
    webhook_id = json_resp["id"]

    print "Webhook is " + repr(webhook_url)
    print "Id is " + repr(webhook_id)

    # List the webhook by id and ensure we get the correct response
    resp = list_webhook(env.accountId, webhook_id=webhook_id)
    assert resp["name"] == "listsinglewebhooktest"
    assert resp["state"] == "active"
    assert resp["driver"] == "scaleService"

    # Execute Webhook and verify that the scale is incremented by
    # the amount specified
    wh_resp = requests.post(webhook_url)
    assert wh_resp.status_code == 200
    service = client.wait_success(service)
    assert service.scale == 3

    # Delete the Webhook
    delete_webhook_verify(env.accountId, webhook_id)

    delete_all(client, [env])
