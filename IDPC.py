"""
Description: IDPC 基于迭代的DPC算法
"""
import sys
import scipy.cluster.hierarchy as sch
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from multiprocessing import Pool


class DPC(object):
    """
    1. 读取点
    2. 计算距离
    3. 计算截断距离 dc
    4. 计算局部密度 rho
    5. 计算 delta
    6. 确定 聚类中心
    7. 聚类
    8. 绘图
    """

    def __init__(self, path, data_name, n=0, dc_method=0, dc_percent=1, rho_method=1, delta_method=1, use_halo=False, plot=None):
        # 读取点，计算距离
        points, d_matrix, d_list, min_dis, max_dis, max_id = self.load_points_cacl_distance(path)
        d_matrix1 = d_matrix

        # 计算截断距离 dc
        dc = self.get_dc(d_matrix, d_list, min_dis, max_dis, max_id, dc_percent, dc_method)
        print('dc: ', dc)
        # 计算 rho
        rho = self.get_rho(d_matrix, max_id, dc, rho_method)
        # 迭代确定聚类中心
        center = self.get_center(d_matrix, rho, dc, n, max_id)
        print(center)
        # 聚类
        cluster = self.assign(d_matrix1, dc, rho, center, max_id)
        halo = []
        if use_halo:
            # halo
            cluster, halo = self.get_halo(d_matrix, rho, cluster, center, dc, max_id)
        if plot is None:
            # 单数据集绘制图分布
            fig = plt.figure(figsize=(6.2, 6.2))
            axe = plt.subplot(1,1,1)
            # fig.subplots_adjust(left=0.05, right=0.95)
            self.draw_cluster(data_name, cluster, halo, points, axe)
            plt.show()
        else:
            # 全部数据集画图
            self.draw_cluster(data_name, cluster, halo, points, plot)

    def load_points_cacl_distance(self, path):
        print(path)
        points = pd.read_csv(path, sep='\t', usecols=[0, 1])
        max_id = len(points)
        d = pd.DataFrame(np.zeros((max_id, max_id)))  # 距离矩阵
        dis = sch.distance.pdist(points, 'euclidean')  # 欧式距离
        n = 0
        for i in range(max_id):
            for j in range(i + 1, max_id):
                d.at[i, j] = dis[n]
                d.at[j, i] = d.at[i, j]
                n += 1
        min_dis = d.min().min()
        max_dis = d.max().max()
        return points, d, dis, min_dis, max_dis, max_id

    def get_dc(self, d, d_list, min_dis, max_dis, max_id, percent, method):
        """ 求解截断距离

        Desc:

        Args:
            d: 距离矩阵
            d_list: 上三角矩阵
            min_dis: 最小距离
            max_dis: 最大距离
            max_id: 点数
            percent: 占全部点的百分比数
            method: 采用求解dc的方法

        Returns:
            dc: 截断距离

        """
        print('Get dc')
        lower = percent / 100
        upper = (percent + 1) / 100
        if method == 0:
            while 1:
                dc = (min_dis + max_dis) / 2
                neighbors_percent = len(d_list[d_list < dc]) / (((max_id - 1) ** 2) / 2)  # 上三角矩阵
                if lower <= neighbors_percent <= upper:
                    return dc
                elif neighbors_percent > upper:
                    max_dis = dc
                elif neighbors_percent < lower:
                    min_dis = dc

    def get_rho(self, d, max_id, dc, method):
        """ 获取局部密度

        Desc:

        Args:
            d: 距离矩阵
            max_id: 点数
            dc: 截断距离
            method: 计算rho的方法(0, 1, 2)

        Returns:
            rho: 局部密度

        """
        print('Get rho')
        rho = np.zeros(max_id)
        for i in range(max_id):
            if method == 0:  # 和点i距离小于dc的点的数量
                rho[i] = len(d.loc[i, :][d.loc[i, :] < dc]) - 1
            elif method == 1:  # 高斯核
                for j in range(max_id):
                    rho[i] += math.exp(-(d.at[i, j] / dc) ** 2)
            elif method == 2:  # 新方法: 排除dc的异常
                n = int(max_id * 0.05)
                rho[i] = math.exp(-(d.loc[i].sort_values().values[:n].sum() / (n - 1)))
        return rho

    def get_center(self, d, rho, dc, n, max_id):
        """ 获取聚类中心点

        Desc:

        Args:
            d: 距离矩阵
            rho: 局部密度
            delta:
            dc
            n: 聚类中心数目
            max_id

        Returns:
            center: 聚类中心列表

        """
        # gamma = pd.DataFrame(gamma, columns=['gamma']).sort_values('gamma', ascending=False)
        # center = np.array(gamma.index)[:n]  # 取前n个点做中心点
        #  center = gamma[gamma.gamma > threshold].loc[:, 'gamma'].index
        rho_temp = rho.copy()
        center = np.zeros(n, dtype=int)

        center[0] = np.argmax(rho_temp)
        rho_temp[center[0]] = 0

        # for j in range(1, i + 1):
        #     print(j)
        #     distance = (distance * np.array(d.iloc[center[j - 1], :])) / (distance + np.array(d.iloc[center[j - 1], :]))
        #
        # gamma = rho_temp * distance

        for i in range(1, n):
            distance = np.zeros(max_id)
            # for j in range(1, i+1):
            #     print(j)
            #     distance = distance + np.power(np.array(d.iloc[center[j-1], :]), 2)
            for j in range(1, i + 1):
                if j == 1:
                    distance = np.array(d.iloc[center[0], :])
                else:
                    distance = (distance * np.array(d.iloc[center[j - 1], :])) / (distance + np.array(d.iloc[center[j - 1], :]))

            gamma = rho_temp * distance
            center[i] = np.argmax(gamma)
            rho_temp[center[i]] = 0
        return center

    def assign(self, d, dc, rho, center, max_id):
        """ 聚类，分配点

        Desc:

        Args:
            d:
            dc
            rho
            delta
            center: 聚类中心点列表
            max_id

        Returns:
            cluster: dict(center, points)

        """
        print('Assign')
        cluster = dict()  # center: points
        for i in center:
            cluster[i] = []

        link = dict()
        order_rho_index = rho.argsort()[-1::-1]  # 局部密度降序
        for i, v in enumerate(order_rho_index):
            if v in center:
                link[v] = v
                continue
            rho_index = order_rho_index[:i]
            link[v] = d.loc[v, rho_index].sort_values().index.tolist()[0]  # 下一个
        for i, v in link.items():
            c = v
            while c not in center:  # 链式寻找
                c = link[c]
            cluster[c].append(i)

        # 最近中心分配
        # for i in range(max_id):
        #     c = d.loc[i, center].idxmin()
        #     cluster[c].append(i)
        return cluster

    def get_halo(self, d, rho, cluster, center, dc, max_id):
        """ 获取halo 和 core

        Desc:

        Args:
            d:
            rho
            cluster
            center
            dc
            max_id

        Returns:
            cluster
            halo

        """
        print('Get halo')
        all_points = set(list(range(max_id)))  # 所有的点
        self.border_b = []
        for c, points in cluster.items():
            others_points = list(set(all_points) - set(points))  # 属于其他聚类的点
            border = []
            for p in points:
                if d.loc[p, others_points].min() < dc:  # 到其他聚类的点的距离小于dc
                    border.append(p)
            if len(border) != 0:
                #  rho_b = rho[border].max()  # 边界域中密度最大的值
                point_b = border[rho[border].argmax()]  # 边界域中密度最大的点
                self.border_b.append(point_b)
                rho_b = rho[point_b]  # 边界域最大密度
                filter_points = np.where(rho >= rho_b)[0]  # 筛选可靠性高的点
                points = list(set(filter_points) & set(points))  # 该聚类中可靠性高的点
                cluster[c] = points
        # halo
        cluster_points = set()
        for c, points in cluster.items():
            cluster_points = cluster_points | set(points)
        halo = list(set(all_points) - cluster_points)  # 光晕点
        return cluster, halo

    def draw_roh_delta(self, rho, delta, center, plot):
        plot.scatter(rho, delta, label='rho-delta', c='k', s=5)
        plot.set_xlabel('rho')
        plot.set_ylabel('delta')
        center_rho = rho[center]
        center_delta = delta[center]
        np.random.seed(6)
        colors = np.random.rand(len(center), 3)
        plot.scatter(center_rho, center_delta, c=colors)
        plot.legend()

    def draw_gamma(self, rho, delta, plot):
        gamma = pd.DataFrame(rho * delta, columns=['gamma']).sort_values('gamma', ascending=False)
        plot.scatter(range(len(gamma)), gamma.loc[:, 'gamma'], label='gamma', s=5)
        #  plot.hlines(avg, 0, len(gamma), 'b', 'dashed')
        plot.set_xlabel('n')
        plot.set_ylabel('gamma')
        plot.set_title('gamma')
        plot.legend()

    def draw_cluster(self, title, cluster, halo, points, plot):
        cluster_points = dict()
        colors = dict()
        np.random.seed(10)
        for k, v in cluster.items():
            cluster_points[k] = points.loc[cluster[k], :]
            colors[k] = np.random.rand(3)
        for k, v in cluster_points.items():
            plot.scatter(v.loc[:, 'x'], v.loc[:, 'y'], c=colors[k].reshape(1, -1), alpha=0.5)
            plot.scatter(v.at[k, 'x'], v.at[k, 'y'], c=colors[k].reshape(1, -1), s=np.pi * 10 ** 2)
        if len(halo) != 0:
            noise_pointer = points.loc[halo, :]
            plot.scatter(noise_pointer.loc[:, 'x'], noise_pointer.loc[:, 'y'], c='k')
            border_b = points.loc[self.border_b, :]
            plot.scatter(border_b.loc[:, 'x'], border_b.loc[:, 'y'], c='k', s=np.pi * 5 ** 2)
        plot.set_title(title)

    def draw_points(self, points, center=[]):
        points.plot(x='x', y='y', kind='scatter')
        plt.scatter(points.loc[:, 'x'], points.loc[:, 'y'], c='b', alpha='0.5')
        if len(center) != 0:
            center_p = points.loc[center, :]
            plt.scatter(center_p.loc[:, 'x'], center_p.loc[:, 'y'], c='r', s=np.pi * 10 ** 2)
        plt.show()


