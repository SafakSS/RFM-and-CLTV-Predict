from sqlalchemy import create_engine
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
from lifetimes.plotting import plot_period_transactions
from sklearn.preprocessing import MinMaxScaler

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 500)
pd.set_option('display.float_format', lambda x: '%.2f' % x)

def outlier_thresholds(dataframe, variable):
    quartile1 = dataframe[variable].quantile(0.01)
    quartile3 = dataframe[variable].quantile(0.99)
    interquantile_range = quartile3 - quartile1
    up_limit = quartile3 + 1.5 * interquantile_range
    low_limit = quartile1 - 1.5 * interquantile_range
    return low_limit, up_limit

def replace_with_thresholds(dataframe, variable):
    low_limit, up_limit = outlier_thresholds(dataframe, variable)
    dataframe.loc[(dataframe[variable] < low_limit), variable] = low_limit
    dataframe.loc[(dataframe[variable] > up_limit), variable] = up_limit

df_ = pd.read_excel("datasets/online_retail_II.xlsx", sheet_name="Year 2010-2011")


def create_cltv_p(dataframe, month=False, expected=False, diff=False, month1=False, month2=False, segment=False, to_sql=False, name_=False):
        # 1. Veri Ön İşleme
    dataframe.dropna(inplace=True)
    dataframe = dataframe[~dataframe["Invoice"].str.contains("C", na=False)]
    dataframe = dataframe[dataframe["Quantity"] > 0]
    dataframe = dataframe[dataframe["Price"] > 0]
    dataframe = dataframe[dataframe["Country"] == "United Kingdom"]
    replace_with_thresholds(dataframe, "Quantity")
    replace_with_thresholds(dataframe, "Price")
    dataframe["TotalPrice"] = dataframe["Quantity"] * dataframe["Price"]
    today_date = dt.datetime(2011, 12, 11)

    cltv_df = dataframe.groupby('Customer ID').agg(
        {'InvoiceDate': [lambda InvoiceDate: (InvoiceDate.max() - InvoiceDate.min()).days,
                        lambda InvoiceDate: (today_date - InvoiceDate.min()).days],
        'Invoice': lambda Invoice: Invoice.nunique(),
        'TotalPrice': lambda TotalPrice: TotalPrice.sum()})

    cltv_df.columns = cltv_df.columns.droplevel(0)
    cltv_df.columns = ['recency', 'T', 'frequency', 'monetary']
    cltv_df["monetary"] = cltv_df["monetary"] / cltv_df["frequency"]
    cltv_df = cltv_df[(cltv_df['frequency'] > 1)]
    cltv_df["recency"] = cltv_df["recency"] / 7
    cltv_df["T"] = cltv_df["T"] / 7

    # 2. BG-NBD Modelinin Kurulması
    bgf = BetaGeoFitter(penalizer_coef=0.001)
    bgf.fit(cltv_df['frequency'],
            cltv_df['recency'],
            cltv_df['T'])


    # 3. GAMMA-GAMMA Modelinin Kurulması
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(cltv_df['frequency'], cltv_df['monetary'])

    if expected:
        cltv_df["expected_purc_1_week"] = bgf.predict(1,
                                                        cltv_df['frequency'],
                                                        cltv_df['recency'],
                                                        cltv_df['T'])

        cltv_df["expected_purc_1_month"] = bgf.predict(4,
                                                        cltv_df['frequency'],
                                                        cltv_df['recency'],
                                                        cltv_df['T'])

        cltv_df["expected_average_profit"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],
                                                                                         cltv_df['monetary'])


    # 4. BG-NBD ve GG modeli ile CLTV'nin hesaplanması.
    cltv = ggf.customer_lifetime_value(bgf,
                                        cltv_df['frequency'],
                                        cltv_df['recency'],
                                        cltv_df['T'],
                                        cltv_df['monetary'],
                                        time=month,  # ? aylık
                                        freq="W",  # T'nin frekans bilgisi.
                                        discount_rate=0.01)

    cltv = cltv.reset_index()
    cltv_final = cltv_df.merge(cltv, on="Customer ID", how="left")
    cltv_final = cltv_final.sort_values(by="clv", ascending=False)  # sortladık
    cltv_final.head()

    # yorumlayamadığımız için standartlaştırıoruz.
    scaler = MinMaxScaler(feature_range=(0, 100))
    scaler.fit(cltv_final[["clv"]])
    cltv_final["scaled_clv"] = scaler.transform(cltv_final[["clv"]])
    cltv_final.sort_values(by="scaled_clv", ascending=False).head(10)

    if diff:
        cltv_1 = ggf.customer_lifetime_value(bgf,
                                             cltv_df['frequency'],
                                             cltv_df['recency'],
                                             cltv_df['T'],
                                             cltv_df['monetary'],
                                             time=month1,  # ? aylık
                                             freq="W",  # T'nin frekans bilgisi.
                                             discount_rate=0.01)
        cltv_1 = cltv_1.reset_index()
        cltv_1 = cltv_1.sort_values(by="clv", ascending=False).head(10)

        cltv_12 = ggf.customer_lifetime_value(bgf,
                                              cltv_df['frequency'],
                                              cltv_df['recency'],
                                              cltv_df['T'],
                                              cltv_df['monetary'],
                                              time=month2,  # ? aylık
                                              freq="W",  # T'nin frekans bilgisi.
                                              discount_rate=0.01)
        cltv_12 = cltv_12.reset_index()
        cltv_12 = cltv_12.sort_values(by="clv", ascending=False).head(10)

        cltv_final = cltv_1.merge(cltv_12, on="Customer ID", how="left")

    if segment:
        cltv_final["segment"] = pd.qcut(cltv_final["scaled_clv"], 4, labels=["D", "C", "B", "A"])
        # Segmentleri betimleyelim
        # cltv_final.groupby("segment").agg({"count", "mean", "sum"})
        # B segmentini potansiyel sadık müşteri olmaya yatkın gibi görebiliriz.
        # Alışveriş frekanslarını biraz daha arttırısak onları da A segmentine dahil edebiliriz.

        # D segmentinin recency değeri diğerlerine göre daha iyi sanki satın alma eğilimindeler.
        # Ama bir itici kuvvet bekliyorlar. Yani bunlara daha fazla kampanya yapabiliriz.


    if to_sql:
        creds = {'user': '',
                 'passwd': '',
                 'host': '',
                 'port': ,
                 'db': ''}
        # MySQL conection string.
        connstr = 'mysql+mysqlconnector://{user}:{passwd}@{host}:{port}/{db}'
        # sqlalchemy engine for MySQL connection.
        conn = create_engine(connstr.format(**creds))
        pd.read_sql_query("show tables", conn)
        cltv_final.to_sql(name=name_, con=conn, if_exists='replace', index=False)

    return cltv_final

df = df_.copy()
ctlv_prediction = create_cltv_p(df, month=6)


