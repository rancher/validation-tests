from common_fixtures import *  # NOQA
from common_fixtures import _client_for_user
from selenium import webdriver
from requests.auth import AuthBase
# test the github auth workflow
USER_SCOPE = 'github_user'
TEAM_SCOPE = 'github_team'
ORG_SCOPE = 'github_org'

GITHUB_CLIENT_ID = os.getenv('API_AUTH_GITHUB_CLIENT_ID', None)
GITHUB_CLIENT_SECRET = os.getenv('API_AUTH_GITHUB_CLIENT_SECRET', None)


def create_client_id_and_secret(username=None, password=None):
    port = int(os.getenv('PHANTOMJS_WEBDRIVER_PORT', 4444))
    phantom_bin = os.getenv('PHANTOMJS_BIN', '/usr/local/bin/phantomjs')
    driver = webdriver.PhantomJS(phantom_bin, port=port)
    driver.delete_all_cookies()
    max_wait = 60
    driver.set_page_load_timeout(max_wait)
    driver.set_script_timeout(max_wait)
    driver.implicitly_wait(10)
    driver.set_window_size(1120, 550)

    driver.get('https://github.com/logout')
    try:
        driver.find_element_by_class_name('btn').click()
    except:
        pass
    driver.get('https://github.com/login')
    try:
        driver.find_element_by_id('login_field').send_keys(username)
        driver.find_element_by_id('password').send_keys(password)
        driver.find_element_by_name('commit').click()
    except:
        pass
    time.sleep(3)
    driver.get('https://github.com/settings/applications/new')
    url = base_url()[:-3]
    driver.find_element_by_id('oauth_application_name').send_keys(url)
    driver.find_element_by_id('oauth_application_url').send_keys(url)
    driver.find_element_by_id('oauth_application_callback_url').send_keys(url)
    driver.find_element_by_class_name('btn-primary').click()
    time.sleep(5)
    keys = driver.find_element_by_class_name('keys')
    keys = keys.text.split('\n')
    os.environ['API_AUTH_GITHUB_CLIENT_ID'] = keys[1]
    os.environ['API_AUTH_GITHUB_CLIENT_SECRET'] = keys[3]

if(GITHUB_CLIENT_ID is None and
   os.environ.get('API_AUTH_GITHUB_TEST_USER',  None) is not None):
    create_client_id_and_secret(
        username=os.getenv('API_AUTH_GITHUB_TEST_USER', None),
        password=os.getenv('API_AUTH_GITHUB_TEST_PASS', None))
    GITHUB_CLIENT_ID = os.getenv('API_AUTH_GITHUB_CLIENT_ID', None)
    GITHUB_CLIENT_SECRET = os.getenv('API_AUTH_GITHUB_CLIENT_SECRET', None)


def all_vars():
    needed_vars = [
        'API_AUTH_GITHUB_TEST_USER',
        'API_AUTH_GITHUB_TEST_PASS',
        'API_AUTH_RANCHER_TEST_USER_1',
        'API_AUTH_RANCHER_TEST_USER_2',
        'API_AUTH_RANCHER_TEST_PASS',
        'PHANTOMJS_BIN'
    ]
    for a in needed_vars:
        if os.getenv(a, None) is None:
            return a + ' is not Set.'
    return 'None'

if_github = pytest.mark.skipif(all_vars() != 'None', reason=all_vars())

URL = base_url() + 'schemas'


@pytest.fixture(scope='session')
def GITHUB_CLIENT(admin_client, request):

    def fin():
            admin_client.create_githubconfig(enabled=None,
                                             accessMode='unrestricted',
                                             allowedIdentities=[],
                                             clientId="")
    request.addfinalizer(fin)

    admin_client.create_githubconfig(enabled=False,
                                     accessMode='unrestricted',
                                     clientId=GITHUB_CLIENT_ID,
                                     clientSecret=GITHUB_CLIENT_SECRET)
    get_authed_token(username=os.getenv('API_AUTH_GITHUB_TEST_USER', None),
                     password=os.getenv('API_AUTH_GITHUB_TEST_PASS', None))

    admin_client.create_githubconfig(enabled=True,
                                     accessMode='unrestricted',
                                     clientId=GITHUB_CLIENT_ID,
                                     clientSecret=GITHUB_CLIENT_SECRET)
    return create_github_client(
        username=os.getenv('API_AUTH_GITHUB_TEST_USER', None),
        password=os.getenv('API_AUTH_GITHUB_TEST_PASS', None))


