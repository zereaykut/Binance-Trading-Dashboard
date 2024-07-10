# binance_trading_dashboard
A Streamlit dashboard that uses Binance API data

## Run Dashboard
Clone the repo
```shell
git clone https://github.com/zereaykut/binance_trading_dashboard
cd binance_trading_dashboard
```

Create python environment
```shell
python -m venv env
```

Activate environment in Mac/Linux 
```shell
source env/bin/activate
```

Activate environment in Windows 
```shell
.\env\Scripts\activate
```

Install required packages
```shell
pip install -r requirements.txt
```

Add your binance info to config.json
```json
{
  "API_KEY": "Binance API Key",
  "SECRET_KEY": "Binance API Secret Key"
}
```

Get dashboard data
```shell
python binance_crypto_data.py
```

Run dashboard
```shell
streamlit run binance_crypto_dashboard.py
```
