from common_fixtures import *  # NOQA


def test_cluster_add_remove_host(admin_client, client, test_name,
                                 managed_network, super_client,
                                 socat_containers):

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 1
    cluster = None
    test_container = None

    try:
        cluster = client.create_cluster(name=test_name + '-cluster',
                                        port=9000)
        cluster = wait_for_condition(
            client, cluster,
            lambda x: x.state == 'inactive',
            lambda x: 'State is: ' + x.state)

        cluster.addhost(hostId=hosts[0].id)
        cluster = wait_for_condition(
            client, cluster,
            lambda x: len(x.hosts()) == 1,
            lambda x: 'Number of hosts in cluster is: ' + len(x.hosts()))

        cluster.activate()
        cluster = wait_for_condition(
            client, cluster,
            lambda x: x.state == 'active',
            lambda x: 'State is: ' + x.state)

        # check Cluster Server is deployed
        cluster_server = None
        for instance in cluster.instances():
            if (instance.state == 'removed'):
                continue
            if (instance.name == 'Cluster Server'):
                cluster_server = instance
                break

        assert cluster_server is not None

        assert cluster_server.systemContainer == 'ClusterAgent'
        assert cluster_server.state == 'running'

        cluster.addhost(hostId=hosts[1].id)
        cluster = wait_for_condition(
            client, cluster,
            lambda x: len(x.hosts()) == 2,
            lambda x: 'Number of hosts in cluster is: ' + len(x.hosts()))

        # deploy container to cluster
        test_container = client.create_container(
            name=test_name + "-cl-deployed",
            networkIds=[managed_network.id],
            imageUuid='docker:ubuntu',
            requestedHostId=cluster.id,
            tty=True,
            stdinOpen=True)
        wait_for_condition(
            client, test_container,
            lambda x: x.state == 'running',
            lambda x: 'State is: ' + x.state)

        test_container_found = None
        for instance in cluster.instances():
            if (instance.name == test_name + '-cl-deployed'):
                test_container_found = instance
                break

        assert test_container_found is not None
        assert test_container.id == test_container_found.id

        # check associated host is not a cluster
        host_deployed_to = test_container_found.hosts()
        assert host_deployed_to[0].kind == 'docker'

        nic = super_client.list_container(
            uuid=test_container.uuid)[0].nics()[0]
        assert nic.vnetId is not None
        assert nic.subnetId is not None

        # check primaryIpAddress is using the managed network (10.x.x.x)
        # instead of using the docker IP (172.x.x.x)
        # not a great check but better than nothing
        test_container_found = admin_client.reload(test_container_found)
        primary_ip_address = test_container_found.data.fields.primaryIpAddress
        assert primary_ip_address.startswith('10.')
        assert len(
            client.list_ip_address(address=primary_ip_address).data) == 1

    finally:
        if (test_container is not None):
            client.delete(test_container)

        if (cluster is not None):
            if (cluster.state == 'active'):
                cluster.deactivate()
                cluster = wait_for_condition(
                    client, cluster,
                    lambda x: x.state == 'inactive',
                    lambda x: 'State is: ' + x.state)
            client.delete(cluster)
