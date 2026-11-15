import pytest
from fastapi.testclient import TestClient

from backend.main import app, hardware, recognizer

client = TestClient(app)
PNG = b'\x89PNG\r\n\x1a\n' + b'x' * 25


def post_image(hint=None):
    data = {'hint': hint} if hint else {}
    return client.post('/api/classify', files={'photo': ('can.png', PNG, 'image/png')}, data=data)


def test_homepage():
    r = client.get('/')
    assert r.status_code == 200 and 'eco' in r.text.lower()


def test_frontend_assets_load_locally():
    assert client.get('/app.js').status_code == 200
    assert client.get('/style.css').status_code == 200
    assert client.get('/results.css').status_code == 200


def test_mock_command():
    r = client.post('/api/command', json={'command': 'RECYCLE'})
    assert r.status_code == 200 and r.json()['reply'] == 'OK RECYCLE' and r.json()['mock']


@pytest.mark.parametrize('command', ['RECYCLE', 'COMPOST', 'LANDFILL', 'UNKNOWN', 'OFF'])
def test_all_manual_commands(command):
    r = client.post('/api/command', json={'command': command})
    assert r.status_code == 200
    assert r.json()['command'] == command
    assert r.json()['reply'] == f'OK {command}'


def test_mock_status_never_claims_hardware_connected():
    data = client.get('/api/status').json()
    assert data['hardware']['mock'] is True
    assert data['hardware']['connected'] is False
    assert data['hardware_mode'] == 'mock'


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


def test_multi_item_results_do_not_send_a_collective_bin(monkeypatch):
    commands = []
    monkeypatch.setattr(hardware, 'send', lambda command: commands.append(command) or f'OK {command}')
    monkeypatch.setattr(recognizer, 'recognize', lambda image, hint=None: {
        'object_count': 2,
        'objects': [
            {'object_id': 1, 'item': 'practice can', 'material': 'metal',
             'needs_clarification': False, 'fusion_status': 'material_agreement',
             'detector_label': 'practice can'},
            {'object_id': 2, 'item': 'practice wrapper', 'material': 'plastic',
             'needs_clarification': False, 'fusion_status': 'material_agreement',
             'detector_label': 'practice wrapper'},
        ],
    })
    response = post_image()
    assert response.status_code == 200
    data = response.json()
    assert data['multiple_items'] is True
    assert len(data['objects']) == 2
    assert data['recommendation']['bin'] == 'UNKNOWN'
    assert data['commands_sent'] == []
    assert commands == []
