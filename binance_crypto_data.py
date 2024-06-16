import json
import sqlite3
import time
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
from binance.client import Client
from plotly.subplots import make_subplots
from ta.momentum import rsi, stochrsi, stochrsi_d, stochrsi_k
from ta.trend import (
    ema_indicator,
    ichimoku_a,
    ichimoku_b,
    ichimoku_base_line,
    macd,
    macd_signal,
    sma_indicator,
)
from ta.volatility import average_true_range, bollinger_hband, bollinger_lband


def db():
    """
    Database connection
    """
    conn = sqlite3.connect("database.db")
    return conn


def get_binance_client():
    """
    Initialize binance connection
    """
    api_info = open("config.json", "r", encoding="utf-8")
    api_info = json.load(api_info)
    api_key = api_info["API_KEY"]
    api_secret = api_info["SECRET_KEY"]
    client = Client(api_key, api_secret)
    return client


def get_available_crypto_symbols(client):
    """
    Get available symbols from binance
    """
    crypto_info = client.get_exchange_info()
    symbols = [
        item["symbol"]
        for item in crypto_info["symbols"]
        if item["symbol"].endswith("USDT")
    ]
    return symbols


def binance_get_historical_klines(symbol, interval, lookback, client, query_time_ms):
    """
    This function gets historical binance crypto data and returns pandas dataframe.
    """
    df = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback))
    df = df.iloc[:, :5]
    df.columns = ["open_time", "open", "high", "low", "close"]

    df["open_time_ms"] = df["open_time"]
    df["query_time_ms"] = query_time_ms

    # Fix datatypes
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.set_index("open_time")

    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    return df


def binance_get_multiple_historical_klines(
    symbols, interval, lookback, client, query_time_ms, selected_param
):
    """
    This function uses binance_get_historical_klines function to
    create a dataframe that contains given symbols historical data.
    """
    df_multiple = pd.DataFrame()
    for symbol in symbols:
        df = binance_get_historical_klines(
            symbol, interval, lookback, client, query_time_ms
        )
        df = df[["open_time", selected_param]].rename(columns={selected_param: symbol})
        df_multiple = pd.concat([df_multiple, df.set_index("open_time")], axis=1)
    df_multiple["query_time_ms"] = query_time_ms
    return df_multiple


