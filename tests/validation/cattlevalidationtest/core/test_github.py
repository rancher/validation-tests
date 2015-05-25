from common_fixtures import *  # NOQA
from selenium import webdriver
from selenium.webdriver.phantomjs.service import Service as PhantomJSService
from requests.auth import AuthBase
# test the github auth workflow
USER_SCOPE = 'github_user'
TEAM_SCOPE = 'github_team'
ORG_SCOPE = 'github_org'


class NewService(PhantomJSService):
    def __init__(self, *args, **kwargs):
        super(NewService, self).__init__(*args, **kwargs)
webdriver.phantomjs.webdriver.Service = NewService


if_github = pytest.mark.skipif(os.environ.get('API_AUTH_GITHUB'
                               '_CLIENT_SECRET') is None,
                               reason='API_AUTH_GITHUB'
                                      '_CLIENT_SECRET is not set')

BASE_URL = cattle_url() + '/v1/'
URL = BASE_URL + 'schemas'


@pytest.fixture(scope='session')
def config():
    needed_vars = [
        'API_AUTH_GITHUB_TEST_USER',
        'API_AUTH_GITHUB_TEST_PASS',
        'API_AUTH_GITHUB_CLIENT_ID',
        'API_AUTH_GITHUB_CLIENT_SECRET',
        'API_AUTH_RANCHER_TEST_PASS',

    ]
    for a in needed_vars:
        if os.getenv(a, None) is None:
            raise Exception('Please set ' + a + ' in the environment')
    config = {}
    config['username'] = os.getenv('API_AUTH_GITHUB_TEST_USER', None)
    config['password'] = os.getenv('API_AUTH_GITHUB_TEST_PASS', None)
    config['phantomjs_port'] = int(os.getenv('PHANTOMJS_WEBDRIVER_PORT', 4444))
    config['phantomjs_bin'] = os.getenv('PHANTOMJS_BIN',
                                        '/usr/local/bin/phantomjs')
    assert config['phantomjs_bin'] is not None
    config['client_id'] = os.getenv('API_AUTH_GITHUB_CLIENT_ID', None)
    config['client_secret'] = os.getenv('API_AUTH_GITHUB_CLIENT_SECRET', None)
    config['users'] = {}
    config['users']['1'] = {
        'password': os.getenv('API_AUTH_RANCHER_TEST_PASS', None),
        'username': os.getenv('API_AUTH_RANCHER_TEST_USER_1', 'ranchertest01')
    }
    config['users']['2'] = {
        'password': os.getenv('API_AUTH_RANCHER_TEST_PASS_2', None),
        'username': os.getenv('API_AUTH_RANCHER_TEST_USER_2', 'ranchertest02')
    }
    return config


@pytest.fixture(scope='module')
def github_request_code(config, cattle_url, admin_client, request, user=None):
    def fin():
            admin_client.create_githubconfig(enabled=False)
    request.addfinalizer(fin)
    username = config['username']
    password = config['password']
    if user is not None:
        username = user['username']
        password = user['password']

    driver = webdriver.PhantomJS(config['phantomjs_bin'],
                                 port=config['phantomjs_port'])
    max_wait = 60
    driver.set_page_load_timeout(max_wait)
    driver.set_script_timeout(max_wait)
    driver.implicitly_wait(10)
    # undo monkey patching
    webdriver.phantomjs.webdriver.Service = PhantomJSService

    driver.set_window_size(1120, 550)
    admin_client.create_githubconfig(enabled=True, accessMode='unrestricted',
                                     clientId=config['client_id'],
                                     clientSecret=config['client_secret'])
    urlx = "https://github.com/login/oauth/authorize?response_type=code&client_id=" +\
           config['client_id'] + "&scope=read:org"
    driver.get(urlx)
    driver.find_element_by_id('login_field').send_keys(username)
    driver.find_element_by_id('password').send_keys(password)
    driver.find_element_by_name('commit').submit()
    try:
        driver.find_element_by_class_name('btn-primary').click()
    except:
        pass
    driver.get('https://github.com')
    cookie_dict = dict(driver.get_cookie('_gh_sess'))
    cookie_dict = {'_gh_sess': cookie_dict['value']}
    cookie_dict['user_session'] = driver.get_cookie('user_session')['value']
    r = requests.get(urlx, cookies=cookie_dict, allow_redirects=False)
    redirect_url = r.headers['location']
    code = redirect_url.rsplit('=')[1]
    driver.quit()
    admin_client.create_githubconfig(enabled=False)
    return code


@pytest.fixture(scope='module')
def github_request_token(github_request_code):
    code = github_request_code

    c = requests.post(BASE_URL + 'token', {'code': code})
    return c.json()['jwt']


@pytest.fixture(scope='module')
def github_client(request, cattle_url, github_request_token, admin_client):
    github_client = from_env(url=cattle_url)
    github_client.delete_by_id = delete_by_id
    assert github_client.valid()
    jwt = github_request_token
    github_client._auth = GithubAuth(jwt, 'USER')

    def fin():
        admin_client.create_githubconfig(enabled=False)
    request.addfinalizer(fin)
    return github_client


def delete_by_id(self, type, id):
    url = self.schema.types[type].links.collection
    if url.endswith('/'):
        url = url + id
    else:
        url = '/'.join([url, id])
    return self._delete(url)


def _create_member(name='rancherio', role='member', type=ORG_SCOPE):
    return {
        'role': role,
        'externalId': name,
        'externalIdType': type
    }


def diff_members(members, got_members):
    assert len(members) == len(got_members)
    members_a = set([])
    members_b = set([])
    for member in members:
        members_a.add(member['externalId'] + '  ' + member['externalIdType']
                      + '  ' + member['role'])
    for member in got_members:
        members_b.add(member['externalId'] + '  ' + member['externalIdType']
                      + '  ' + member['role'])
    assert members_a == members_b


