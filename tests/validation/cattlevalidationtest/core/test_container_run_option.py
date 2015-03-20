from common_fixtures import *  # NOQA

TEST_IMAGE = 'ibuildthecloud/helloworld'
TEST_IMAGE_LATEST = TEST_IMAGE + ':latest'
TEST_IMAGE_UUID = 'docker:' + TEST_IMAGE


def check_docker_param_values(s, con, configs):
    container_id = con.data.dockerContainer.Id

    for config in configs:

        docker_param_name = config["docker_param_name"]
        docker_param_value = config["docker_param_value"]

        stdin, stdout, stderr = s.exec_command("sudo docker inspect" +
                                               " --format='{{." +
                                               docker_param_name + "}}' " +
                                               container_id)

        response = stdout.readlines()
        config["docker_value"] = response
        res = False
        for line in response:
            if docker_param_value in line.rstrip('\n'):
                res = True
                break
        config["result"] = res
    return configs


def test_container_run_with_options_1(client, test_name, managed_network,
                                      host_ssh_containers):

    hosts = client.list_host(kind='docker', removed_null=True)
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
    memory_docker_val = "8e+06"
    memory_swap = 16000000
    cpu_set = "0"
    cpu_shares = 400
    command = "sleep"
    command_args = "450"

    # Create a container to link the data volume of the container for
    # validate dataVolumesFrom

    con_vol = client.create_container(name=test_name + "-forvolume",
                                      networkIds=[managed_network.id],
                                      imageUuid=TEST_IMAGE_UUID,
                                      requestedHostId=host.id
                                      )
    con_vol = client.wait_success(con_vol)
    assert con_vol.state == "running"

    docker_vol_from_value = con_vol.uuid

    # Create container with different docker options and validate the option
    # testing with docker inspect command

    c = client.create_container(name=test_name,
                                networkIds=[managed_network.id],
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
                                command=command,
                                commandArgs=[command_args]
                                )

    c = client.wait_success(c)
    assert c.state == "running"

    configs = []

    configs.append({"docker_param_name": "HostConfig.Binds",
                   "docker_param_value": docker_vol_value,
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "HostConfig.VolumesFrom",
                    "docker_param_value": docker_vol_from_value,
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "HostConfig.PublishAllPorts",
                    "docker_param_value": "false",
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "HostConfig.Privileged",
                    "docker_param_value": "false",
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "HostConfig.Dns",
                    "docker_param_value": dns_name[0],
                    "docker_value": None,
                    "result": False})
    configs.append({"docker_param_name": "HostConfig.DnsSearch",
                   "docker_param_value": dns_search[0],
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.OpenStdin",
                    "docker_param_value": "false",
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.Tty",
                    "docker_param_value": "false",
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.Hostname",
                    "docker_param_value": host_name,
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.Domainname",
                    "docker_param_value": domain_name,
                    "docker_value": None,
                    "result": False})
    configs.append({"docker_param_name": "Config.Env",
                   "docker_param_value": "name1=value1",
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.User",
                    "docker_param_value": user,
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "HostConfig.CapAdd",
                    "docker_param_value": cap_add[0],
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "HostConfig.CapDrop",
                    "docker_param_value": cap_drop[0],
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.Cpuset",
                    "docker_param_value": cpu_set,
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "HostConfig.RestartPolicy.Name",
                    "docker_param_value": "on-failure",
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name":
                    "HostConfig.RestartPolicy.MaximumRetryCount",
                    "docker_param_value": "5",
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.Cmd",
                    "docker_param_value": command,
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Args",
                   "docker_param_value": command_args,
                    "docker_value": None,
                    "result": False})

    configs.append({"docker_param_name": "Config.Memory",
                    "docker_param_value": memory_docker_val,
                    "docker_value": None,
                    "result": False})

    with get_ssh_to_host_ssh_container(host) as ssh:
        configs = check_docker_param_values(ssh, c, configs)

    for config in configs:
        result = config["result"]
        result_string = "Config value - %s - Expected - %s Returned - %s" \
                        % (str(config["docker_param_name"]),
                           str(config["docker_param_value"]),
                           str(config["docker_value"]))
        assert result, result_string

    delete_all(client, [con_vol, c])


def test_container_run_with_options_2(client, test_name, unmanaged_network,
                                      host_ssh_containers):

    hosts = client.list_host(kind='docker', removed_null=True)
    host = hosts[0]

    c = client.create_container(name=test_name,
                                networkIds=[unmanaged_network.id],
                                imageUuid=TEST_IMAGE_UUID,
                                requestedHostId=host.id,
                                publishAllPorts=True,
                                privileged=True,
                                stdinOpen=True,
                                tty=True,
                                )
    c = client.wait_success(c)
    assert c.state == "running"

    configs = [{"docker_param_name": "HostConfig.Privileged",
               "docker_param_value": "true",
                "docker_value": None,
                "result": False},
               {"docker_param_name": "Config.OpenStdin",
               "docker_param_value": "true",
                "docker_value": None,
                "result": False},
               {"docker_param_name": "Config.Tty",
               "docker_param_value": "true",
                "docker_value": None,
                "result": False},
               {"docker_param_name": "HostConfig.PublishAllPorts",
               "docker_param_value": "true",
                "docker_value": None,
                "result": False}
               ]

    with get_ssh_to_host_ssh_container(host) as ssh:
        configs = check_docker_param_values(ssh, c, configs)

    for config in configs:
        result = config["result"]
        result_string = "Config value - %s - Expected - %s Returned - %s" \
                        % (str(config["docker_param_name"]),
                           str(config["docker_param_value"]),
                           str(config["docker_value"]))
        assert result, result_string

    delete_all(client, [c])