# 进程函数
# path | title | N: 聚类数 | dc method | dc per | rho method | delta method | use_halo | plot
def cluster(path, data_name, n, dc_method=0, dc_percent=1, rho_method=1, delta_method=1, use_halo=False, plot=None):
    DPC(path, data_name, n, dc_method, dc_percent, rho_method, delta_method, use_halo, plot)


def draw_all_cluster():
    path = sys.path[0] + '/dataset/'
    # 全部数据集绘图
    fig, axes = plt.subplots(5, 2, figsize=(12, 30))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.99, bottom=0.01)
    DPC(path + 'origin_1000.dat', 'origin-1000', 5, dc_percent=2, use_halo=True, plot=axes[0][1])
    # DPC(path + 'origin_4000.dat', 'origin-4000', 5, dc_percent=2, use_halo=True, plot=axes[0][0])
    #
    # DPC(path + 'flame.dat', 'flame', 2, dc_percent=3, use_halo=True, plot=axes[1][0])
    # DPC(path + 'spiral.dat', 'spiral', 3, dc_percent=2, use_halo=True, plot=axes[1][1])
    # DPC(path + 'aggregation.dat', 'aggregation', 7, dc_percent=3, use_halo=True, plot=axes[2][0])
    # DPC(path + 'R15.dat', 'R15', 15, use_halo=True, plot=axes[2][1])
    # DPC(path + 'D31.dat', 'D31', 31, use_halo=True, plot=axes[3][0])
    # DPC(path + 'jain.dat', 'jain', 2, use_halo=True, plot=axes[3][1])
    # DPC(path + 'pathbased.dat', 'pathbased', 3, dc_percent=4, use_halo=True, plot=axes[4][0])
    # DPC(path + 'compound.dat', 'compound', 5, dc_percent=4, use_halo=True, plot=axes[4][1])
    plt.show()


