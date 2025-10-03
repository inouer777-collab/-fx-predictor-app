#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS App Runner FX予測アプリ（最終修正版）
環境変数はコード内で設定
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import ta

from flask import Flask, render_template_string, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps

# 環境変数をコード内で設定
os.environ.setdefault('FLASK_ENV', 'production')

# App Runner環境用設定
app = Flask(__name__)
app.secret_key = 'fx_predictor_aws_2024'

# レート制限設定
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 基本認証
def check_auth(username, password):
    return username == 'admin' and password == 'fx2024'

def authenticate():
    return '''
    <html>
    <head><title>FX予測アプリ - ログイン</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; text-align: center;">
    <h2>🔐 FX予測アプリ</h2>
    <form method="post" action="/login">
    <p><input type="text" name="username" placeholder="ユーザー名" required style="padding: 10px; width: 200px; margin: 5px;"></p>
    <p><input type="password" name="password" placeholder="パスワード" required style="padding: 10px; width: 200px; margin: 5px;"></p>
    <p><input type="submit" value="ログイン" style="padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer;"></p>
    </form>
    <p><small>ユーザー名: admin / パスワード: fx2024</small></p>
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

class FXPredictor:
    def __init__(self):
        self.models = {}
        self.currency_pairs = ['USDJPY=X', 'EURJPY=X', 'EURUSD=X']
        self.currency_names = {
            'USDJPY=X': 'USD/JPY',
            'EURJPY=X': 'EUR/JPY', 
            'EURUSD=X': 'EUR/USD'
        }
        
    def get_fx_data(self, symbol, period='1y'):
        """為替データを取得（期間を短縮してパフォーマンス向上）"""
        try:
            logging.info(f"データ取得開始: {symbol}")
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            if data.empty:
                logging.error(f"データ取得失敗: {symbol}")
                return None
            logging.info(f"データ取得成功: {symbol}, {len(data)}件")
            return data
        except Exception as e:
            logging.error(f"データ取得エラー {symbol}: {e}")
            return None
    
    def create_features(self, data):
        """テクニカル指標を作成（簡略化）"""
        try:
            df = data.copy()
            
            # 基本的な移動平均のみ
            df['SMA_5'] = ta.trend.sma_indicator(df['Close'], window=5)
            df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
            
            # RSI
            df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
            
            # 価格変動率
            df['Returns'] = df['Close'].pct_change()
            df['Volatility'] = df['Returns'].rolling(window=10).std()
            
            # ラグ特徴量（簡略化）
            for lag in [1, 2, 3]:
                df[f'Close_lag_{lag}'] = df['Close'].shift(lag)
            
            return df.dropna()
            
        except Exception as e:
            logging.error(f"特徴量作成エラー: {e}")
            return None
    
    def train_model(self, symbol):
        """モデルを訓練（軽量化）"""
        try:
            logging.info(f"モデル訓練開始: {symbol}")
            
            # データ取得
            data = self.get_fx_data(symbol)
            if data is None:
                return False
            
            # 特徴量作成
            df = self.create_features(data)
            if df is None:
                return False
            
            # 特徴量選択（簡略化）
            feature_columns = [
                'SMA_5', 'SMA_20', 'RSI', 'Volatility',
                'Close_lag_1', 'Close_lag_2', 'Close_lag_3'
            ]
            
            X = df[feature_columns].fillna(method='ffill').fillna(0)
            y = df['Close']
            
            # 訓練・テストデータ分割
            split_index = int(len(X) * 0.8)
            X_train, X_test = X[:split_index], X[split_index:]
            y_train, y_test = y[:split_index], y[split_index:]
            
            # 軽量モデル
            model = RandomForestRegressor(
                n_estimators=50,  # 100→50に削減
                max_depth=8,      # 10→8に削減
                random_state=42,
                n_jobs=1          # -1→1に変更（App Runner環境対応）
            )
            
            model.fit(X_train, y_train)
            
            # 精度評価
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            
            self.models[symbol] = {
                'model': model,
                'features': feature_columns,
                'mae': mae,
                'last_data': df.iloc[-1],
                'last_close': df['Close'].iloc[-1]
            }
            
            logging.info(f"{symbol} モデル訓練完了, MAE: {mae:.4f}")
            return True
            
        except Exception as e:
            logging.error(f"モデル訓練エラー {symbol}: {e}")
            return False
    
    def predict_future(self, symbol, days=10):
        """将来予測"""
        try:
            if symbol not in self.models:
                success = self.train_model(symbol)
                if not success:
                    return None
            
            model_info = self.models[symbol]
            model = model_info['model']
            features = model_info['features']
            
            # 最新データで予測
            latest_data = model_info['last_data'][features].values.reshape(1, -1)
            
            predictions = []
            current_close = model_info['last_close']
            
            # 10日間の予測
            for day in range(1, days + 1):
                pred_price = model.predict(latest_data)[0]
                
                # 予測結果の調整（極端な値を防ぐ）
                change_rate = (pred_price - current_close) / current_close
                if abs(change_rate) > 0.05:  # 5%以上の変動は制限
                    change_rate = 0.05 if change_rate > 0 else -0.05
                    pred_price = current_close * (1 + change_rate)
                
                pred_date = datetime.now() + timedelta(days=day)
                
                predictions.append({
                    'date': pred_date.strftime('%Y-%m-%d'),
                    'day': f"{day}日後",
                    'predicted_price': round(pred_price, 4),
                    'change': round(pred_price - model_info['last_close'], 4),
                    'change_rate': round((pred_price - model_info['last_close']) / model_info['last_close'] * 100, 2)
                })
            
            return {
                'symbol': symbol,
                'currency_name': self.currency_names[symbol],
                'current_price': round(model_info['last_close'], 4),
                'mae': round(model_info['mae'], 4),
                'predictions': predictions
            }
            
        except Exception as e:
            logging.error(f"予測エラー {symbol}: {e}")
            return None

# FX予測器のインスタンス
fx_predictor = FXPredictor()

# HTML テンプレート
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 FX予測アプリ - AWS App Runner版</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .prediction-card { margin-bottom: 20px; }
        .positive { color: #28a745; }
        .negative { color: #dc3545; }
        .neutral { color: #6c757d; }
        .loading { display: none; }
    </style>
</head>
<body>
    <div class="container mt-5">
        <div class="row">
            <div class="col-md-12 text-center">
                <h1>🚀 FX予測アプリ</h1>
                <p class="lead">AWS App Runner版 - 10日間毎日予測</p>
                <div class="alert alert-info">
                    <small>✅ デプロイ成功 | 🔐 認証済み | ☁️ AWS稼働中</small>
                </div>
                <hr>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-8 offset-md-2">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">📊 通貨ペア選択</h5>
                        <form method="POST" id="predictionForm">
                            <div class="mb-3">
                                <select class="form-select" name="currency_pair" required>
                                    <option value="">通貨ペアを選択してください</option>
                                    <option value="USDJPY=X">USD/JPY (米ドル/日本円)</option>
                                    <option value="EURJPY=X">EUR/JPY (ユーロ/日本円)</option>
                                    <option value="EURUSD=X">EUR/USD (ユーロ/米ドル)</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                🔮 10日間予測を実行
                            </button>
                        </form>
                        
                        <div class="loading mt-3">
                            <div class="text-center">
                                <div class="spinner-border" role="status">
                                    <span class="visually-hidden">予測計算中...</span>
                                </div>
                                <p class="mt-2">機械学習による予測計算中... (約10-20秒)</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        {% if prediction %}
        <div class="row mt-4">
            <div class="col-md-12">
                <div class="card prediction-card">
                    <div class="card-header bg-success text-white">
                        <h5>📈 {{ prediction.currency_name }} 予測結果</h5>
                        <small>現在価格: {{ prediction.current_price }} | 予測精度(MAE): {{ prediction.mae }}</small>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>日付</th>
                                        <th>予測価格</th>
                                        <th>変動額</th>
                                        <th>変動率</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for pred in prediction.predictions %}
                                    <tr>
                                        <td>{{ pred.date }} ({{ pred.day }})</td>
                                        <td><strong>{{ pred.predicted_price }}</strong></td>
                                        <td class="{% if pred.change > 0 %}positive{% elif pred.change < 0 %}negative{% else %}neutral{% endif %}">
                                            {{ "+" if pred.change > 0 else "" }}{{ pred.change }}
                                        </td>
                                        <td class="{% if pred.change_rate > 0 %}positive{% elif pred.change_rate < 0 %}negative{% else %}neutral{% endif %}">
                                            {{ "+" if pred.change_rate > 0 else "" }}{{ pred.change_rate }}%
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if error %}
        <div class="row mt-4">
            <div class="col-md-12">
                <div class="alert alert-danger">
                    <h6>❌ エラーが発生しました</h6>
                    <p>{{ error }}</p>
                    <small>しばらく待ってから再度お試しください。</small>
                </div>
            </div>
        </div>
        {% endif %}
        
        <div class="row mt-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-body">
                        <h6>📝 システム情報</h6>
                        <ul>
                            <li><strong>機械学習:</strong> Random Forest (軽量版)</li>
                            <li><strong>テクニカル分析:</strong> RSI, 移動平均, ボラティリティ</li>
                            <li><strong>データソース:</strong> Yahoo Finance API</li>
                            <li><strong>インフラ:</strong> AWS App Runner (自動スケーリング)</li>
                            <li><strong>セキュリティ:</strong> HTTPS + Basic認証</li>
                        </ul>
                        
                        <small class="text-muted">
                            ⚠️ 免責事項: この予測は教育・研究目的です。実際の投資判断には使用しないでください。
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('predictionForm').addEventListener('submit', function() {
            document.querySelector('.loading').style.display = 'block';
        });
    </script>
</body>
</html>
'''

