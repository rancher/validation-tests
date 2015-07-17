from common_fixtures import *  # NOQA
import re

WEB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
SSH_IMAGE_UUID = "docker:sangeetha/testclient:latest"

logger = logging.getLogger(__name__)


def env_with_2_svc_and_volume_mount_with_config(client, service_scale,
                                                launch_config_consumed_service,
                                                launch_config_service):
    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service

    random_name = random_str()
    consumed_service_name = random_name.replace("-", "")

    launch_config_service["dataVolumesFromLaunchConfigs"] = \
        [consumed_service_name]
    launch_config_consumed_service["name"] = consumed_service_name

    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service])

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name = \
        env.name + "_" + service.name + "_" + consumed_service_name

    service_name = env.name + "_" + service.name
    return env, service, service_name, consumed_service_name


def create_env_with_2_svc_and_volume_mount(client, service_scale):
    launch_config_consumed_service = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": SSH_IMAGE_UUID}
    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount_with_config(
            client, service_scale,
            launch_config_consumed_service, launch_config_service)

    return env, service, service_name, consumed_service_name


def create_env_with_multiple_svcs_and_volume_mounts(
        client, service_scale):

    launch_config_consumed_service1 = {
        "imageUuid": "docker:redis"}

    launch_config_consumed_service2 = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": SSH_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name1 = random_name.replace("-", "")

    random_name = random_str()
    consumed_service_name2 = random_name.replace("-", "")

    launch_config_service["dataVolumesFromLaunchConfigs"] = \
        [consumed_service_name1, consumed_service_name2]

    launch_config_consumed_service1["name"] = consumed_service_name1
    launch_config_consumed_service2["name"] = consumed_service_name2

    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service1,
                                launch_config_consumed_service2])

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name1 = \
        env.name + "_" + service.name + "_" + consumed_service_name1

    consumed_service_name2 = \
        env.name + "_" + service.name + "_" + consumed_service_name2

    service_name = env.name + "_" + service.name
    return env, service, service_name, \
        [consumed_service_name1, consumed_service_name2]


def create_env_with_multiple_levels_svcs_and_volume_mounts(
        client, service_scale):

    launch_config_consumed_service1 = {
        "imageUuid": "docker:redis"}

    launch_config_consumed_service2 = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": SSH_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name1 = random_name.replace("-", "")

    random_name = random_str()
    consumed_service_name2 = random_name.replace("-", "")

    launch_config_service["dataVolumesFromLaunchConfigs"] = \
        [consumed_service_name1]
    launch_config_consumed_service1["dataVolumesFromLaunchConfigs"] = \
        [consumed_service_name2]
    launch_config_consumed_service1["name"] = consumed_service_name1
    launch_config_consumed_service2["name"] = consumed_service_name2

    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service1,
                                launch_config_consumed_service2])

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name1 = \
        env.name + "_" + service.name + "_" + consumed_service_name1

    consumed_service_name2 = \
        env.name + "_" + service.name + "_" + consumed_service_name2

    service_name = env.name + "_" + service.name

    return \
        env, service, service_name, consumed_service_name1, \
        consumed_service_name2


def create_env_with_multiple_levels_svcs_and_volume_mounts_circular(
        client, service_scale):

    launch_config_consumed_service1 = {
        "imageUuid": "docker:redis"}

    launch_config_consumed_service2 = {
        "imageUuid": WEB_IMAGE_UUID}

    launch_config_service = {
        "imageUuid": SSH_IMAGE_UUID}

    random_name = random_str()
    consumed_service_name1 = random_name.replace("-", "")

    random_name = random_str()
    consumed_service_name2 = random_name.replace("-", "")

    launch_config_service["dataVolumesFromLaunchConfigs"] = \
        [consumed_service_name1]
    launch_config_consumed_service1["dataVolumesFromLaunchConfigs"] = \
        [consumed_service_name2]

    launch_config_consumed_service2["dataVolumesFromLaunchConfigs"] = \
        [consumed_service_name1]

    launch_config_consumed_service1["name"] = consumed_service_name1
    launch_config_consumed_service2["name"] = consumed_service_name2

    # Create Environment
    random_name = random_str()
    env_name = random_name.replace("-", "")
    env = client.create_environment(name=env_name)
    env = client.wait_success(env)
    assert env.state == "active"

    # Create service
    random_name = random_str()
    service_name = random_name.replace("-", "")
    service = client.create_service(
        name=service_name, environmentId=env.id,
        launchConfig=launch_config_service, scale=service_scale,
        secondaryLaunchConfigs=[launch_config_consumed_service1,
                                launch_config_consumed_service2])

    service = client.wait_success(service)
    assert service.state == "inactive"

    consumed_service_name1 = \
        env.name + "_" + service.name + "_" + consumed_service_name1

    consumed_service_name2 = \
        env.name + "_" + service.name + "_" + consumed_service_name2

    service_name = env.name + "_" + service.name
    return \
        env, service, service_name, consumed_service_name1, \
        consumed_service_name2


