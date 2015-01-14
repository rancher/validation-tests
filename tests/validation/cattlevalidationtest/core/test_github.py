import urlparse
from common_fixtures import *  # NOQA
from selenium import webdriver
import json

# test the github auth workflow


if_github = pytest.mark.skipif(os.environ.get('API_AUTH_GITHUB'
                               '_TEST_USER') is None,
                               reason='API_AUTH_GITHUB_TEST_USER is not set')


@if_github
def test_github_token_has_access():

    URL = os.environ.get('CATTLE_TEST_URL',
                         'http://localhost:8080/v1/schemas')

    username = os.getenv('API_AUTH_GITHUB_TEST_USER', None)
    password = os.getenv('API_AUTH_GITHUB_TEST_PASS', None)

    driver = webdriver.PhantomJS()
    driver.set_window_size(1120, 550)
    client_id = os.getenv('API_AUTH_GITHUB_CLIENT_ID', None)

    if username is None or password is None or client_id is None:
        raise Exception('please set username, password and client_id in env')

    urlx = "https://github.com/login/oauth/authorize?client_id=" +\
           client_id + "&scope=read:org&state=random_string"
    driver.get(urlx)
    driver.find_element_by_id('login_field').send_keys(username)
    driver.find_element_by_id('password').send_keys(password)
    driver.find_element_by_name('commit').submit()
    cookie_dict = dict(driver.get_cookie('_gh_sess'))
    cookie_dict = {'_gh_sess': cookie_dict['value']}
    cookie_dict['user_session'] = driver.get_cookie('user_session')['value']
    r = None
    try:
        r = requests.get(urlx, cookies=cookie_dict, allow_redirects=False)
    except Exception as e:
        print e
    redirect_url = r.headers['location']
    query = urlparse.urlparse(redirect_url)[4]
    query = urlparse.parse_qs(query)

    BASE_URL = URL[:-1 * len('schemas')]

    c = requests.post(BASE_URL + 'token', {'code': query['code']})

    jwt = c.json()['jwt']

    requests.post(BASE_URL + 'githubconfig',
                  data=json.dumps({'enabled': 'true'}))

    no_auth = requests.get(URL)

    assert no_auth.status_code == 401

    bad_auth = requests.get(URL,
                            headers={'Authorization':
                                     'Bearer some_random_string'})

    assert bad_auth.status_code == 401

    schemas = requests.get(URL, headers={'Authorization': 'Bearer ' + jwt})

    assert schemas.status_code == 200

    requests.post(BASE_URL + 'githubconfig',
                  headers={'Authorization': 'Bearer ' + jwt},
                  data=json.dumps({'enabled': 'false'}))

    driver.quit()