def get_authed_token(username=None,
                     password=None):
    port = int(os.getenv('PHANTOMJS_WEBDRIVER_PORT', 4444))
    phantom_bin = os.getenv('PHANTOMJS_BIN', '/usr/local/bin/phantomjs')
    driver = webdriver.PhantomJS(phantom_bin, port=port)
    driver.delete_all_cookies()
    max_wait = 60
    driver.set_page_load_timeout(max_wait)
    driver.set_script_timeout(max_wait)
    driver.implicitly_wait(10)
    driver.set_window_size(1120, 550)

    driver.get('{}logout'.format(base_url()[:-3]))
    driver.get('https://github.com/logout')
    try:
        driver.find_element_by_class_name('btn').click()
    except:
        pass
    urlx = "https://github.com/login/oauth/authorize?" + \
           "response_type=code&client_id=" +\
           GITHUB_CLIENT_ID + "&scope=read:org"
    driver.get('https://github.com/login')
    try:
        driver.find_element_by_id('login_field').send_keys(username)
        driver.find_element_by_id('password').send_keys(password)
        driver.find_element_by_name('commit').click()
    except:
        pass
    driver.get(urlx)
    try:
        driver.find_element_by_class_name('btn-primary').click()
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
    c = requests.post(base_url() + 'token', {'code': code})
    token = c.json()
    assert token['user'] == username
    return token


def create_github_client(username=None, password=None, project_id=None):
    client = _client_for_user('user', accounts())
    client.delete_by_id = delete_by_id
    assert client.valid()
    jwt = get_authed_token(username=username, password=password)['jwt']
    client._access_key = None
    client._secret_key = None

    client._auth = GithubAuth(jwt, prj_id=project_id)
    client.reload_schema()
    assert client.valid()
    return client


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
        if (member['role'] is not None):
            members_a.add(member['externalId'] + '  ' +
                          member['externalIdType'] + '  ' + member['role'])
        else:
            members_a.add(member['externalId'] + '  ' +
                          member['externalIdType'])
    for member in got_members:
        if (member['role'] is not None):
            members_b.add(member['externalId'] + '  ' +
                          member['externalIdType'] + '  ' + member['role'])
        else:
            members_b.add(member['externalId'] + '  ' +
                          member['externalIdType'])

    assert members_a == members_b


def get_plain_members(members):
    plain_members = []
    for member in members:
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


@if_github
def test_ui_turn_on_github(admin_client, base_url=base_url()):
    admin_client.create_githubconfig(clientId=None)

    username = os.getenv('API_AUTH_GITHUB_TEST_USER', None)
    password = os.getenv('API_AUTH_GITHUB_TEST_PASS', None)

    port = int(os.getenv('PHANTOMJS_WEBDRIVER_PORT', 4444))
    phantom_bin = os.getenv('PHANTOMJS_BIN', '/usr/local/bin/phantomjs')
    driver = webdriver.PhantomJS(phantom_bin, port=port)
    driver.delete_all_cookies()
    max_wait = 60
    driver.set_page_load_timeout(max_wait)
    driver.set_script_timeout(max_wait)
    driver.implicitly_wait(10)
    driver.set_window_size(1120, 550)
    driver.get('{}logout'.format(base_url[:-3]))
    driver.get('https://github.com/logout')
    try:
        driver.find_element_by_class_name('btn').click()
    except:
        pass
    driver.get('https://github.com/login')
    try:
        driver.find_element_by_id('login_field').send_keys(username)
        driver.find_element_by_id('password').send_keys(password)
        driver.find_element_by_name('commit').click()
    except:
        pass
    url = '{}admin/access/github'.format(base_url[:-3])
    driver.get(url)
    inputs = driver.find_elements_by_class_name('ember-text-field')
    inputs[0].clear()
    inputs[0].send_keys(GITHUB_CLIENT_ID)
    inputs[1].send_keys(GITHUB_CLIENT_SECRET)
    driver.find_element_by_class_name('btn-primary').click()
    try:
        driver.find_element_by_class_name('btn-primary').click()
    except:
        pass
    time.sleep(10)
    no_auth = requests.get(URL)
    assert no_auth.status_code == 401


@if_github
def test_github_auth_config_unauth_user(GITHUB_CLIENT):
    no_auth = requests.get(URL)
    assert no_auth.status_code == 401