def env_with_2_svc_and_volume_mount(super_client, client, service_scale):

    env, service, service_name, consumed_service_name = \
        create_env_with_2_svc_and_volume_mount(
            client, service_scale)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])
    return env, service, service_name, consumed_service_name


def test_volume_mount_activate_env(client, super_client, socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service_name = \
        create_env_with_2_svc_and_volume_mount(client, service_scale)

    env = env.activateservices()
    env = client.wait_success(env, 120)
    assert env.state == "active"

    service = client.wait_success(service, 120)
    assert service.state == "active"

    delete_all(client, [env])


def test_volume_mount_activate_service(client, super_client,
                                       socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service_name = \
        create_env_with_2_svc_and_volume_mount(client, service_scale)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])

    delete_all(client, [env])


def test_multiple_volume_mount_activate_service(client, super_client,
                                                socat_containers):

    service_scale = 2

    env, service, service_name, consumed_services =\
        create_env_with_multiple_svcs_and_volume_mounts(
            client, service_scale)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_volume_mount(
        super_client, service, service_name,  consumed_services)
    delete_all(client, [env])


def test_multiple_level_volume_mount_activate_service(client, super_client,
                                                      socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service1, consumed_service2 =\
        create_env_with_multiple_levels_svcs_and_volume_mounts(
            client, service_scale)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service1])
    validate_volume_mount(super_client, service, consumed_service1,
                          [consumed_service2])
    delete_all(client, [env])


def test_multiple_level_volume_mount_activate_service_circular(client):

    service_scale = 2
    try:
        env, service, consumed_service1, consumed_service2 =\
            create_env_with_multiple_levels_svcs_and_volume_mounts_circular(
                client, service_scale)
    except Exception as e1:
        assert e1.error.code == "InvalidReference"
        assert e1.error.status == 422


def test_volume_mount_service_scale_up(client, super_client, socat_containers):

    service_scale = 2

    final_service_scale = 3

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])
    delete_all(client, [env])


def test_volume_mount_service_scale_down(client, super_client,
                                         socat_containers):
    service_scale = 4

    final_service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    service = client.update(service, scale=final_service_scale,
                            name=service.name)
    service = client.wait_success(service, 120)
    assert service.state == "active"
    assert service.scale == final_service_scale

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])
    delete_all(client, [env])


def test_volume_mount_consumed_services_stop_start_instance(
        client,  super_client, socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    container_name = consumed_service_name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 120)
    client.wait_success(service)

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])

    delete_all(client, [env])


def test_volume_mount_consumed_services_restart_instance(
        client,  super_client, socat_containers):
    service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    container_name = consumed_service_name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])

    delete_all(client, [env])


def test_volume_mount_consumed_services_delete_instance(
        client,  super_client, socat_containers):

    service_scale = 3

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    container_name = consumed_service_name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    client.wait_success(service)

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])

    delete_all(client, [env])


def test_volume_mount_deactivate_activate_environment(client, super_client,
                                                      socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    env = env.deactivateservices()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    wait_until_instances_get_stopped_for_service_with_sec_launch_configs(
        super_client, service)

    env = env.activateservices()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])
    delete_all(client, [env])


