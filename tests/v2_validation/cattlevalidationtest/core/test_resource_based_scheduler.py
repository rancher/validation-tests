from common_fixtures import *  # NOQA
from cattle import ClientApiError


def test_resource_based_scheduler(client, test_name):
    hosts = client.list_host(kind='docker', removed_null=True, state="active")
    assert len(hosts) > 0
    host = hosts[0]
    con1 = client.create_container(name=test_name + "-scheduler",
                                   networkMode=UNMANAGED_NETWORK,
                                   imageUuid=TEST_IMAGE_UUID,
                                   ports=["9000:8080/tcp"],
                                   requestedHostId=host.id)
    con1 = client.wait_success(con1, 120)
    assert con1.state == "running"

    con2 = client.create_container(name=test_name + "-scheduler",
                                   networkMode=UNMANAGED_NETWORK,
                                   imageUuid=TEST_IMAGE_UUID,
                                   ports=["9000:8080/tcp"],
                                   requestedHostId=host.id)
    with pytest.raises(ClientApiError) as e:
        client.wait_success(con2)
    assert e.value.message.startswith('Scheduling failed')
    # since we have three host, test if we can launch 2 container on other
    # hosts where 9000 is not used
    con3 = client.create_container(name=test_name + "-scheduler",
                                   networkMode=UNMANAGED_NETWORK,
                                   imageUuid=TEST_IMAGE_UUID,
                                   ports=["9000:8080/tcp"],
                                   )
    con3 = client.wait_success(con3, 120)
    assert con3.state == "running"

    con4 = client.create_container(name=test_name + "-scheduler",
                                   networkMode=UNMANAGED_NETWORK,
                                   imageUuid=TEST_IMAGE_UUID,
                                   ports=["9000:8080/tcp"],
                                   )
    con4 = client.wait_success(con4, 120)
    assert con4.state == "running"

    con5 = client.create_container(name=test_name + "-scheduler",
                                   networkMode=UNMANAGED_NETWORK,
                                   imageUuid=TEST_IMAGE_UUID,
                                   ports=["9000:8080/tcp"],
                                   )
    with pytest.raises(ClientApiError) as e:
        client.wait_success(con5)
    assert e.value.message.startswith('Scheduling failed')

    delete_all(client, [con1, con2, con3, con4, con5])