def add_indicators(df):
    """
    This function adds some preselected indicators with their corresponding parameters
    """
    # SMA (Simple Moving Average)
    df["sma_200"] = sma_indicator(df["close"], window=200)
    df["sma_100"] = sma_indicator(df["close"], window=100)

    # EMA (Exponential Moving Average)
    df["ema_200"] = ema_indicator(df["close"], window=200)
    df["ema_100"] = ema_indicator(df["close"], window=100)

    # DEMA (Double Exponential Moving Average)
    df["dema_200"] = df["ema_200"] * 2 - ema_indicator(df["ema_200"], window=200)
    df["dema_100"] = df["ema_100"] * 2 - ema_indicator(df["ema_100"], window=100)

    # ATR (Average True Range)
    df["atr"] = average_true_range(df["high"], df["low"], df["close"], window=14)

    # Super Trend
    multiplier = 3
    df["basic_uband"] = ((df["high"] + df["low"]) / 2) + (multiplier * df["atr"])
    df["basic_lband"] = ((df["high"] + df["low"]) / 2) - (multiplier * df["atr"])

    # Ichimoku
    df["ichimoku_a"] = ichimoku_a(df["high"], df["low"], window1=9, window2=26)
    df["ichimoku_b"] = ichimoku_b(df["high"], df["low"], window2=26, window3=52)
    df["ichimoku_base_line"] = ichimoku_base_line(
        df["high"], df["low"], window1=9, window2=26
    )

    # Bollinger
    df["bollinger_hband"] = bollinger_hband(df["close"], window=30, window_dev=2)
    df["bollinger_lband"] = bollinger_lband(df["close"], window=30, window_dev=2)
    df["bollinger_mband"] = (df["bollinger_hband"] + df["bollinger_lband"]) / 2

    # MACD (Moving Average Convergence Divergence)
    df["macd"] = macd(df["close"], window_slow=26, window_fast=12)
    df["macd_signal"] = macd_signal(
        df["close"], window_slow=26, window_fast=12, window_sign=9
    )

    # RSI (Relative Strength Index)
    df["rsi"] = rsi(df["close"], window=14)
    df["stochrsi"] = stochrsi(df["close"], window=14, smooth1=3, smooth2=3)
    df["stochrsi_d"] = stochrsi_d(df["close"], window=14, smooth1=3, smooth2=3)
    df["stochrsi_k"] = stochrsi_k(df["close"], window=14, smooth1=3, smooth2=3)

    # Supertrend
    atr_multiplier = 3
    df["hl2"] = (df["high"] + df["low"]) / 2
    df["upperband"] = df["hl2"] + (atr_multiplier * df["atr"])
    df["lowerband"] = df["hl2"] - (atr_multiplier * df["atr"])
    df["in_uptrend"] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df["close"][current] > df["upperband"][previous]:
            df["in_uptrend"][current] = True
        elif df["close"][current] < df["lowerband"][previous]:
            df["in_uptrend"][current] = False
        else:
            df["in_uptrend"][current] = df["in_uptrend"][previous]

            if (
                df["in_uptrend"][current]
                and df["lowerband"][current] < df["lowerband"][previous]
            ):
                df["lowerband"][current] = df["lowerband"][previous]

            if (
                not df["in_uptrend"][current]
                and df["upperband"][current] > df["upperband"][previous]
            ):
                df["upperband"][current] = df["upperband"][previous]

    return df


def add_supertrend_indicator(
    df, atr_window=14, atr_multiplier=3, supertrend_multiplier=3
):
    """
    This function adds calculated supertrend indicator with its dependencies.
    Source: https://www.youtube.com/watch?v=21tLM3XrU9I
    """
    # ATR (Average True Range)
    df["atr"] = average_true_range(
        df["high"], df["low"], df["close"], window=atr_window
    )

    # Super Trend
    df["basic_uband"] = ((df["high"] + df["low"]) / 2) + (
        supertrend_multiplier * df["atr"]
    )
    df["basic_lband"] = ((df["high"] + df["low"]) / 2) - (
        supertrend_multiplier * df["atr"]
    )

    # Supertrend
    df["hl2"] = (df["high"] + df["low"]) / 2
    df["upperband"] = df["hl2"] + (atr_multiplier * df["atr"])
    df["lowerband"] = df["hl2"] - (atr_multiplier * df["atr"])
    df["in_uptrend"] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df["close"][current] > df["upperband"][previous]:
            df["in_uptrend"][current] = True
        elif df["close"][current] < df["lowerband"][previous]:
            df["in_uptrend"][current] = False
        else:
            df["in_uptrend"][current] = df["in_uptrend"][previous]

            if (
                df["in_uptrend"][current]
                and df["lowerband"][current] < df["lowerband"][previous]
            ):
                df["lowerband"][current] = df["lowerband"][previous]

            if (
                not df["in_uptrend"][current]
                and df["upperband"][current] > df["upperband"][previous]
            ):
                df["upperband"][current] = df["upperband"][previous]

    return df


def strategy_st_momentum_tsl(df, entry=0.005, dist=0.95):
    """
    This function is an example of given link's trading strategy
    Source: https://www.youtube.com/watch?v=ntGrOburPdQ
    """
    # Source
    # https://www.youtube.com/watch?v=ntGrOburPdQ
    df["price"] = df["open"].shift(-1)
    df["ret"] = df["close"].pct_change()
    df = df.dropna()

    profits = []
    in_position = False

    for index, row in df.reset_index().iterrows():
        if not in_position & row.loc["ret"] > entry:
            buy_price = row.loc["price"]
            in_position = True
            trailing_stop = buy_price * dist
        if in_position:
            if row.loc["close"] * dist >= trailing_stop:
                trailing_stop = row.loc["close"] * dist
            if row.loc["close"] <= trailing_stop:
                sell_price = row.loc["price"]
                profit = (sell_price - buy_price) / buy_price - 0.0015
                profits.append(profit)
                in_position = False
    return profits