if __name__ == '__main__':
    # 绘制全部数据集结果
    # draw_all_cluster()

    # 绘制指定数据集详情
    p = Pool(4)
    path = sys.path[0] + '/dataset/'
    # path | title | N: 聚类数 | dc method | dc per | rho method | delta method | use_halo | plot
    # p.apply_async(cluster, args=(path + 'origin_4000.dat', 'origin-4000', 5, 0, 2, 1, 1, False))
    p.apply_async(cluster, args=(path + 'origin_1000.dat', 'origin-1000', 5, 0, 2, 1, 1, False))
    # p.apply_async(cluster, args=(path + 'flame.dat', 'flame', 2, 0, 1, 1, 1, False))
    # p.apply_async(cluster, args=(path + 'spiral.dat', 'spiral', 3, 0, 3))
    # p.apply_async(cluster, args=(path + 'aggregation.dat', 'aggregation', 7, 0, 3))
    # p.apply_async(cluster, args=(path + 'R15.dat', 'R15', 15, 0, 20))
    # p.apply_async(cluster, args=(path + 'R15.dat', 'R15', 15, 0, 2))
    # p.apply_async(cluster, args=(path + 'D31.dat', 'D31', 31))
    # p.apply_async(cluster, args=(path + 'jain.dat', 'jain', 2))
    # p.apply_async(cluster, args=(path + 'pathbased.dat', 'pathbased', 3, 0, 4))
    # p.apply_async(cluster, args=(path + 'compound.dat', 'compound', 5, 0, 4))
    # p.apply_async(cluster, args=(path + 't48k.dat', 't48k', 6, 0, 2))
    p.close()
    p.join()