def get_plain_members(members):
    plain_members = []
    for member in members.data:
        plain_members.append({
            'role': member.role,
            'externalId': member.externalId,
            'externalIdType': member.externalIdType
        })
    return plain_members


class GithubAuth(AuthBase):
    def __init__(self, jwt, prj_id=None):
        # setup any auth-related data here
        self.jwt = jwt
        self.prj_id = prj_id

    def __call__(self, r):
        # modify and return the request
        r.headers['Authorization'] = 'Bearer ' + self.jwt
        if self.prj_id is not None:
            r.headers['X-API-Project-Id'] = self.prj_id
        return r


def switch_on_auth(admin_client, request, config):
    admin_client.create_githubconfig(enabled=True, accessMode='restricted',
                                     clientId=config['client_id'],
                                     clientSecret=config['client_secret'])

    def fin():
        admin_client.create_githubconfig(enabled=False)

    request.addfinalizer(fin)


@if_github
def test_github_auth_config_unauth_user(github_client, request, admin_client,
                                        config):
    switch_on_auth(admin_client, request, config)
#   do not set any auth headers
    no_auth = requests.get(URL)

#   test that auth is switched on
    assert no_auth.status_code == 401


@if_github
def test_github_auth_config_invalid_user(github_client, request,
                                         admin_client, config):
    switch_on_auth(admin_client, request, config)

#   set invalid auth headers
    bad_auth = requests.get(URL,
                            headers={'Authorization':
                                     'Bearer some_random_string'})

#   test that user does not have access
    assert bad_auth.status_code == 401


@if_github
def test_github_auth_config_valid_user(github_client, github_request_token,
                                       admin_client, request, config):
    switch_on_auth(admin_client, request, config)
    jwt = github_request_token

#   set valid auth headers
    schemas = requests.get(URL, headers={'Authorization': 'Bearer ' + jwt})

#   test that user has access
    assert schemas.status_code == 200


@pytest.mark.skipif(True, reason="Can't create githubconfigs with users o"
                                 "r orgs in tests right now.")
def test_github_auth_config_api_whitelist_users(admin_client, github_client,
                                                config):
    github_client.create_githubconfig(allowedUsers=[
        config['users']['1']['username'],
        config['users']['2']['username']
    ])

#   test that these users were whitelisted
    r = github_client.list_githubconfig()

    users = r[0]['allowedUsers']

    assert len(users) == 2

    assert config['users']['1']['username'] in users
    assert config['users']['2']['username'] in users
    assert 'ranchertest02' in users


@pytest.mark.skipif(True, reason="Can't create githubconfigs with users o"
                                 "r orgs in tests right now.")
def test_github_auth_config_api_whitelist_orgs(admin_client, request,
                                               github_client, config):
    switch_on_auth(admin_client, request, config)
    github_client.create_githubconfig(allowedOrganizations=['rancherio'])

#   test that these users were whitelisted
    r = github_client.list_githubconfig()

    orgs = r[0]['allowedOrganizations']

    assert len(orgs) == 1

    assert 'rancherio' in orgs


@pytest.mark.skipif(True, reason="Can't create githubconfigs with users o"
                                 "r orgs in tests right now.")
def test_github_add_whitelisted_user(admin_client, config, request,
                                     github_client):
    switch_on_auth(admin_client, request, config)
    #   set whitelisted orgs
    github_client.create_githubconfig(allowedUsers=[
        config['users']['1']['username']
    ])

    #   test that these users were whitelisted
    r = github_client.list_githubconfig()

    users = r[0]['allowedUsers']

    assert config['users']['1']['username'] in users

    new_token = github_request_code(config, config['users']['1'])

    assert new_token is not None


@pytest.mark.skipif(True, reason="Can't create githubconfigs with users o"
                                 "r orgs in tests right now.")
def test_github_projects(github_client, cattle_url, config, request,
                         admin_client):
    user_client = from_env(url=cattle_url)
    switch_on_auth(admin_client, request, config)

    #   set whitelisted orgs
    github_client.create_githubconfig(allowedUsers=[
        config['users']['1']['username']
    ])
    #   test that these users were whitelisted
    r = github_client.list_githubconfig()

    users = r[0]['allowedUsers']

    assert config['users']['1']['username'] in users

    new_token = github_request_code(config, cattle_url, admin_client, request,
                                    user=config['users']['1'])
    new_token = github_request_token(new_token)
    user_client._auth = GithubAuth(new_token, "user")
    members = [_create_member(
        name=config['users']['1']['username'],
        type=USER_SCOPE,
        role='owner'
    ),  _create_member()]
    project = user_client.create_project(members=members)
    assert len(project.projectMembers()) == 2
    diff_members(get_plain_members(project.projectMembers()), members)
    project = github_client.wait_success(project)
    project = github_client.wait_success(project.deactivate())
    project = github_client.wait_success(project.remove())
    project = github_client.wait_success(project.purge())
    project = user_client.by_id('project', project.id)
    assert project.state == 'purged'


@if_github
def test_github_id_name(github_client, config, cattle_url, request,
                        admin_client):
    user_client = from_env(url=cattle_url)
    switch_on_auth(admin_client, request, config)
    new_token = github_request_code(config, cattle_url, admin_client, request,
                                    user=config['users']['1'])
    new_token = github_request_token(new_token)
    user_client._auth = GithubAuth(new_token, "user")
    sent_members = [_create_member(
        name=config['users']['1']['username'],
        type=USER_SCOPE,
        role='owner'
    ),
        _create_member()
    ]
    project = user_client.create_project(members=sent_members)

    members = get_plain_members(project.projectMembers())
    assert len(members) == 2
    diff_members(members, sent_members)
