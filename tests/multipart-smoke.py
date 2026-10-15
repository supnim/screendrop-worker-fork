"""Run against `bun run dev` with UPLOAD_TOKEN in the environment."""
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get('SCREENDROP_URL', 'http://127.0.0.1:3000')
TOKEN = os.environ['UPLOAD_TOKEN']

def call(method, path, body=None, headers=None, status=200, auth=True):
    headers = {"User-Agent": "ScreendropMultipartSmoke/1.0", **(headers or {})}
    if auth:
        headers['Authorization'] = 'Bearer ' + TOKEN
    if isinstance(body, dict):
        body = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as error:
        response = error
    data = response.read()
    assert response.status == status, (method, path, response.status, data[:500])
    if response.headers.get_content_type() == 'application/json':
        return json.loads(data)
    return data

headers = {'X-Filename': 'multipart-test.bin', 'Content-Type': 'application/octet-stream', 'X-Title': 'Multipart%20test', 'X-Social-Enabled': 'false'}
call('POST', '/api/upload/multipart', headers=headers, status=401, auth=False)
session = call('POST', '/api/upload/multipart', headers=headers, status=201)
path = '/api/upload/multipart/' + session['id']
def query(number=1):
    return '?' + urllib.parse.urlencode({'key': session['key'], 'uploadId': session['uploadId'], 'partNumber': number})
call('PUT', path + query(0), b'x', status=400)
call('PUT', path + '?' + urllib.parse.urlencode({'key': 'uploads/other/test', 'uploadId': session['uploadId'], 'partNumber': 1}), b'x', status=400)
first = bytes(range(256)) * (5 * 1024 * 1024 // 256)
last = b'final part'
p1 = call('PUT', path + query(1), first)
p1 = call('PUT', path + query(1), first)
assert p1['partNumber'] == 1
p2 = call('PUT', path + query(2), last)
body = {'key': session['key'], 'uploadId': session['uploadId'], 'parts': [p2, p1]}
result = call('POST', path, body, status=201)
assert result['size'] == len(first) + len(last)
assert call('POST', path, body, status=201) == result
media = call('GET', '/api/media/' + session['id'])
assert hashlib.sha256(media).digest() == hashlib.sha256(first + last).digest()
call('DELETE', '/api/upload/' + session['id'])
session = call('POST', '/api/upload/multipart', headers=headers, status=201)
path = '/api/upload/multipart/' + session['id']
call('PUT', path + query(), first)
call('DELETE', path + query())
call('POST', path, {'key': session['key'], 'uploadId': session['uploadId'], 'parts': [p1]}, status=400)
# Existing small-file API remains compatible.
result = call('PUT', '/api/upload', b'small-file', headers, status=201)
assert call('GET', '/api/media/' + result['id']) == b'small-file'
call('DELETE', '/api/upload/' + result['id'])
print('PASS: authentication, validation, part retry, completion retry, byte integrity, abort, legacy upload')
