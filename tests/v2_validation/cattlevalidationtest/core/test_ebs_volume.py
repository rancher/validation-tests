from common_fixtures import *  # NOQA

# we should test the following scenarios:
# 1. Adding an environment scoped ebs volume.
# 2. Adding a stack scoped ebs volume.

if_test_ebs=pytest.mark.skipif(
    RANCHER_EBS != "true",
    reason="rancher ebs test environment is not enabled"
)


@if_test_ebs
def test_environment_ebs_volume(client):
    volume_name = "ebs_" + random_str()
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name, "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":/test"],
                     "networkMode": "managed",
                     "imageUuid": "docker:ubuntu:14.04.3",
                     "stdinOpen": True
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                      scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    client.delete(stack)
    delete_all(client, [stack])
    client.delete(volume)


@if_test_ebs
def test_stack_ebs_volume(client):
    volume_name = "ebs_" + random_str()
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":/test"],
                     "networkMode": "managed",
                     "imageUuid": "docker:ubuntu:14.04.3",
                     "stdinOpen": True
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                      scale)
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name, "stackId": stack.id,
                                   "driverOpts": {"size": "1"}})
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    client.delete(stack)


@if_test_ebs
def test_ebs_volume_move(client):
    # this test requires host a and host b are in the same AZ
    volume_name = "ebs_" + random_str()
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    volume = client.create_volume({"type": "volume", "driver": "rancher-ebs",
                                   "name": volume_name, "driverOpts": {"size": "1"}})
    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":/test"],
                     "networkMode": "managed",
                     "imageUuid": "docker:ubuntu:14.04.3",
                     "stdinOpen": True,
                     "requestedHostId": hosts[0].id
                     }
    scale = 1

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    client.delete(stack)

    wait_for_condition(client, volume, lambda x: x.state == "detached")

    launch_config = {"volumeDriver": "rancher-ebs",
                     "dataVolumes": [volume_name + ":/test"],
                     "networkMode": "managed",
                     "imageUuid": "docker:ubuntu:14.04.3",
                     "stdinOpen": True,
                     "requestedHostId": hosts[1].id
                     }

    service, stack = create_env_and_svc(client, launch_config,
                                        scale)
    stack = stack.activateservices()
    service = client.wait_success(service, 300)
    assert service.state == "active"

    client.delete(stack)