@app.route('/')
@requires_auth
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/', methods=['POST'])
@requires_auth
@limiter.limit("5 per minute")  # レート制限を緩和
def predict():
    try:
        currency_pair = request.form.get('currency_pair')
        if not currency_pair:
            return render_template_string(HTML_TEMPLATE, error="通貨ペアを選択してください")
        
        logging.info(f"予測リクエスト: {currency_pair}")
        
        # 予測実行
        prediction = fx_predictor.predict_future(currency_pair, days=10)
        
        if prediction is None:
            return render_template_string(HTML_TEMPLATE, error="予測の計算に失敗しました。データ取得に問題がある可能性があります。")
        
        return render_template_string(HTML_TEMPLATE, prediction=prediction)
        
    except Exception as e:
        logging.error(f"予測処理エラー: {e}")
        return render_template_string(HTML_TEMPLATE, error=f"システムエラーが発生しました: {str(e)}")

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'app': 'FX Predictor AWS App Runner'
    })

@app.route('/test')
def test():
    return jsonify({
        'message': 'FX予測アプリは正常に動作しています',
        'timestamp': datetime.now().isoformat(),
        'environment': os.environ.get('FLASK_ENV', 'unknown')
    })

if __name__ == '__main__':
    # AWS App Runner環境
    port = int(os.environ.get('PORT', 8443))
    logging.info(f"FX予測アプリを起動中... ポート: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)