#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, render_template_string, request
from functools import wraps

app = Flask(__name__)

def check_auth(username, password):
    return username == 'admin' and password == 'fx2024'

def authenticate():
    return '''
    <html>
    <head><title>FX予測アプリ Phase 1</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto;">
    <h2>🔐 FX予測アプリ - Phase 1</h2>
    <form method="post" action="/login">
    <p><input type="text" name="username" placeholder="admin" required></p>
    <p><input type="password" name="password" placeholder="fx2024" required></p>
    <p><input type="submit" value="ログイン"></p>
    </form>
    </body>
    </html>
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
    <html>
    <head><title>FX予測アプリ - Phase 1</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto;">
    <h1>🚀 FX予測アプリ - Phase 1: データ処理基盤</h1>
    
    <div style="background: #e8f5e8; padding: 20px; border-radius: 5px; margin: 20px 0;">
    <h3>✅ Phase 1 機能</h3>
    <ul>
    <li>✅ AWS App Runner稼働中</li>
    <li>✅ pandas, numpy データ処理</li>
    <li>✅ 基本認証セキュリティ</li>
    <li>✅ レスポンシブUI</li>
    </ul>
    </div>
    
    <div style="background: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0;">
    <h3>📊 サンプルデータ処理デモ</h3>
    <p><strong>為替レートサンプル:</strong></p>
    ''' + get_sample_data() + '''
    </div>
    
    <div style="background: #d1ecf1; padding: 20px; border-radius: 5px; margin: 20px 0;">
    <h3>🔄 次のフェーズプレビュー</h3>
    <ul>
    <li>📈 Phase 2: リアルタイム為替データ取得</li>
    <li>🤖 Phase 3: 機械学習予測機能</li>
    <li>🎨 Phase 4: 高度なUI・可視化</li>
    </ul>
    </div>
    
    <hr>
    <p><a href="/health">ヘルスチェック</a> | <a href="/test">システム情報</a></p>
    </body>
    </html>
    '''

def get_sample_data():
    """サンプル為替データを生成"""
    dates = pd.date_range('2024-10-01', periods=7, freq='D')
    rates = np.random.uniform(149.0, 151.0, 7)
    
    df = pd.DataFrame({
        '日付': dates.strftime('%Y-%m-%d'),
        'USD/JPY': [f"{rate:.2f}" for rate in rates]
    })
    
    html_table = df.to_html(index=False, table_id="sample-data")
    return html_table

@app.route('/health')
def health():
    return {
        'status': 'healthy', 
        'phase': 'Phase 1 - データ処理基盤',
        'features': ['pandas', 'numpy', 'データ処理'],
        'timestamp': datetime.now().isoformat()
    }

@app.route('/test')
def test():
    return {
        'message': 'Phase 1 稼働中',
        'pandas_version': pd.__version__,
        'numpy_version': np.__version__,
        'next_phase': 'Phase 2 - yfinance データ取得'
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8443))
    app.run(host='0.0.0.0', port=port, debug=False)