@if_github
def test_github_auth_config_invalid_user(GITHUB_CLIENT):
    bad_auth = requests.get(URL,
                            headers={'Authorization':
                                     'Bearer some_random_string'})
    assert bad_auth.status_code == 401


@if_github
def test_github_auth_config_valid_user(GITHUB_CLIENT):
    token = get_authed_token(
        username=os.getenv('API_AUTH_RANCHER_TEST_USER_1', None),
        password=os.getenv('API_AUTH_RANCHER_TEST_PASS', None))

    schemas = requests.get(URL, headers={'Authorization': 'Bearer ' +
                                                          token['jwt']})
    assert schemas.status_code == 200


@if_github
def test_github_auth_config_api_whitelist_users(GITHUB_CLIENT):
    user1 = os.getenv('API_AUTH_RANCHER_TEST_USER_1', None)
    user1_pass = os.getenv('API_AUTH_RANCHER_TEST_PASS', None)
    user2 = os.getenv('API_AUTH_RANCHER_TEST_USER_2', None)
    user3 = os.getenv('API_AUTH_GITHUB_TEST_USER', None)

    user1 = GITHUB_CLIENT.list_identity(name=user1)[0]
    user2 = GITHUB_CLIENT.list_identity(name=user2)[0]
    user3 = GITHUB_CLIENT.list_identity(name=user3)[0]
    GITHUB_CLIENT.create_githubconfig(allowedIdentities=[user1, user2, user3],
                                      accessMode='restricted',
                                      enabled=True,
                                      clientId=GITHUB_CLIENT_ID,
                                      clientSecret=GITHUB_CLIENT_SECRET)
#   test that these users were whitelisted
    r = GITHUB_CLIENT.list_githubconfig()

    allowed_identities = r[0]['allowedIdentities']

    assert len(allowed_identities) == 3
    diff_members(get_plain_members([user1, user2, user3]),
                 get_plain_members(allowed_identities))

    new_token = get_authed_token(username=user1['login'], password=user1_pass)

    assert new_token is not None


@if_github
def test_github_auth_config_api_whitelist_orgs(GITHUB_CLIENT):
    rancher = GITHUB_CLIENT.list_identity(name='rancher')
    assert len(rancher) == 1
    GITHUB_CLIENT.create_githubconfig(allowedIdentities=[rancher[0]],
                                      accessMode='restricted',
                                      enabled=True,
                                      clientId=GITHUB_CLIENT_ID,
                                      clientSecret=GITHUB_CLIENT_SECRET)

#   test that these org was whitelisted
    r = GITHUB_CLIENT.list_githubconfig()

    allowed_identities = r[0]['allowedIdentities']

    assert len(allowed_identities) == 1

    diff_members(get_plain_members([rancher[0]]),
                 get_plain_members(allowed_identities))


@if_github
def test_github_projects(GITHUB_CLIENT):
    member1 = GITHUB_CLIENT.list_identity(
        name=os.getenv('API_AUTH_GITHUB_TEST_USER', None))[0]
    assert member1['login'] == os.getenv('API_AUTH_GITHUB_TEST_USER', None)
    member1['role'] = 'owner'

    member2 = GITHUB_CLIENT.list_identity(
        name=os.getenv('API_AUTH_RANCHER_TEST_USER_1', None))[0]
    assert member2['login'] == os.getenv('API_AUTH_RANCHER_TEST_USER_1', None)
    member2['role'] = 'member'

    member3 = GITHUB_CLIENT.list_identity(
        name='rancher')[0]
    assert member3['login'] == 'rancher'
    member3['role'] = 'member'

    members = [member1,  member2, member3]
    project = GITHUB_CLIENT.create_project(members=members)
    project = GITHUB_CLIENT.wait_success(project)
    diff_members(get_plain_members(project.projectMembers().data),
                 get_plain_members(members))

    github_client_2 = create_github_client(
        username=os.getenv('API_AUTH_RANCHER_TEST_USER_1', None),
        password=os.getenv('API_AUTH_RANCHER_TEST_PASS', None),
        project_id=project.id)

    project_from_2 = github_client_2.reload(project)
    diff_members(get_plain_members(project_from_2.projectMembers().data),
                 members)

    project = GITHUB_CLIENT.wait_success(project)
    project = GITHUB_CLIENT.wait_success(project.deactivate())
    project = GITHUB_CLIENT.wait_success(project.remove())
    project = GITHUB_CLIENT.wait_success(project.purge())
    project = GITHUB_CLIENT.by_id('project', project.id)
    assert project.state == 'purged'
