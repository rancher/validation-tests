from common_fixtures import *  # NOQA


def test_environment_rancher_compose(client):
    dockerCompose = '''redis:
    image: redis
    '''
    rancherCompose = '''redis:
    scale: 2
    '''
    env = client.create_environment(name=random_str(),
                                    dockerCompose=dockerCompose,
                                    rancherCompose=rancherCompose)
    env = client.wait_success(env)
    assert env.state == "active"

    assert len(env.services()) == 1
    assert env.services()[0].scale == 2
    assert env.services()[0].state == "inactive"

    env = client.wait_success(env.remove())
    assert env.state == "removed"


def stopped_transitioning(env):
    return env.transitioning != "yes"


def test_environment_failure(client):
    dockerCompose = '''redis:
    build: .
    '''

    rancherCompose = '''redis:
    scale: 2
    '''
    env = client.create_environment(name=random_str(),
                                    dockerCompose=dockerCompose,
                                    rancherCompose=rancherCompose)
    env = wait_for_condition(client, env, stopped_transitioning)
    assert env.state == "error"

    env = client.wait_success(env.remove())
    assert env.state == "removed"

#
# def test_environment_no_file_lookup(client):
#    dockerCompose = '''redis:
#    extends: dummyserv
#    '''
#
#    rancherCompose = '''redis:
#    scale: 2
#    '''
#    env = client.create_environment(name=random_str(),
#                                    dockerCompose=dockerCompose,
#                                    rancherCompose=rancherCompose)
#    env = wait_for_condition(client, env, stopped_transitioning)
#    assert env.state == "error"
#
#    env = client.wait_success(env.remove())
#    assert env.state == "removed"
