import math
import os.path
import random
import numpy as np
import copy
import sklearn
from sklearn.neighbors import kneighbors_graph
import torch
from torch_geometric.data import Data as geoData
import networkx as nx
from sklearn.preprocessing import OneHotEncoder
import matplotlib.pyplot as plt
import pandas as pd
import umap
from sklearn.metrics import silhouette_score, adjusted_rand_score, accuracy_score, f1_score
import seaborn as sns
import wandb
import scipy.spatial as spt
from random import sample
from sklearn.decomposition import PCA
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest
hue = []

def mean_norm(data):
    '''
    scGCN中的标准化处理，对表达矩阵的每一个表达量做一个平均加权
    :param data: 矩阵 (cells * genes)
    :return: 返回归一化的矩阵
    '''
    row_sum = np.sum(data, axis=1)
    mean_transcript = np.mean(row_sum)
    print("细胞平均表达量是 {:.3f}".format(mean_transcript))
    # 防止出现除0的问题
    row_sum[np.where(row_sum == 0)] = 1

    # scale_factor = 1e4
    # data_norm = np.log1p((data / row_sum.reshape(-1 ,1))*scale_factor)
    data_norm = (data / row_sum.reshape(-1, 1)) * mean_transcript


    return data_norm


def z_score_scale(data):
    '''
    利用z-score方法做一个batch normalization
    :param data: 矩阵，（样本 * 特征）, 二维数组
    :return:
    '''
    means = np.mean(data, axis=0)
    standard = np.std(data, axis=0)

    return (data - means) / standard


def mask_data(data, masked_prob):
    '''
    :param data: 表达矩阵 (cells * genes)
    :param masked_prob: mask概率
    :return:
        1. X: mask后的表达矩阵，
        2. index_pair: 矩阵中不为0的索引，[(行),(列)],
        3. masking_idx: 随机选择index_pair中行列的下标
        X[index_pair[0][masking_idx], index_pair[1][masking_idx]] 就是指被masked的数据
    '''
    index_pair = np.where(data != 0)
    seed = 1
    np.random.seed(seed)
    idx = np.random.choice(index_pair[0].shape[0], int(index_pair[0].shape[0] * masked_prob), replace=False)
    # masking_idx = [idx, idx]
    # to retrieve the position of the masked: data_train[index_pair_train[0][masking_idx], index_pair[1][masking_idx]]
    X = copy.deepcopy(data)
    mask_idx = [index_pair[0][idx], index_pair[1][idx]]
    X[mask_idx[0], mask_idx[1]] = 0

    return X, mask_idx

def mask_column(data, masked_prob, cols):
    tmp_data = data[:, cols]
    index_pair = np.where(tmp_data != 0)
    seed = 1
    random.seed(seed)   #为了复现
    idx = random.sample(range(index_pair[0].shape[0]), int(index_pair[0].shape[0] * masked_prob))   #无重复采样
    mask_rows = index_pair[0][idx]
    # cols 代表原来数据的列下标
    cols = np.array(cols)
    # print(index_pair[1][idx])
    mask_cols = cols[index_pair[1][idx]]
    mask_idx = [mask_rows, mask_cols]
    # to retrieve the position of the masked: data_train[index_pair_train[0][masking_idx], index_pair[1][masking_idx]]
    X = copy.deepcopy(data)
    # print(index_pair[0])
    X[mask_idx[0], mask_idx[1]] = 0
    return X, mask_idx

def construct_graph_with_knn(data, k=2):
    A = kneighbors_graph(data, k, mode='connectivity', include_self=False) # 拿到Similarity矩阵
    G = nx.from_numpy_matrix(A.todense())
    edges = []
    # 把有向图转为无向图
    for (u, v) in G.edges():
        edges.append([u, v])
        edges.append([v, u])
    edges = np.array(edges).T
    edges = torch.tensor(edges, dtype=torch.long)
    feat = torch.tensor(data, dtype=torch.float)
    # 将节点信息和边的信息放入特定类中
    g_data = geoData(x=feat, edge_index=edges)
    return g_data

def get_similarity_matrix(data, k=2):
    A = kneighbors_graph(data, k, mode='connectivity', include_self=False)  # 拿到Similarity矩阵
    return A.todense()


