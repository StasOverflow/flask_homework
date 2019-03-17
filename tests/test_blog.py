import pytest
from blog.db import get_db


def test_index(client, auth):
    response = client.get('/')
    assert b"Log In" in response.data
    assert b"Register" in response.data

    auth.login()
    response = client.get('/')
    assert b'Log Out' in response.data
    assert b'test title' in response.data
    assert b'by test on 2018-01-01' in response.data
    assert b'test\nbody' in response.data
    assert b'href="/post/update/1"' in response.data


@pytest.mark.parametrize('path', (
    '/post/create',
    '/post/update/1',
    '/post/delete/1',
))
def test_login_required(client, path):
    response = client.post(path)
    assert response.headers['Location'] == 'http://localhost/auth/login'


def test_author_required(app, client, auth):
    # change the post author to another user
    with app.app_context():
        db = get_db()
        db.execute('UPDATE post SET author_id = 2 WHERE id = 1')
        db.commit()

    auth.login()
    # current user can't modify other user's post
    assert client.post('/post/update/1').status_code == 403
    assert client.post('/post/delete/1').status_code == 403
    # current user doesn't see edit link
    assert b'href="/update/1"' not in client.get('/').data


@pytest.mark.parametrize('path', (
    '/post/update/2',
    '/post/delete/2',
))
def test_exists_required(client, auth, path):
    auth.login()
    assert client.post(path).status_code == 404


def test_create(client, auth, app):
    auth.login()
    assert client.get('/post/create').status_code == 200
    client.post('/post/create', data={'title': 'created', 'body': ''})

    with app.app_context():
        db = get_db()
        count = db.execute('SELECT COUNT(id) FROM post').fetchone()[0]
        assert count == 2


def test_update(client, auth, app):
    auth.login()
    assert client.get('/post/update/1').status_code == 200
    client.post('/post/update/1', data={'title': 'updated', 'body': ''})

    with app.app_context():
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        assert post['title'] == 'updated'


@pytest.mark.parametrize('path', (
    '/post/create',
    '/post/update/1',
))
def test_create_update_validate(client, auth, path):
    auth.login()
    response = client.post(path, data={'title': '', 'body': ''})
    assert b'Title is required.' in response.data


def test_delete(client, auth, app):
    auth.login()
    response = client.post('/post/delete/1')
    assert response.headers['Location'] == 'http://localhost/'

    with app.app_context():
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        assert post is None


def test_post_detail(client, auth, app):
    assert client.get('/post/1').status_code == 200
    with app.app_context():
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        response = client.get('/post/1')
        assert bytes(post['title'], 'UTF-8') in response.data
        assert b'href="/post/update/1"' not in client.get('/').data
        # redirects to login page, as @login_required deco is set
        assert client.get('/post/update/1').status_code == 302


def test_post_detail_logged_in(client, auth, app):
    with app.app_context():
        auth.login()
        assert client.get('/post/1').status_code == 200
        db = get_db()
        post = db.execute('SELECT * FROM post WHERE id = 1').fetchone()
        response = client.get('/post/1')
        assert bytes(post['title'], 'UTF-8') in response.data
        assert b'href="/post/update/1"' in client.get('/').data
        assert client.get('/post/update/1').status_code == 200
