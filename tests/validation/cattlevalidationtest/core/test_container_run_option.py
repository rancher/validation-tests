from common_fixtures import *  # NOQA

TEST_IMAGE = 'ibuildthecloud/helloworld'
TEST_IMAGE_LATEST = TEST_IMAGE + ':latest'
TEST_IMAGE_UUID = 'docker:' + TEST_IMAGE


def test_container_run_with_options_1(client, test_name,
                                      socat_containers):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 0
    host = hosts[0]

    volume_in_host = "/test/container"
    volume_in_container = "/test/vol1"
    docker_vol_value = volume_in_host + ":" + volume_in_container + ":ro"

    env_var = {"name1": "value1"}
    host_name = "host1"
    domain_name = "abc.com"
    dns_name = ["test.com"]
    dns_search = ["8.8.8.8"]
    cap_add = ["CHOWN"]
    cap_drop = ["KILL"]
    user = "root"
    restart_policy = {"maximumRetryCount": 5, "name": "on-failure"}
    memory = 8000000
    memory_swap = 16000000
    cpu_set = "0"
    cpu_shares = 400
    command = ["sleep", "450"]

    # Create a container to link the data volume of the container for
    # validate dataVolumesFrom

    con_vol = client.create_container(name=test_name + "-forvolume",
                                      networkMode=MANAGED_NETWORK,
                                      imageUuid=TEST_IMAGE_UUID,
                                      requestedHostId=host.id
                                      )
    con_vol = client.wait_success(con_vol, 120)
    assert con_vol.state == "running"

    docker_vol_from_value = con_vol.externalId

    # Create container with different docker options and validate the option
    # testing with docker inspect command

    c = client.create_container(name=test_name,
                                networkMode=MANAGED_NETWORK,
                                imageUuid=TEST_IMAGE_UUID,
                                requestedHostId=host.id,
                                dataVolumes=docker_vol_value,
                                dataVolumesFrom=con_vol.id,
                                publishAllPorts=False,
                                privileged=False,
                                environment=env_var,
                                hostname=host_name,
                                domainName=domain_name,
                                stdinOpen=False,
                                tty=False,
                                dns=dns_name,
                                dnsSearch=dns_search,
                                capAdd=cap_add,
                                capDrop=cap_drop,
                                user=user,
                                memory=memory,
                                memorySwap=memory_swap,
                                cpuSet=cpu_set,
                                cpuShares=cpu_shares,
                                restartPolicy=restart_policy,
                                command=command
                                )

    c = client.wait_success(c, 120)
    assert c.state == "running"

    docker_client = get_docker_client(host)
    inspect = docker_client.inspect_container(c.externalId)
    print inspect

    assert inspect["HostConfig"]["Binds"] == [docker_vol_value]
    assert inspect["HostConfig"]["VolumesFrom"] == [docker_vol_from_value]
    assert inspect["HostConfig"]["PublishAllPorts"] is False
    assert inspect["HostConfig"]["Privileged"] is False
    assert inspect["Config"]["OpenStdin"] is False
    assert inspect["Config"]["Tty"] is False
    assert inspect["HostConfig"]["Dns"] == dns_name
    assert inspect["HostConfig"]["DnsSearch"] == dns_search
    assert inspect["Config"]["Hostname"] == host_name
    assert inspect["Config"]["Domainname"] == domain_name
    assert inspect["Config"]["User"] == user
    assert inspect["HostConfig"]["CapAdd"] == cap_add
    assert inspect["HostConfig"]["CapDrop"] == cap_drop
    assert inspect["Config"]["Cpuset"] == cpu_set
    assert inspect["HostConfig"]["RestartPolicy"]["Name"] == "on-failure"
    assert inspect["HostConfig"]["RestartPolicy"]["MaximumRetryCount"] == 5

    assert inspect["Config"]["Cmd"] == command
    assert inspect["Config"]["Memory"] == memory
    assert "name1=value1" in inspect["Config"]["Env"]

    delete_all(client, [con_vol, c])


def test_container_run_with_options_2(client, test_name,
                                      socat_containers):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) >= 1
    host = hosts[0]

    c = client.create_container(name=test_name,
                                networkMode=UNMANAGED_NETWORK,
                                imageUuid=TEST_IMAGE_UUID,
                                requestedHostId=host.id,
                                publishAllPorts=True,
                                privileged=True,
                                stdinOpen=True,
                                tty=True,
                                )
    c = client.wait_success(c, 120)
    assert c.state == "running"
    docker_client = get_docker_client(host)
    inspect = docker_client.inspect_container(c.externalId)

    assert inspect["HostConfig"]["PublishAllPorts"]
    assert inspect["HostConfig"]["Privileged"]
    assert inspect["Config"]["OpenStdin"]
    assert inspect["Config"]["Tty"]

    delete_all(client, [c])
