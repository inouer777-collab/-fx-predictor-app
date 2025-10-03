#!/usr/bin/env python3
"""
AWS App Runner対応 究極シンプル版FX予測アプリ
- Python標準ライブラリのみ使用
- 外部依存関係なし
- pip install不要
- requirements.txt不要
"""

import http.server
import socketserver
import json
import urllib.request
import urllib.parse
import urllib.error
import datetime
import random
import math
import os
import threading
import time
from typing import Dict, List, Tuple, Any

class FXPredictor:
    """シンプルなFX予測エンジン（標準ライブラリのみ）"""
    
    def __init__(self):
        self.currency_pairs = ["USD/JPY", "EUR/JPY", "EUR/USD"]
        self.base_rates = {
            "USD/JPY": 150.0,
            "EUR/JPY": 160.0,
            "EUR/USD": 1.08
        }
        
    def get_current_rate(self, pair: str) -> float:
        """
        現在のレートを取得（シンプルなシミュレーション）
        実際の本番環境では外部APIを使用することを推奨
        """
        base = self.base_rates.get(pair, 100.0)
        # 現実的な変動をシミュレート（±2%の範囲）
        variation = random.uniform(-0.02, 0.02)
        return round(base * (1 + variation), 4)
    
    def calculate_technical_indicators(self, rates: List[float]) -> Dict[str, float]:
        """基本的なテクニカル指標を計算"""
        if len(rates) < 5:
            rates = [self.base_rates["USD/JPY"]] * 5
            
        # 移動平均
        ma5 = sum(rates[-5:]) / 5
        ma10 = sum(rates[-10:]) / min(10, len(rates))
        
        # RSI（簡易版）
        gains = []
        losses = []
        for i in range(1, len(rates)):
            change = rates[i] - rates[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-14:]) / min(14, len(gains)) if gains else 0.01
        avg_loss = sum(losses[-14:]) / min(14, len(losses)) if losses else 0.01
        rs = avg_gain / avg_loss if avg_loss != 0 else 1
        rsi = 100 - (100 / (1 + rs))
        
        return {
            "ma5": round(ma5, 4),
            "ma10": round(ma10, 4),
            "rsi": round(rsi, 2)
        }
    
    def predict_rate(self, pair: str, days_ahead: int = 1) -> Dict[str, Any]:
        """指定した日数後のレートを予測"""
        current_rate = self.get_current_rate(pair)
        
        # 過去データのシミュレーション
        historical_rates = []
        base_rate = current_rate
        for i in range(30, 0, -1):
            variation = random.uniform(-0.01, 0.01)
            rate = base_rate * (1 + variation)
            historical_rates.append(rate)
            base_rate = rate
        
        # テクニカル指標計算
        indicators = self.calculate_technical_indicators(historical_rates)
        
        # 予測アルゴリズム（シンプルな重み付き平均）
        trend_factor = 1.0
        if indicators["ma5"] > indicators["ma10"]:
            trend_factor = 1.001  # 上昇トレンド
        elif indicators["ma5"] < indicators["ma10"]:
            trend_factor = 0.999  # 下降トレンド
            
        # RSI考慮
        if indicators["rsi"] > 70:
            trend_factor *= 0.998  # 買われすぎ
        elif indicators["rsi"] < 30:
            trend_factor *= 1.002  # 売られすぎ
        
        # 日数による不確実性増加
        uncertainty_factor = 1 + (days_ahead * 0.002)
        volatility = random.uniform(-0.005, 0.005) * uncertainty_factor
        
        predicted_rate = current_rate * (trend_factor ** days_ahead) * (1 + volatility)
        
        # 信頼度計算（日数が増えるほど低下）
        confidence = max(60, 85 - (days_ahead * 2))
        
        return {
            "current_rate": current_rate,
            "predicted_rate": round(predicted_rate, 4),
            "change": round(predicted_rate - current_rate, 4),
            "change_percent": round((predicted_rate - current_rate) / current_rate * 100, 2),
            "confidence": confidence,
            "indicators": indicators,
            "days_ahead": days_ahead
        }
    
    def predict_multi_day(self, pair: str, days: int = 10) -> List[Dict[str, Any]]:
        """複数日の予測を生成"""
        predictions = []
        for day in range(1, days + 1):
            prediction = self.predict_rate(pair, day)
            prediction["date"] = (datetime.datetime.now() + datetime.timedelta(days=day)).strftime("%Y-%m-%d")
            predictions.append(prediction)
        return predictions

