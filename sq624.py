import numpy as np
import pandas as pd
from sklearn import preprocessing
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import time
def sse_cal(data, label):
    label_num = len(set(label.tolist()))
    print(set(label))
    center_mean = [data[label == i].mean() for i in range(label_num)]
    sse = 0
    for point, label in zip(data, label):
        # print(point)
        # print(center_mean[label])
        sse += np.square(point - center_mean[label]).sum()
        print(sse)
    return sse

def check_csm_kmeans(data):
    # 直接进行K-means聚类
    csm_arr = []
    for k in range(2, 30):
        kmeans = KMeans(n_clusters=k, random_state=0)
        kmeans.fit(data)
        s = silhouette_score(data, kmeans.labels_)
        csm_arr.append(s)
    plt.figure()
    plt.title('SeoulBikeData')
    plt.xlabel('n cluster')
    plt.ylabel('CSM')
    plt.plot(np.array(list(range(2, 30))), csm_arr, '-bx')
    plt.show()

def check_csm_dbscan(data):
    csm_arr = []
    eps = [0.5, 1, 1.5, 2, 2.5, 3, 3.5]
    for k in eps:
        dbscan = DBSCAN(eps=k)
        dbscan.fit(data)
        s = silhouette_score(data, dbscan.labels_)
        csm_arr.append(s)
    plt.figure()
    plt.xlabel('eps')
    plt.ylabel('CSM')
    plt.plot(np.array(eps), csm_arr, '-bx')
    plt.show()

def check_csm_agg(data):
    csm_arr = []
    K_arr = range(2, 30)
    for k in K_arr:
        dbscan = AgglomerativeClustering(n_clusters=k)
        dbscan.fit(data)
        s = silhouette_score(data, dbscan.labels_)
        csm_arr.append(s)
    plt.figure()
    plt.xlabel('n cluster')
    plt.ylabel('CSM')
    plt.plot(np.array(list(K_arr)), csm_arr, '-bx')
    plt.show()

def get_metrics(data, method):
    t_b = time.time()
    if method == "k-means":
        kmeans = KMeans(n_clusters=10, random_state=0)
        kmeans.fit(data)
        t_e = time.time()
        time_taken = t_e - t_b
        s_score = silhouette_score(data, kmeans.labels_)
        sse = sse_cal(data, kmeans.labels_)
    elif method == "dbscan":
        dbscan = DBSCAN(eps=2)
        dbscan.fit(data)
        t_e = time.time()
        time_taken = t_e - t_b
        s_score = silhouette_score(data, dbscan.labels_)
        sse = sse_cal(data, dbscan.labels_)
    else:
        # Agglomerative algorithm
        agg = AgglomerativeClustering(n_clusters=2)
        agg.fit(data)
        t_e = time.time()
        time_taken = t_e - t_b
        s_score = silhouette_score(data, agg.labels_)
        sse = sse_cal(data, agg.labels_)
    return time_taken, sse, s_score


def main_procees(data_name, path):
    if(data_name=='1'):
        # Data1: SeoulBikeData
        data = pd.read_csv(path, index_col=0)
        # 1.确认数据是否有缺省值
        # 去掉date, holiday还有functional day
        data = data.iloc[:, list(range(1, 11))]
        # 对离散特征进行独热编码
        data = pd.get_dummies(data, columns=['Hour', 'Seasons'])

        # 对数据进行归一化(z_score)
        data = data.to_numpy()
        data = preprocessing.StandardScaler().fit_transform(data)

        # 利用PCA对数据进行降维操作

        data = PCA(n_components=5).fit_transform(data)
        # check_csm_kmeans(data)
        # check_csm_dbscan(data)
        print("(time_taken, sse, silhouette score) : {}".format(get_metrics(data, "dbscan")))
    if(data_name=='2'):
        # Data2: Facebook_Live_sellers
        data = pd.read_csv(path, index_col=0)
        data = data.iloc[:, [0]+list(range(2, 10))]

        # 保留为photo和video, link的type
        idx = data['status_type'].isin(['photo', 'video', 'link']).tolist()
        data = data.iloc[idx, :]
        data = pd.get_dummies(data, columns=['status_type'])

        # 对数据进行归一化(z_score)
        data = data.to_numpy()
        data = preprocessing.StandardScaler().fit_transform(data)

        data = PCA(n_components=5).fit_transform(data)

        check_csm_kmeans(data)
        print("(time_taken, sse, silhouette score) : {}".format(get_metrics(data, "k-means")))


    if(data_name=='3'):
        # Data2: Facebook_Live_sellers
        data = pd.read_csv(path, header=None)
        data = data.iloc[:, 1:]

        # 对数据进行清洗，将?转为0
        data = data.apply(lambda x : x.replace('?', 0))

        # 对数据进行归一化(z_score)
        data = data.to_numpy()
        data = preprocessing.StandardScaler().fit_transform(data)
        data = PCA(n_components=5).fit_transform(data)

        check_csm_kmeans(data)
        print("(time_taken, sse, silhouette score) : {}".format(get_metrics(data, "k-means")))


main_procees("1", 'C:\\Users\\Lenovo\\Desktop\\sq627\\SeoulBikeData.csv')
