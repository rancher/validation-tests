from common_fixtures import *  # NOQA

TEST_SERVICE_OPT_IMAGE = 'ibuildthecloud/helloworld'
TEST_SERVICE_OPT_IMAGE_LATEST = TEST_SERVICE_OPT_IMAGE + ':latest'
TEST_SERVICE_OPT_IMAGE_UUID = 'docker:' + TEST_SERVICE_OPT_IMAGE_LATEST
LB_IMAGE_UUID = "docker:sangeetha/testlbsd:latest"
RCLICOMMANDS_SUBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'resources/ranchercli')
logger = logging.getLogger(__name__)

if_compose_data_files = pytest.mark.skipif(
    not os.environ.get('CATTLE_TEST_DATA_DIR'),
    reason='Docker compose files directory location not set')


def test_cli_create_service(super_client, client, rancher_cli_container):

    env_name = random_str().replace("-", "")
    launch_rancher_cli_from_file(
        client, RCLICOMMANDS_SUBDIR, "dc1.yml", env_name,
        "up -d", "Creating stack", "rc1.yml")

    env, service = get_env_service_by_name(client, env_name, "test1")

    # Confirm service is active and the containers are running
    assert service.state == "active"
    assert service.scale == 2
    assert service.name == "test1"

    check_config_for_service(super_client, service, {"test1": "value1"}, 1)

    container_list = get_service_container_list(super_client, service)
    assert len(container_list) == 2
    for container in container_list:
        assert container.state == "running"

    delete_all(client, [env])
