# binance_trading_dashboard
A Streamlit dashboard that uses Binance API data

## Run Dashboard
Clone the repo
```console
foo@bar:~$ git clone https://github.com/zereaykut/binance_trading_dashboard
foo@bar:~$ cd binance_trading_dashboard
```

Create python environment
```console
foo@bar:~$ python -m venv env
```

Activate environment in Mac/Linux 
```console
foo@bar:~$ source env/bin/activate
```

Activate environment in Windows 
```console
foo@bar:~$ env\Scripts\activate
```

Install required packages
```console
foo@bar:~$ pip install -r requirements.txt
```

Add your binance info to config.json
```json
{
  "API_KEY": "your_binance_api_key",
  "SECRET_KEY": "your_binance_api_secret_key"
}
```

Get dashboard data
```console
foo@bar:~$ python binance_crypto_data.py
```

Run dashboard
```console
foo@bar:~$ streamlit run app.py
```
