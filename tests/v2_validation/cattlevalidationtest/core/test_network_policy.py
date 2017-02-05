from common_fixtures import *  # NOQA

test_network_policy = os.environ.get(
    'TEST_NETWORK_POLICY', "False")
np_reason = \
    'Rancher NetworkPolicy Manager needs to de deployed in "Default" env'
if_network_policy = pytest.mark.skipif(test_network_policy != "True",
                                       reason=np_reason)

NETWORKPOLICY_SUBDIR = \
    os.path.join(os.path.dirname(os.path.realpath(__file__)),
                 'resources/networkpolicy')
policy_within_stack = {"within": "stack", "action": "allow"}
policy_groupby = {"between": {"groupBy": "com.rancher.stack.location"},
                  "action": "allow"}

if_compose_data_files = pytest.mark.skipif(
    not os.path.isdir(NETWORKPOLICY_SUBDIR),
    reason='Docker compose files directory location not set/ does not Exist')

shared_environment = {"env": []}


@pytest.fixture(scope='session', autouse=True)
def create_env_for_network_policy(request, client):
    env1 = create_stack_with_service(client, "stack1.yml", "stack1-rc.yml")
    assert len(env1.services()) == 4
    env2 = create_stack_with_service(client, "stack2.yml", "stack2-rc.yml")
    assert len(env2.services()) == 4
    shared_environment["env"].append(env1)
    shared_environment["env"].append(env2)
    shared_environment["env1_test1allow"] = \
        get_service_by_name(client, env1,  "test1allow")
    shared_environment["env1_test2allow"] = \
        get_service_by_name(client, env1,  "test2allow")
    shared_environment["env1_test3deny"] = \
        get_service_by_name(client, env1,  "test3deny")
    shared_environment["env1_test4deny"] = \
        get_service_by_name(client, env1,  "test4deny")
    shared_environment["env2_test1allow"] = \
        get_service_by_name(client, env2,  "test1allow")
    shared_environment["env2_test2allow"] = \
        get_service_by_name(client, env2,  "test2allow")
    shared_environment["env2_test3deny"] = \
        get_service_by_name(client, env2,  "test3deny")
    shared_environment["env2_test4deny"] = \
        get_service_by_name(client, env2,  "test4deny")

    def fin():
        to_delete = [env1, env2]
        delete_all(client, to_delete)

    request.addfinalizer(fin)


def validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client):
    time.sleep(sleep_interval)
    validate_connectivity_between_services(
        admin_client, shared_environment["env1_test1allow"],
        [shared_environment["env1_test2allow"],
         shared_environment["env1_test3deny"],
         shared_environment["env1_test4deny"]],
        connection="allow")
    validate_connectivity_between_services(
        admin_client, shared_environment["env1_test1allow"],
        [shared_environment["env2_test1allow"],
         shared_environment["env2_test2allow"],
         shared_environment["env2_test3deny"],
         shared_environment["env2_test4deny"]],
        connection="deny")


def validate_default_network_action_deny_networkpolicy_none(
        admin_client):
    time.sleep(sleep_interval)
    validate_connectivity_between_services(
        admin_client, shared_environment["env1_test1allow"],
        [shared_environment["env1_test2allow"],
         shared_environment["env1_test3deny"],
         shared_environment["env1_test4deny"],
         shared_environment["env2_test1allow"],
         shared_environment["env2_test2allow"],
         shared_environment["env2_test3deny"],
         shared_environment["env2_test4deny"]],
        connection="deny")


def validate_default_network_action_deny_networkpolicy_groupby(
        admin_client):
    time.sleep(sleep_interval)
    validate_connectivity_between_services(
        admin_client, shared_environment["env1_test1allow"],
        [shared_environment["env1_test2allow"],
         shared_environment["env2_test1allow"],
         shared_environment["env2_test2allow"]],
        connection="allow")

    validate_connectivity_between_services(
        admin_client, shared_environment["env1_test1allow"],
        [shared_environment["env1_test3deny"],
         shared_environment["env1_test4deny"],
         shared_environment["env2_test3deny"],
         shared_environment["env2_test4deny"]],
        connection="deny")

    validate_connectivity_between_services(
        admin_client, shared_environment["env1_test3deny"],
        [shared_environment["env2_test3deny"]],
        connection="allow")

    validate_connectivity_between_services(
        admin_client, shared_environment["env1_test3deny"],
        [shared_environment["env1_test1allow"],
         shared_environment["env1_test2allow"],
         shared_environment["env1_test4deny"],
         shared_environment["env2_test1allow"],
         shared_environment["env2_test2allow"],
         shared_environment["env2_test4deny"]],
        connection="deny")


@if_network_policy
def test_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client, client):
    set_network_policy(client, "deny", policy_within_stack)
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy
def test_dna_deny_np_allow_within_stacks_stop_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_within_stack)
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy
def test_dna_deny_np_allow_within_stacks_delete_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_within_stack)
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy
def test_dna_deny_np_allow_within_stacks_restart_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_within_stack)
    restart_service_instances(client, shared_environment["env"][0],
                              shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_allow_within_stacks(
        admin_client)


@if_network_policy
def test_default_network_action_deny_networkpolicy_none(admin_client, client):
    set_network_policy(client, "deny")
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy
def test_dna_deny_np_none_stop_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny")
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy
def test_dna_deny_np_none_delete_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny")
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy
def test_dna_deny_np_none_restart_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny")
    restart_service_instances(client, shared_environment["env"][0],
                              shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_none(
        admin_client)


@if_network_policy
def test_default_network_action_deny_networkpolicy_groupby(
        admin_client, client):
    set_network_policy(client, "deny", policy_groupby)
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


@if_network_policy
def test_dna_deny_np_groupby_stop_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_groupby)
    stop_service_instances(client, shared_environment["env"][0],
                           shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


@if_network_policy
def test_dna_deny_np_groupby_delete_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_groupby)
    delete_service_instances(client, shared_environment["env"][0],
                             shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


@if_network_policy
def test_dna_deny_np_groupby_restart_service(
        admin_client, client, socat_containers):
    set_network_policy(client, "deny", policy_groupby)
    restart_service_instances(client, shared_environment["env"][0],
                              shared_environment["env1_test1allow"], [1])
    validate_default_network_action_deny_networkpolicy_groupby(
        admin_client)


def create_stack_with_service(client, dc_file, rc_file):
    random_name = random_str()
    env_name = random_name.replace("-", "")
    dockerCompose = readDataFile(NETWORKPOLICY_SUBDIR, dc_file)
    rancherCompose = readDataFile(NETWORKPOLICY_SUBDIR, rc_file)
    env = client.create_stack(name=env_name,
                              dockerCompose=dockerCompose,
                              rancherCompose=rancherCompose,
                              startOnCreate=True)
    env = client.wait_success(env, timeout=300)
    assert env.state == "active"

    for service in env.services():
        wait_for_condition(
            client, service,
            lambda x: x.state == "active",
            lambda x: 'State is: ' + x.state,
            timeout=60)
    return env


def set_network_policy(client, defaultPolicyAction="allow", policy=None):
    networks = client.list_network(name='ipsec')
    assert len(networks) == 1
    network = networks[0]
    network = client.update(
        network, defaultPolicyAction=defaultPolicyAction, policy=policy)
    network = wait_success(client, network)
    assert network.defaultPolicyAction == defaultPolicyAction
