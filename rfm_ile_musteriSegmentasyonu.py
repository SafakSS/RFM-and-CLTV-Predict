import datetime as dt
import pandas as pd
pd.set_option('display.max_columns', 10)
pd.set_option('display.max_rows', 10)
pd.set_option('display.float_format', lambda x: '%.2f' % x)

# 2009-2010 yılı içerisindeki veriler
# Görev 1 : Verisetini okuyunuz ve kopyasını oluştur.
df_ = pd.read_excel("datasets/online_retail_II.xlsx", sheet_name="Year 2010-2011")
df = df_.copy()

# 1.2 Veri setinin betimsel istatistiklerini inceleyiniz.
df.describe().T

# 1.3 Veri setinde eksik gözlem var mı? Varsa hangi değişkende kaçar tane?
df.isnull().sum()

# 1.4 Eksik gözlemleri veri setinden çıkarınız. Çıkarma işleminde inplace = True parametresini kullanınız.
df.dropna(inplace=True)
df.isnull().sum()

# 1.5 Eşsiz ürün sayısı kaçtır?
df["Description"].nunique()
# na değerleri dropladıktan sonra değerimiz değişti.

# 1.6 Hangi üründen kaçar tane vardır?
df["Description"].value_counts()

# 1.7 En çok sipariş edilen 5 ürünü çoktan aza doğru sıralayınız.
df.groupby("Description").agg({"Quantity": "count"}).sort_values(["Quantity"], ascending=False).head()

# 1.8 Faturalardaki 'C' iptal edilen işlemleri göstermektedir.
# İptal edilen faturaları veri setinden çıkarınız.
df = df[~df["Invoice"].str.contains("C", na=False)]
df = df[df["Price"] > 0]
df = df[df["Quantity"] > 0]

# 1.9 Fatura başına elde edilen toplam kazancı ifade eden 'ToplamPrice'
# adındaki bir değişken oluşturunuz.

df["TotalPrice"] = df["Quantity"] * df["Price"]


# Görev 2: RFM Metriklerinin Hesaplanması.
# Görev 2.1 - Recency, Frequency ve Monetary tanımlarını yapınız.
# Görev 2.2 - Müşteri özelinde Recency, Frequency ve Monetary metriklerini groupby, agg ve lambda ile hesaplayınız.
# Görev 2.3 - Hesapladığınız metrikleri rfm isimli bir değişkene atayınız.
df["InvoiceDate"].max()  # 2011-12-09
today_date = dt.datetime(2011, 12, 11)

rfm = df.groupby("Customer ID").agg({"InvoiceDate": lambda x: (today_date - x.max()).days,
                                    "Invoice": lambda x: x.nunique(),
                                    "TotalPrice": lambda x: x.sum()
                                    })

# Görev 2.5 - Oluşturduğunuz metriklerin isimlerini recency, frequency ve monetary olarak değiştiriniz.
rfm.columns = ['Recency', 'Frequency', 'Monetary']
rfm = rfm[rfm['Monetary'] > 0]