def construct_graph(data, similarity_mat, k):
    '''
    :param data: 表达矩阵 (被mask的矩阵)
    :param similarity_mat: 邻接矩阵 (ndarray)
    :return: 返回Cell similarity的图结构
    '''

    # 要对similarity_mat取前K个最大的weight作为neighbors
    k_idxs = []
    # 将对角线部分全部设为0, 避免自己做自己的邻居
    similarity_mat[np.diag_indices_from(similarity_mat)] = 0
    for i in range(similarity_mat.shape[0]):
        top_k_idx = similarity_mat[i].argsort()[::-1][0:k]
        k_idxs.append(top_k_idx)

    similarity_mat = np.zeros(shape=similarity_mat.shape)
    # 原来这一步真的很离谱，这里构造图的时候一直都错了，下面的for循环才是对的
    for i in range(similarity_mat.shape[0]):
        similarity_mat[i, k_idxs[i]] = 1

    similarity_mat = similarity_mat.astype(np.int64)
    graph = nx.from_numpy_matrix(np.matrix(similarity_mat))


    edges = []
    # 把有向图转为无向图
    for (u, v) in graph.edges():
        edges.append([u, v])
        edges.append([v, u])


    edges = np.array(edges).T
    edges = torch.tensor(edges, dtype=torch.long)
    feat = torch.tensor(data, dtype=torch.float)
    # 将节点信息和边的信息放入特定类中
    g_data = geoData(x=feat, edge_index=edges)
    return g_data


def read_data_label_h5(path, key):
    print('Reading data...')
    data_path = os.path.join(path, 'data.h5')

    data_df = pd.read_hdf(data_path, key + '/data')
    data = data_df.to_numpy()

    label_df = pd.read_hdf(data_path, key + '/label')
    # print(label_df['type'].value_counts())

    label = label_df.to_numpy().reshape(-1)

    print('表达矩阵的shape为 :{}'.format(data.shape))  # (samples,genes)
    print('label的shape为 : {}'.format(label.shape))
    return data, label


# def read_data_label(data_path, label_path):
#     '''
#     读取数据, 数据格式需要满足一定格式
#     表达矩阵第一列是cell id, 第一行是名称
#     label矩阵只有一列
#
#
#     :param Single cell的表达矩阵Path
#     :param 标签Path
#     :return: 返回Numpy类型数组（表达矩阵，标签）
#     '''
#
#     print('Reading data...')
#     data_df = pd.read_csv(data_path, index_col=0)
#     data = data_df.to_numpy()
#
#     label_df = pd.read_csv(label_path)
#     label = label_df.to_numpy().reshape(-1)
#     print('表达矩阵的shape为 :{}'.format(data.shape))  # (samples,genes)
#     print('label的shape为 : {}'.format(label.shape))
#     return data, label


# def read_similarity_mat(path):
#     mat_df = pd.read_csv(path, index_col=0)
#     similarity_mat = mat_df.to_numpy()
#     return similarity_mat.astype(np.float64)


def read_similarity_mat_h5(path, key):

    # print("reading graph...")
    data_path = os.path.join(path, 'data.h5')
    mat_df = pd.read_hdf(data_path, key)

    # print(mat_df.isnull().any())
    #
    # print(np.isnan(mat_df).any())
    # print(np.isinf(mat_df).all())
    #
    # print(np.isfinite(mat_df).all())
    similarity_mat = mat_df.to_numpy()
    # print("Finish")
    return similarity_mat.astype(np.float64)

def sel_feature(data1, data2, label1, nf=3000):
    # 先去掉表达量为0的基因, 然后再做交集, 这里暂时不打算取HVG
    # sum1 = np.sum(data1, axis=0)
    # idx1 = set(np.where(sum1!=0)[0])
    # sum2 = np.sum(data2, axis=0)
    # idx2 = set(np.where(sum2!=0)[0])
    # idx = list(idx1 & idx2) #交集
    # data1 = data1[:, idx]
    # data2 = data2[:, idx]
    # print("After gene selction , ref data shape {:}, query data shape {:}".format(data1.shape, data2.shape))
    # return data1, data2

    sel_model = SelectKBest(k=nf)   #default score function is f_classif

    sel_model.fit(data1, label1)
    idx = sel_model.get_support(indices=True)

    # sel_model = SelectKBest(k=nf)
    # sel_model.fit(data2, label2)
    # idx2 = sel_model.get_support(indices=True)

    # idx = list(set(idx1) & set(idx2))
    data1 = data1[:, idx]
    data2 = data2[:, idx]
    print("After gene selction , ref data shape {:}, query data shape {:}".format(data1.shape, data2.shape))

    return data1, data2