def test_volume_mount_services_stop_start_instance(
        client,  super_client, socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Stop instance
    container = client.wait_success(container.stop(), 120)
    client.wait_success(service)

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])

    delete_all(client, [env])


def test_volume_mount_services_restart_instance(client, super_client,
                                                socat_containers):
    service_scale = 3

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    container_name = env.name + "_" + service.name + "_2"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # restart instance
    container = client.wait_success(container.restart(), 120)
    assert container.state == 'running'

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])

    delete_all(client, [env])


def test_volume_mount_services_delete_instance(
        client,  super_client, socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    container_name = env.name + "_" + service.name + "_1"
    containers = client.list_container(name=container_name)
    assert len(containers) == 1
    container = containers[0]

    # Delete instance
    container = client.wait_success(client.delete(container))
    assert container.state == 'removed'

    client.wait_success(service)

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])

    delete_all(client, [env])


def test_volume_mount_services_deactivate_activate(
        client,  super_client, socat_containers):

    service_scale = 2

    env, service, service_name, consumed_service_name = \
        env_with_2_svc_and_volume_mount(super_client, client, service_scale)

    service = service.deactivate()
    service = client.wait_success(service, 120)
    assert service.state == "inactive"

    wait_until_instances_get_stopped_for_service_with_sec_launch_configs(
        super_client, service)

    service = service.activate()
    service = client.wait_success(service, 120)
    assert service.state == "active"

    validate_volume_mount(super_client, service, service_name,
                          [consumed_service_name])
    delete_all(client, [env])


def get_service_container_name_list(super_client, service, name):

    container = []
    instance_maps = super_client.list_serviceExposeMap(serviceId=service.id,
                                                       state="active")
    nameformat = re.compile(name + "_[0-9]{1,2}")
    for instance_map in instance_maps:
        c = super_client.by_id('container', instance_map.instanceId)
        if nameformat.match(c.name):
            containers = super_client.list_container(
                externalId=c.externalId,
                include="hosts")
            assert len(containers) == 1
            container.append(containers[0].externalId)

    return container


def validate_volume_mount(
        super_client, primary_service, service, consumed_services):
    print "Validating service - " + service

    containers = get_service_containers_with_name(super_client,
                                                  primary_service,
                                                  service)
    assert len(containers) == primary_service.scale

    consolidated_container_list = []
    mounted_container_names = []
    volumes_from_list = []

    for consumed_service_name in consumed_services:
        print "Validating Consumed Services: " + consumed_service_name
        mounted_containers = get_service_container_name_list(
            super_client, primary_service, consumed_service_name)
        assert len(mounted_containers) == primary_service.scale
        for mounted_container in mounted_containers:
            mounted_container_names.append(mounted_container)
        consolidated_container_list.append(mounted_containers)

    print "All container lists" + str(consolidated_container_list)
    print "All containers" + str(mounted_container_names)

    # For every container in the service , make sure that there is 1
    # mounted container volume from each of the consumed service
    for con in containers:
        host = super_client.by_id('host', con.hosts[0].id)
        docker_client = get_docker_client(host)
        inspect = docker_client.inspect_container(con.externalId)
        volumeFrom = inspect["HostConfig"]["VolumesFrom"]
        print con.name + "->" + str(volumeFrom)
        assert volumeFrom is not None
        assert len(volumeFrom) == len(consumed_services)

        container_list = consolidated_container_list[:]
        container_names = mounted_container_names[:]
        # Check that there is exactly only 1 entry from each of the
        # consumed services
        for volume in volumeFrom:
            volumes_from_list.append(volume)
            found = False
            for volume_list in container_list:
                if volume in volume_list:
                    container_list.remove(volume_list)
                    found = True
            if (not found):
                error_string = \
                    str(volume) + " is not in " + str(container_list)
                assert False, error_string
            # Make sure that the container is in the same host by inspecting it
            inspect = docker_client.inspect_container(volume)
            assert inspect is not None

    # Check that the volumes occur only once in consolidated list of
    # containers
    for volume in volumes_from_list:
        found = False
        for container in container_names:
            if (volume == container):
                container_names.remove(container)
                found = True
        if (not found):
            error_string = \
                str(volume) + " is not in " + str(container_names)
            assert False, error_string