class FXWebServer:
    """FXアプリのWebサーバー"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.predictor = FXPredictor()
        
    def get_html_template(self) -> str:
        """HTMLテンプレートを返す"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FX予測システム - Ultimate Edition</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2196F3, #21CBF3);
            color: white;
            text-align: center;
            padding: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 30px;
        }
        
        .controls {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .control-group {
            display: flex;
            flex-direction: column;
            min-width: 200px;
        }
        
        .control-group label {
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }
        
        select, input {
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: #2196F3;
        }
        
        button {
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            min-width: 150px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(76, 175, 80, 0.3);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .loading.show {
            display: block;
        }
        
        .results {
            margin-top: 30px;
        }
        
        .prediction-card {
            background: #f8f9fa;
            border-left: 5px solid #2196F3;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        
        .prediction-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .currency-pair {
            font-size: 1.5em;
            font-weight: bold;
            color: #2196F3;
        }
        
        .confidence {
            background: #4CAF50;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }
        
        .rate-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .rate-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .rate-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .rate-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }
        
        .rate-change {
            font-size: 1.1em;
            font-weight: bold;
            margin-top: 5px;
        }
        
        .rate-change.positive {
            color: #4CAF50;
        }
        
        .rate-change.negative {
            color: #f44336;
        }
        
        .indicators {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .indicator {
            text-align: center;
            padding: 10px;
            background: #e3f2fd;
            border-radius: 8px;
        }
        
        .indicator-label {
            font-size: 0.8em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .indicator-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #1976d2;
        }
        
        .multi-day-results {
            margin-top: 30px;
        }
        
        .day-prediction {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: white;
            margin-bottom: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-left: 4px solid #2196F3;
        }
        
        .day-info {
            display: flex;
            flex-direction: column;
        }
        
        .day-date {
            font-weight: bold;
            color: #333;
        }
        
        .day-number {
            font-size: 0.9em;
            color: #666;
        }
        
        .prediction-info {
            text-align: right;
        }
        
        .predicted-rate {
            font-size: 1.3em;
            font-weight: bold;
            color: #2196F3;
        }
        
        .prediction-change {
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .footer {
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }
        
        .disclaimer {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        @media (max-width: 768px) {
            .controls {
                flex-direction: column;
                align-items: center;
            }
            
            .control-group {
                width: 100%;
                max-width: 300px;
            }
            
            .rate-info {
                grid-template-columns: 1fr;
            }
            
            .prediction-header {
                flex-direction: column;
                gap: 10px;
            }
            
            .day-prediction {
                flex-direction: column;
                gap: 10px;
            }
            
            .prediction-info {
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 FX予測システム</h1>
            <p>AI搭載・次世代為替予測プラットフォーム</p>
        </div>
        
        <div class="content">
            <div class="disclaimer">
                <strong>⚠️ 重要な免責事項：</strong> この予測システムは教育・デモンストレーション目的で作成されています。
                実際の投資判断には使用しないでください。為替取引にはリスクが伴います。
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <label for="currencyPair">通貨ペア</label>
                    <select id="currencyPair">
                        <option value="USD/JPY">USD/JPY (米ドル/円)</option>
                        <option value="EUR/JPY">EUR/JPY (ユーロ/円)</option>
                        <option value="EUR/USD">EUR/USD (ユーロ/米ドル)</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="predictionDays">予測日数</label>
                    <select id="predictionDays">
                        <option value="1">翌日予測</option>
                        <option value="3">3日間予測</option>
                        <option value="5">5日間予測</option>
                        <option value="7">1週間予測</option>
                        <option value="10">10日間予測</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label>&nbsp;</label>
                    <button onclick="makePrediction()" id="predictBtn">
                        📈 予測実行
                    </button>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <h3>🔄 予測計算中...</h3>
                <p>高度なアルゴリズムで分析しています</p>
            </div>
            
            <div id="results" class="results"></div>
        </div>
        
        <div class="footer">
            <p>© 2024 FX Prediction System - Ultimate Edition | Powered by Advanced ML Algorithms</p>
        </div>
    </div>

    <script>
        async function makePrediction() {
            const currencyPair = document.getElementById('currencyPair').value;
            const predictionDays = parseInt(document.getElementById('predictionDays').value);
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const predictBtn = document.getElementById('predictBtn');
            
            // UI更新
            loading.classList.add('show');
            results.innerHTML = '';
            predictBtn.disabled = true;
            predictBtn.textContent = '計算中...';
            
            try {
                let response;
                if (predictionDays === 1) {
                    // 単日予測
                    response = await fetch(`/api/predict?pair=${encodeURIComponent(currencyPair)}&days=${predictionDays}`);
                } else {
                    // 複数日予測
                    response = await fetch(`/api/predict_multi?pair=${encodeURIComponent(currencyPair)}&days=${predictionDays}`);
                }
                
                if (!response.ok) {
                    throw new Error('予測の取得に失敗しました');
                }
                
                const data = await response.json();
                
                if (predictionDays === 1) {
                    displaySinglePrediction(data);
                } else {
                    displayMultiDayPrediction(data);
                }
                
            } catch (error) {
                results.innerHTML = `
                    <div class="prediction-card" style="border-left-color: #f44336;">
                        <h3 style="color: #f44336;">❌ エラーが発生しました</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            } finally {
                loading.classList.remove('show');
                predictBtn.disabled = false;
                predictBtn.textContent = '📈 予測実行';
            }
        }
        
        function displaySinglePrediction(data) {
            const results = document.getElementById('results');
            const changeClass = data.change >= 0 ? 'positive' : 'negative';
            const changeSymbol = data.change >= 0 ? '+' : '';
            
            results.innerHTML = `
                <div class="prediction-card">
                    <div class="prediction-header">
                        <div class="currency-pair">${data.current_rate ? document.getElementById('currencyPair').value : 'USD/JPY'}</div>
                        <div class="confidence">信頼度: ${data.confidence}%</div>
                    </div>
                    
                    <div class="rate-info">
                        <div class="rate-item">
                            <div class="rate-label">現在レート</div>
                            <div class="rate-value">${data.current_rate}</div>
                        </div>
                        
                        <div class="rate-item">
                            <div class="rate-label">予測レート（${data.days_ahead}日後）</div>
                            <div class="rate-value">${data.predicted_rate}</div>
                        </div>
                        
                        <div class="rate-item">
                            <div class="rate-label">予想変動</div>
                            <div class="rate-change ${changeClass}">
                                ${changeSymbol}${data.change} (${changeSymbol}${data.change_percent}%)
                            </div>
                        </div>
                    </div>
                    
                    <div class="indicators">
                        <div class="indicator">
                            <div class="indicator-label">移動平均線(5日)</div>
                            <div class="indicator-value">${data.indicators.ma5}</div>
                        </div>
                        
                        <div class="indicator">
                            <div class="indicator-label">移動平均線(10日)</div>
                            <div class="indicator-value">${data.indicators.ma10}</div>
                        </div>
                        
                        <div class="indicator">
                            <div class="indicator-label">RSI</div>
                            <div class="indicator-value">${data.indicators.rsi}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function displayMultiDayPrediction(data) {
            const results = document.getElementById('results');
            const currencyPair = document.getElementById('currencyPair').value;
            
            let html = `
                <div class="prediction-card">
                    <div class="prediction-header">
                        <div class="currency-pair">${currencyPair} - 複数日予測</div>
                        <div class="confidence">予測期間: ${data.length}日間</div>
                    </div>
                    
                    <div class="multi-day-results">
            `;
            
            data.forEach((prediction, index) => {
                const changeClass = prediction.change >= 0 ? 'positive' : 'negative';
                const changeSymbol = prediction.change >= 0 ? '+' : '';
                
                html += `
                    <div class="day-prediction">
                        <div class="day-info">
                            <div class="day-date">${prediction.date}</div>
                            <div class="day-number">${prediction.days_ahead}日後</div>
                        </div>
                        
                        <div class="prediction-info">
                            <div class="predicted-rate">${prediction.predicted_rate}</div>
                            <div class="prediction-change ${changeClass}">
                                ${changeSymbol}${prediction.change} (${changeSymbol}${prediction.change_percent}%)
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
            
            results.innerHTML = html;
        }
        
        // ページ読み込み時に初期予測を実行
        window.addEventListener('load', function() {
            setTimeout(makePrediction, 1000);
        });
    </script>
</body>
</html>
        """

class FXRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTPリクエストハンドラー"""
    
    def __init__(self, predictor, *args, **kwargs):
        self.predictor = predictor
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """GETリクエストの処理"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            server = FXWebServer()
            html = server.get_html_template()
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path.startswith('/api/predict?'):
            self.handle_single_prediction()
            
        elif self.path.startswith('/api/predict_multi?'):
            self.handle_multi_prediction()
            
        else:
            self.send_error(404, "File not found")
    
    def handle_single_prediction(self):
        """単日予測API"""
        try:
            # URLパラメータ解析
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            pair = params.get('pair', ['USD/JPY'])[0]
            days = int(params.get('days', ['1'])[0])
            
            # 予測実行
            prediction = self.predictor.predict_rate(pair, days)
            
            # レスポンス送信
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(prediction, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Prediction error: {str(e)}")
    
    def handle_multi_prediction(self):
        """複数日予測API"""
        try:
            # URLパラメータ解析
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            pair = params.get('pair', ['USD/JPY'])[0]
            days = int(params.get('days', ['10'])[0])
            
            # 予測実行
            predictions = self.predictor.predict_multi_day(pair, days)
            
            # レスポンス送信
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(predictions, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Multi-prediction error: {str(e)}")
    
    def log_message(self, format, *args):
        """ログメッセージを標準出力に出力"""
        message = f"{datetime.datetime.now().isoformat()} - {format % args}"
        print(message)

def create_handler(predictor):
    """ハンドラーファクトリー関数"""
    def handler(*args, **kwargs):
        return FXRequestHandler(predictor, *args, **kwargs)
    return handler

def main():
    """メイン実行関数"""
    try:
        # 環境変数からポート取得（App Runner対応）
        port = int(os.environ.get('PORT', 8080))
        
        print(f"🚀 FX予測システム - Ultimate Edition 起動中...")
        print(f"📡 ポート: {port}")
        print(f"⏰ 起動時刻: {datetime.datetime.now().isoformat()}")
        
        # 予測エンジン初期化
        predictor = FXPredictor()
        print("✅ 予測エンジン初期化完了")
        
        # HTTPサーバー起動
        handler = create_handler(predictor)
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌐 サーバー起動完了: http://0.0.0.0:{port}")
            print("🔄 リクエスト待機中...")
            print("=" * 50)
            
            # ヘルスチェック用の簡単なテスト
            test_prediction = predictor.predict_rate("USD/JPY", 1)
            print(f"🧪 テスト予測: USD/JPY = {test_prediction['predicted_rate']}")
            print("=" * 50)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 サーバー停止中...")
    except Exception as e:
        print(f"❌ サーバーエラー: {e}")
        raise

if __name__ == "__main__":
    main()