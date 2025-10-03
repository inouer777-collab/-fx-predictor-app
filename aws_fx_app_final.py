#!/usr/bin/env python3
import os
from flask import Flask, render_template_string, request
from functools import wraps

app = Flask(__name__)

# 基本認証
def check_auth(username, password):
    return username == 'admin' and password == 'fx2024'

def authenticate():
    return '''
    <h2>🔐 FX予測アプリ - ログイン</h2>
    <form method="post" action="/login">
    <p><input type="text" name="username" placeholder="admin" required></p>
    <p><input type="password" name="password" placeholder="fx2024" required></p>
    <p><input type="submit" value="ログイン"></p>
    </form>
    '''

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate(), 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    return '''
    <h1>🚀 FX予測アプリ - デプロイ成功！</h1>
    <p>✅ AWS App Runner で正常に動作しています</p>
    <p>📊 機械学習機能は次のアップデートで追加予定</p>
    <p>🔐 認証: admin / fx2024</p>
    <hr>
    <p><a href="/health">ヘルスチェック</a> | <a href="/test">テスト</a></p>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'message': 'FX予測アプリ稼働中'}

@app.route('/test')
def test():
    return {'message': 'デプロイ成功！AWS App Runner稼働中', 'port': os.environ.get('PORT', '8443')}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8443))
    app.run(host='0.0.0.0', port=port, debug=False)