def mnnCorrect(data1, data2):
    # 消除Batch effects影响
    pass

def pre_process(data1, data2, label1, nf=2000):
    # 先选择合适的feature
    data1, data2 = sel_feature(data1, data2, label1, nf=nf)
    # scaler = StandardScaler()
    data1 = mean_norm(data1)
    data2 = mean_norm(data2)
    # data1 = scaler.fit_transform(data1)
    # data2 = scaler.transform(data2)
    # 再做ScaleData: z_score
    # data1, data2 = z_score_scale(data1), z_score_scale(data2)
    return data1, data2

def cpm_classify(lsd1, lsd2, label):
    """In most cases, this method is used to predict the highest accuracy.
    :param lsd1: train set's latent space data
    :param lsd2: test set's latent space data
    :param label: label of train set
    :return: Predicted label
    """
    F_h_h = np.dot(lsd2, np.transpose(lsd1))
    label = label.reshape(len(label), 1)
    enc = OneHotEncoder()
    a = enc.fit_transform(label)
    # print(a)
    label_onehot = a.toarray()
    label_num = np.sum(label_onehot, axis=0)
    F_h_h_sum = np.dot(F_h_h, label_onehot)
    F_h_h_mean = F_h_h_sum / label_num
    label_pre = np.argmax(F_h_h_mean, axis=1)
    return label_pre


def runUMAP(data):
    umap_model = umap.UMAP(random_state=0)
    data_2d = umap_model.fit_transform(data)
    return data_2d


def runPCA(data):
    pca = PCA(n_components=32)
    return pca.fit_transform(data)


def show_cluster(data, label, title, save_path):
    '''
    可视化聚类的函数
    :param data: 降维之后的数据(2d)
    :param label: 样本的标签
    :param title: 可视化窗口的titleplt.scatter
    '''
    save_path = os.path.join(save_path, 'image')
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    data = {
        'x': data[:, 0],
        'y': data[:, 1],
        'label': label
    }

    df = pd.DataFrame(data=data)
    # 去掉部分数据(为了更好的可视化)
    # df = df[~((df['x']>10) | (df['y']>10))]

    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x='x', y='y', hue='label', palette='deep', s=3)
    plt.legend(loc=3, bbox_to_anchor=(1, 0))  # 设置图例位置
    plt.xlabel('UMAP1')
    plt.ylabel('UMAP2')
    plt.title(title)
    plt.savefig(os.path.join(save_path, "_".join(title.split()) + '.png'), bbox_inches='tight')  # dpi可以设置

    # 数据上报
    # wandb.save(os.path.join(save_path, "_".join(title.split()) + '.png'))
    # plt.show()


def concat_views(views):
    return np.concatenate(views, axis=1).astype(np.float64)


def batch_mixing_entropy(ref_data, query_data, L=100, M=300, K=500):
    '''
    :param ref_data:
    :param query_data:
    :param L: 次数
    :param M: 随机抽取的细胞数
    :param k: neibor数x
    :return: 返回一个BatchEntroy数组, 代表进行L次随机取样的结果
    '''
    data = np.concatenate([ref_data, query_data], axis=0)
    nbatchs = 2
    batch0 = np.concatenate([np.zeros(ref_data.shape[0]), np.ones(query_data.shape[0])])
    entropy = [0 for i in range(L)]
    kdtree = spt.KDTree(data)
    random.seed(0)
    data_idx = [p for p in range(data.shape[0])]
    for boot in range(L):
        rand_samples_idx = sample(data_idx, M)
        _, neighbor_idx = kdtree.query(data[rand_samples_idx, :], k=K)
        for i in range(len(rand_samples_idx)):
            for j in range(nbatchs):
                xi = max(1, (batch0[neighbor_idx[i]] == j).sum())
                entropy[boot] += xi * math.log(xi)
    entropy = [-(x / M) for x in entropy]
    return entropy


def encode_label(ref_label, query_label):
    '''
    :param ref_label: ref的label
    :param query_label:  query的label
    :return:
    '''
    enc = LabelEncoder()
    enc.fit(ref_label)

    return enc.transform(ref_label), enc.transform(query_label), enc


