from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)
PNG = b'\x89PNG\r\n\x1a\n' + b'x' * 25


def post_image(hint=None):
    data = {'hint': hint} if hint else {}
    return client.post('/api/classify', files={'photo': ('can.png', PNG, 'image/png')}, data=data)


def test_homepage():
    r = client.get('/')
    assert r.status_code == 200 and 'eco' in r.text.lower()


def test_mock_command():
    r = client.post('/api/command', json={'command': 'RECYCLE'})
    assert r.status_code == 200 and r.json()['reply'] == 'OK RECYCLE' and r.json()['mock']


def test_reject_command():
    assert client.post('/api/command', json={'command': 'TEXT hacked'}).status_code == 400


def test_hint_still_unknown():
    r = post_image('aluminum can')
    assert r.status_code == 200
    data = r.json()
    assert data['recognition']['item'] == 'aluminum can'
    assert data['recommendation']['bin'] == 'UNKNOWN'
    assert data['mock_recognition'] and data['mock_hardware']
    assert data['commands_sent'] == ['UNKNOWN', 'TEXT aluminum can']


def test_no_hint_clarification():
    data = post_image().json()
    assert data['recommendation']['bin'] == 'UNKNOWN'
    assert data['recognition']['needs_clarification']
    assert data['recognition']['question']


def test_file_type_rejection():
    r = client.post('/api/classify', files={'photo': ('x.txt', b'hello', 'text/plain')})
    assert r.status_code == 415


def test_file_size_rejection():
    r = client.post('/api/classify', files={'photo': ('huge.png', PNG + b'0' * (10 * 1024 * 1024), 'image/png')})
    assert r.status_code == 413
