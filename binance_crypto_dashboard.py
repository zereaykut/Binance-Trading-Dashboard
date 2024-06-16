from datetime import date, timedelta

import pandas as pd
import streamlit as st

from binance_crypto_data import add_indicators, db, plotly_graph_with_indicators


def main():
    st.set_page_config(layout="wide")
    col1, col2, col3 = st.columns(3)
    start_date = col1.date_input("start date", date.today() - timedelta(days=7))
    start_date = str(start_date)
    end_date = col2.date_input("end date", date.today())
    end_date = str(end_date)
    conn = db()
    symbols = pd.read_sql(
        """SELECT name FROM sqlite_schema WHERE type ='table' AND name NOT LIKE 'sqlite_%';""",
        conn,
    )
    symbol = col3.selectbox("Symbol", symbols)

    df = pd.read_sql(f"SELECT * FROM {symbol}", conn)
    conn.close()

    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.drop(columns=["query_time_ms", "open_time_ms"])
    df = df.set_index("open_time")
    df = df.sort_index()
    df = df.iloc[-2000:]
    df = add_indicators(df)
    # df = df.loc[start_date:end_date]
    st.dataframe(df)

    fig = plotly_graph_with_indicators(df)
    st.plotly_chart(fig, theme="streamlit", use_container_width=True)


if __name__ == "__main__":
    main()