def precies_of_cell(cell_type, pred, trues):
    idx = np.array(np.where(trues == cell_type)).squeeze()
    acc = (pred[idx] == cell_type).sum() / len(idx)
    return acc

def show_result(ret, save_path):
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    joint_embedding = np.concatenate([ret['ref_out'], ret['query_out']], axis=0)

    # embedding_h_pca = runPCA(embedding_h)

    ref_h = joint_embedding[:ret['ref_out'].shape[0], :]
    query_h = joint_embedding[ret['ref_out'].shape[0]:, :]

    # evaluation metrics
    # total_s_score = silhouette_score(joint_embedding, list(ret['ref_label']) + list(ret['pred']))
    # ref_s_score = silhouette_score(ref_h, ret['ref_label'])
    # q_s_score = silhouette_score(query_h, ret['pred'])

    ari = adjusted_rand_score(ret['query_label'], ret['pred'])
    # bme = batch_mixing_entropy(ref_h, query_h)
    # bme = sum(bme) / len(bme)
    acc = accuracy_score(ret['query_label'], ret['pred'])
    f1 = f1_score(ret['query_label'], ret['pred'], average='macro')
    alpha_precision = precies_of_cell("alpha", ret['pred'], ret['query_label'])
    beta_precision = precies_of_cell("beta", ret['pred'], ret['query_label'])
    gamma_precision = precies_of_cell("gamma", ret['pred'], ret['query_label'])
    delta_precision = precies_of_cell("delta", ret['pred'], ret['query_label'])

    print("alpha precision is {:.3f}".format(alpha_precision))
    print("beta precision is {:.3f}".format(beta_precision))
    print("gamma precision is {:.3f}".format(gamma_precision))
    print("delta precision is {:.3f}".format(delta_precision))
    print("Prediction Accuracy is {:.3f}".format(acc))


    '''
        2023.1.3 以下代码暂时注释掉，为了multi ref更快显示结果，同时保存模型
    '''
    # print('f1-score is {:.3f}'.format(f1))
    # print('Prediction ARI is {:.3f}'.format(ari))
    #
    # # print('batch mixing score is {:.3f}'.format(bme))
    #
    #
    # # 这部分和原来的feature对应
    # raw_trues = np.concatenate([ret['ref_raw_label'], ret['query_label']]).reshape(-1)
    # # 这部分和h对应
    # trues_after_shuffle = np.concatenate([ret['ref_label'], ret['query_label']]).reshape(-1)
    # preds = np.concatenate([ret['ref_label'], ret['pred']]).reshape(-1)
    #
    # raw_data = np.concatenate([ret['ref_raw_data'], ret['query_raw_data']], axis=0)
    #
    # np.save(os.path.join(save_path, 'raw_trues.npy'), raw_trues)
    # np.save(os.path.join(save_path, 'preds.npy'), preds)
    # # exit()
    # raw_data_2d = runUMAP(raw_data)
    # h_data_2d = runUMAP(joint_embedding)
    #
    # np.save(os.path.join(save_path, 'raw_data_2d.npy'), raw_data_2d)
    # np.save(os.path.join(save_path, 'embeddings_2d.npy'), h_data_2d)
    # np.save(os.path.join(save_path, 'raw_trues.npy'), raw_trues)
    # np.save(os.path.join(save_path, 'preds.npy'), preds)
    # np.save(os.path.join(save_path, 'trues_after_shuffle.npy'), trues_after_shuffle)
    #
    # show_cluster(raw_data_2d, raw_trues, 'reference-query raw true label', save_path)
    # show_cluster(h_data_2d, trues_after_shuffle, 'reference-query h true label', save_path)
    # show_cluster(h_data_2d, preds, 'reference-query h pred label', save_path)
    # show_cluster(raw_data_2d,
    #              ["reference" for i in range(ref_h.shape[0])] + ["query" for i in range(query_h.shape[0])],
    #              "raw batches",
    #              save_path)
    # show_cluster(h_data_2d,
    #              ["reference" for i in range(ref_h.shape[0])] + ["query" for i in range(query_h.shape[0])],
    #              "h batches",
    #              save_path)
    '''
        ====== 以上 ======
    '''
    # show_cluster(raw_data_2d[:ret['ref_raw_data'].shape[0],:], ret['ref_raw_label'], "raw reference data", save_path)
    # show_cluster(raw_data_2d[ret['ref_raw_data'].shape[0]:,], ret['query_raw_label'], "raw query data", save_path)