# Görev 3: RFM skorlarının oluşturulması ve tek bir değişkene  çevrilmesi
# - Recency, Frequency ve Monetary metriklerini qcut yardımı ile 1-5 arasında skorlara çeviriniz.
rfm["recency_score"] = pd.qcut(rfm['Recency'], 5, labels=[5, 4, 3, 2, 1])
rfm["frequency_score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
rfm["monetary_score"] = pd.qcut(rfm["Monetary"], 5, labels=[1, 2, 3, 4, 5])
rfm.head()


rfm["RFM_SCORE"] = rfm['recency_score'].astype(str) + rfm['frequency_score'].astype(str)
rfm.head()


# Görev 4: RFM skorlarının segment olarak tanımlanması
# - Oluşturulan RFM skorlarının daha açıklanabilir olması için segment tanımlamaları yapınız.
seg_map = {
        r'[1-2][1-2]': 'hibernating',
        r'[1-2][3-4]': 'at_risk',
        r'[1-2]5': 'cant_loose',
        r'3[1-2]': 'about_to_sleep',
        r'33': 'need_attention',
        r'[3-4][4-5]': 'loyal_customers',
        r'41': 'promising',
        r'51': 'new_customers',
        r'[4-5][2-3]': 'potential_loyalists',
        r'5[4-5]': 'champions'
    }

rfm['RFM_SCORE'] = rfm['RFM_SCORE'].replace(seg_map, regex=True)
rfm = rfm[["Recency", "Frequency", "Monetary", "RFM_SCORE"]]



# Görev 5: Yorum
rfm[["RFM_SCORE", "Recency", "Frequency", "Monetary"]].groupby("RFM_SCORE").agg(["mean", "count"])
new_df = pd.DataFrame()
new_df["new_customer_id"] = rfm[rfm["RFM_SCORE"] == "loyal_customers"].index
new_df.head()

new_df.to_csv("new_customers.csv")


# Aksiyon Zamanı
# Hibernating : Uyuyan Tayfa
# Bu grupta 1071 müşterimiz var. Bütün müşterilerimizin %24.6'sı.
# Ortalama 217 gündür alışveriş yapmıyorlar.
# Ortalama 1.10 kez alışveriş yapmışlar.
# Ortalama 488$ kazanmışız.
# Hibernating segmenti için kesinlikle bir aksiyon kararı almalıyız.
# Çünkü hibernating segmentimiz mevcut müşterilerimizin %24.6'sını temsil ediyor.
# Uyuyan bu segmentimizi uyandırmak için ise :
# Öncelikle bu segmentimizle tekrar iletişime geçmemiz lazım.
# Özel ilgi sunmalıyız ve markamızın değerini onların gözünde tekrar oluşturmalıyız.
# Kendimizi mailler, mesajlar vb. gibi yöntemlerle tekrar hatırlatmalıyız.
# Geçmiş aramalarına göre özel kampanyalar düzenleyebiliriz.

# Potential_loyalists : Sadık Olmaya Yatkın Tayfa
# Yani bunları sadık yapmalıyız.
# Bu grupta 484 müşterimiz var. Bütün müşterilerimizin yüzde 11'i.
# Ortalama 17 gündür alışveriş yapmıyorlar.
# Ortalama 2 kez alışveriş yapmışlar.
# Bu sınıf sadık olmaya yakın olduğu için şöyle bir şey denenebilir :
# Örneğin davet ettikleri kişiler, kişi başına toplamda 100$ harcama yaptıklarında.
# Davet eden sadık müşterimize 5$'lık kupon verebiliriz.
# Sanki onlara şirketimizde ortakmışız hissiyatı oluşturabilir.


# at_risk : kaybetme ihtimalimizin yüksek olduğu tayfa, riskli
# Bu grupta 593 müşterimiz var. Bütün müşterilerimizin yüzde 13'ü.
# Ortalama 153 gündür alışveriş yapmıyorlar.
# Ortalama 2.8 kez alışveriş yapmışlar.
# Yeniden bağlantı kurmal   arı için onlara kişiselleştirilmiş kampanyalar göndermeliyiz.
# Faydalı ürünler ve çokça indirimler sunarsak geri getirebiliriz bu tayfayı.

def create_rfm(dataframe):

    # VERIYI HAZIRLAMA
    dataframe.dropna(inplace=True)
    dataframe = dataframe[~dataframe["Invoice"].str.contains("C", na=False)]
    dataframe = dataframe[(dataframe['Quantity'] > 0)]
    dataframe = dataframe[(dataframe['Price'] > 0)]
    dataframe["TotalPrice"] = dataframe["Quantity"] * dataframe["Price"]

    # RFM METRIKLERININ HESAPLANMASI
    today_date = dt.datetime(2011, 12, 11)
    rfm = dataframe.groupby('Customer ID').agg({'InvoiceDate': lambda date: (today_date - date.max()).days,
                                                'Invoice': lambda num: num.nunique(),
                                                "TotalPrice": lambda price: price.sum()})
    rfm.columns = ['recency', 'frequency', "monetary"]
    rfm = rfm[(rfm['monetary'] > 0)]

    # RFM SKORLARININ HESAPLANMASI
    rfm["recency_score"] = pd.qcut(rfm['recency'], 5, labels=[5, 4, 3, 2, 1])
    rfm["frequency_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    rfm["monetary_score"] = pd.qcut(rfm['monetary'], 5, labels=[1, 2, 3, 4, 5])


    rfm["RFM_SCORE"] = (rfm['recency_score'].astype(str) +
                        rfm['frequency_score'].astype(str))


    # SEGMENTLERIN ISIMLENDIRILMESI
    seg_map = {
        r'[1-2][1-2]': 'hibernating',
        r'[1-2][3-4]': 'at_risk',
        r'[1-2]5': 'cant_loose',
        r'3[1-2]': 'about_to_sleep',
        r'33': 'need_attention',
        r'[3-4][4-5]': 'loyal_customers',
        r'41': 'promising',
        r'51': 'new_customers',
        r'[4-5][2-3]': 'potential_loyalists',
        r'5[4-5]': 'champions'
    }

    rfm['segment'] = rfm['RFM_SCORE'].replace(seg_map, regex=True)
    rfm = rfm[["recency", "frequency", "monetary", "segment"]]
    return rfm

df = df_.copy()
rfm_new = create_rfm(df)
rfm_new.head()