def check_table_exist(conn, symbol):
    """
    Check if given symbol is exists as table in sqlite database.
    """
    cursor = conn.cursor()
    cursor.execute(
        f"""SELECT name FROM sqlite_master WHERE type="table" AND name="{symbol}";"""
    )
    rows = cursor.fetchall()
    if len(rows) > 0:
        return 1
    return 0


def update_db_data(df, conn, query_time_ms, symbol):
    """
    Updates table data
    """
    df_ = pd.read_sql(f"SELECT * FROM {symbol}", conn)
    df_["open_time"] = pd.to_datetime(df_["open_time"])
    df = pd.concat([df_, df], axis=0)
    df = df.sort_values(by=["query_time_ms", "open_time_ms"])
    df = df.drop_duplicates(subset=["open_time"], keep="last")
    df["query_time_ms"] = query_time_ms
    df = df.set_index("open_time")
    df.to_sql(symbol, conn, index=True, if_exists="replace")


def plotly_graph_with_indicators(df):
    """
    A plotly obejct to plot crypto data with selected indicators
    """
    df_plot = df.copy()
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Candlestick(
            x=df_plot.index,
            open=df_plot["open"],
            high=df_plot["high"],
            low=df_plot["low"],
            close=df_plot["low"],
            name="candle",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df_plot.index,
            y=df_plot["bollinger_hband"],
            mode="lines",
            name="bollinger_hband",
            line={"color": "black"},
            opacity=0.7,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot.index,
            y=df_plot["bollinger_mband"],
            mode="lines",
            name="bollinger_lband",
            line={"color": "orange"},
            opacity=0.7,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot.index,
            y=df_plot["bollinger_lband"],
            mode="lines",
            name="bollinger_lband",
            line={"color": "black"},
            opacity=0.7,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df_plot.index,
            y=df_plot["rsi"],
            mode="lines",
            name="rsi",
            line={"color": "blue"},
            opacity=0.3,
        ),
        secondary_y=True,
    )
    fig.add_hline(
        y=70,
        line_width=3,
        line_color="blue",
        name="rsi 70",
        opacity=0.2,
        secondary_y=True,
    )
    fig.add_hline(
        y=30,
        line_width=3,
        line_color="blue",
        name="rsi 30",
        opacity=0.2,
        secondary_y=True,
    )

    fig.update_layout(
        height=800,
    )

    return fig


def main():
    # Time Parameters
    query_time = datetime.today()
    query_time_ms = query_time.timestamp() * 1000
    # Binance API
    client = get_binance_client()
    symbols = get_available_crypto_symbols(client)
    # SQLite Database
    conn = db()

    for symbol in symbols:
        print(f"Get {symbol}")
        check_table = check_table_exist(conn, symbol)

        if check_table == 1:
            lookback = str(date.today() - timedelta(days=15))

            try:
                df = binance_get_historical_klines(
                    symbol, "15m", lookback, client, query_time_ms
                )
                update_db_data(df, conn, query_time_ms, symbol)
                print(f"{symbol} updated in db")
                time.sleep(1)
            except Exception as e:
                print(e)

        else:
            lookback = str(date.today() - timedelta(days=400))

            try:
                df = binance_get_historical_klines(
                    symbol, "15m", lookback, client, query_time_ms
                )
                df.to_sql(symbol, conn, index=True, if_exists="replace")
                print(f"{symbol} saved to db")
                time.sleep(1)
            except Exception as e:
                print(e)


if __name__ == "__main__":
    main()
