from common_fixtures import *  # NOQA
import websocket as ws
import pytest


def test_host_api_token(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    # valid token and a url to the websocket
    stats = hosts[0].stats()
    conn = ws.create_connection(stats.url+'?token='+stats.token)
    result = conn.recv()
    assert result is not None
    assert result.startswith('{')


def test_host_api_no_token(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    # Pass No token
    stats = hosts[0].stats()
    with pytest.raises(Exception) as excinfo:
            ws.create_connection(stats.url)
    assert 'Handshake status 401' in str(excinfo.value)


def test_host_api_garbage_token(client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    # pass garbage token
    stats = hosts[0].stats()
    with pytest.raises(Exception) as excinfo:
        ws.create_connection(stats.url+'?token=abcd')
    assert 'Handshake status 401' in str(excinfo.value)


def test_host_api_hoststats(client, admin_client):
    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0

    stats = hosts[0].hostStats()
    conn = ws.create_connection(stats.url + '?token=' + stats.token)
    result = conn.recv()
    conn.close()
    assert result is not None
    assert result.startswith('[')

    project = admin_client.list_project()[0]

    stats = project.hostStats()
    conn = ws.create_connection(stats.url + '?token=' + stats.token)
    result = conn.recv()
    conn.close()
    assert result is not None
    assert result.startswith('[')


def test_host_api_containerstats(client):
    container = client.create_container(name='test', imageUuid=TEST_IMAGE_UUID)
    container = client.wait_success(container, timeout=600)

    assert len(container.hosts()) == 1

    stats = container.containerStats()
    conn = ws.create_connection(stats.url + '?token=' + stats.token)
    result = conn.recv()
    conn.close()
    assert result is not None
    assert result.startswith('[')


def test_host_api_service_containerstats(client):
    env = client.create_environment(name=random_str())
    env = client.wait_success(env)
    assert env.state == "active"

    image_uuid = TEST_IMAGE_UUID
    launch_config = {"imageUuid": image_uuid}

    service = client.create_service(name=random_str(),
                                    environmentId=env.id,
                                    launchConfig=launch_config)
    service = client.wait_success(service)
    assert service.state == "inactive"
    service.activate()
    service = client.wait_success(service, timeout=600)
    assert service.state == "active"
    stats = service.containerStats()

    conn = ws.create_connection(stats.url + '?token=' + stats.token)
    result = conn.recv()
    conn.close()
    assert result is not None
    assert result.startswith('[')
