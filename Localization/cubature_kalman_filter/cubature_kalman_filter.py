"""
Implementation of Cubature Kalman filter using Constant Turn Rate and Velocity (CTRV) motion model
Fuse sensor data from IMU and GPS to obtain accurate position

Author: Raghuram Shankar
"""

import math
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import sqrtm

"""
initialize global variables and flags
"""


dt = 0.1
N = 100

show_final = 1
show_animation = 0
show_ellipse = 0


z_noise = np.array([[0.1, 0.0, 0.0, 0.0],
                    [0.0, 0.1, 0.0, 0.0],
                    [0.0, 0.0, 0.1, 0.0],
                    [0.0, 0.0, 0.0, 0.1]])


x_0 = np.array([[0.0],                                  # x position    [m]
                [0.0],                                  # y position    [m]
                [0.0],                                  # yaw           [rad]
                [1.0],                                  # velocity      [m/s]
                [0.1]])                                 # yaw rate      [rad/s]


p_0 = np.array([[1e-3, 0.0, 0.0, 0.0, 0.0],
                [0.0, 1e-3, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0]])


q = np.array([[1e-11, 0.0,    0.0,               0.0, 0.0],
              [0.0, 1e-11,    0.0,               0.0, 0.0],
              [0.0, 0.0,    np.deg2rad(1e-4),   0.0, 0.0],
              [0.0, 0.0,    0.0,               1e-4, 0.0],
              [0.0, 0.0,    0.0,                0.0, np.deg2rad(1e-4)]])


hx = np.array([[1.0, 0.0, 0.0, 0.0, 0.0],
               [0.0, 1.0, 0.0, 0.0, 0.0],
               [0.0, 0.0, 0.0, 1.0, 0.0],
               [0.0, 0.0, 0.0, 0.0, 1.0]])


r = np.array([[0.015, 0.0, 0.0, 0.0],
              [0.0, 0.010, 0.0, 0.0],
              [0.0, 0.0, 0.1, 0.0],
              [0.0, 0.0, 0.0, 0.01]])**2


"""
Main Program
"""


def main():
    print(__file__ + " start!!")
    x_est = x_0
    p_est = p_0
    x_true = x_0
    x_true_cat = np.array([x_0[0, 0], x_0[1, 0]])
    x_est_cat = np.array([x_0[0, 0], x_0[1, 0]])
    z_cat = np.array([x_0[0, 0], x_0[1, 0]])
    for i in range(N):
        x_true = f(x_true)
        z = gen_measurement(x_true)
        if i == (N - 1) and show_final == 1:
            show_final_flag = 1
        else:
            show_final_flag = 0
        if show_animation == 1:
            plot_animation(i, x_true_cat, x_est_cat, z)
        if show_ellipse == 1:
            plot_ellipse(x_est[0:2], p_est)
        if show_final_flag == 1:
            plot_final(x_true_cat, x_est_cat, z_cat)
        x_est, p_est = cubature_kalman_filter(x_est, p_est, z)
        x_true_cat = np.vstack((x_true_cat, x_true[0:2].T))
        x_est_cat = np.vstack((x_est_cat, x_est[0:2].T))
        z_cat = np.vstack((z_cat, z[0:2].T))
    print('CKF Over')


def cubature_kalman_filter(x_est, p_est, z):
    x_pred, p_pred = cubature_prediction(x_est, p_est)
    x_upd, p_upd = cubature_update(x_pred, p_pred, z)
    return x_upd, p_upd


""" 
Motion model
"""


def f(x):
    x[0] = x[0] + (x[3]/x[4]) * (np.sin(x[4] * dt + x[2]) - np.sin(x[2]))
    x[1] = x[1] + (x[3]/x[4]) * (- np.cos(x[4] * dt + x[2]) + np.cos(x[2]))
    x[2] = x[2] + x[4] * dt
    x[3] = x[3]
    x[4] = x[4]
    return x


"""
Measurement model
"""


def h(x):
    x = hx @ x
    return x


"""
Cubature Kalman Filter
"""


def sigma(x, p):
    n = np.shape(x)[0]
    SP = np.zeros((n, 2*n))
    W = np.zeros((1, 2*n))
    for i in range(n):
        SD = sqrtm(p)
        SP[:, i] = (x + (math.sqrt(n) * SD[:, i]).reshape((n, 1))).flatten()
        SP[:, i+n] = (x - (math.sqrt(n) * SD[:, i]).reshape((n, 1))).flatten()
        W[:, i] = 1/(2*n)
        W[:, i+n] = W[:, i]
    return SP, W


def cubature_prediction(x_pred, p_pred):
    n = np.shape(x_pred)[0]
    [SP, W] = sigma(x_pred, p_pred)
    x_pred = np.zeros((n, 1))
    p_pred = q
    for i in range(2*n):
        x_pred = x_pred + (f(SP[:, i]).reshape((n, 1)) * W[0, i])
    for i in range(2*n):
        p_step = (f(SP[:, i]).reshape((n, 1)) - x_pred)
        p_pred = p_pred + (p_step @ p_step.T * W[0, i])
    return x_pred, p_pred


def cubature_update(x_pred, p_pred, z):
    n = np.shape(x_pred)[0]
    m = np.shape(z)[0]
    [SP, W] = sigma(x_pred, p_pred)
    y_k = np.zeros((m, 1))
    P_xy = np.zeros((n, m))
    s = r
    for i in range(2*n):
        y_k = y_k + (h(SP[:, i]).reshape((m, 1)) * W[0, i])
    for i in range(2*n):
        p_step = (h(SP[:, i]).reshape((m, 1)) - y_k)
        P_xy = P_xy + ((SP[:, i]).reshape((n, 1)) -
                       x_pred) @ p_step.T * W[0, i]
        s = s + p_step @ p_step.T * W[0, i]
    x_pred = x_pred + P_xy @ np.linalg.pinv(s) @ (z - y_k)
    p_pred = p_pred - P_xy @ np.linalg.pinv(s) @ P_xy.T
    return x_pred, p_pred


"""
Generate Measurements
"""


def gen_measurement(x_true):
    """x position [m], y position [m]"""
    gz = hx @ x_true
    z = gz + z_noise @ np.random.randn(4, 1)
    return z


"""
Post Processing
"""


def plot_animation(i, x_true_cat, x_est_cat, z):
    if i == 0:
        plt.plot(x_true_cat[0], x_true_cat[1], '.r')
        plt.plot(x_est_cat[0], x_est_cat[1], '.b')
    else:
        plt.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r')
        plt.plot(x_est_cat[0:, 0], x_est_cat[0:, 1], 'b')
    plt.plot(z[0], z[1], '+g')
    plt.grid(True)
    plt.pause(0.001)


def plot_ellipse(x_est, p_est):
    phi = np.linspace(0, 2 * math.pi, 100)
    p_ellipse = np.array(
        [[p_est[0, 0], p_est[0, 1]], [p_est[1, 0], p_est[1, 1]]])
    x0 = 3 * sqrtm(p_ellipse)
    xy_1 = np.array([])
    xy_2 = np.array([])
    for i in range(100):
        arr = np.array([[math.sin(phi[i])], [math.cos(phi[i])]])
        arr = x0 @ arr
        xy_1 = np.hstack([xy_1, arr[0]])
        xy_2 = np.hstack([xy_2, arr[1]])
    plt.plot(xy_1 + x_est[0], xy_2 + x_est[1], 'r')
    plt.pause(0.00001)


def plot_final(x_true_cat, x_est_cat, z_cat):
    fig = plt.figure()
    f = fig.add_subplot(111)
    f.plot(x_true_cat[0:, 0], x_true_cat[0:, 1], 'r', label='True Position')
    f.plot(x_est_cat[0:, 0], x_est_cat[0:, 1], 'b', label='Estimated Position')
    f.plot(z_cat[0:, 0], z_cat[0:, 1], '+g', label='Noisy Measurements')
    f.set_xlabel('x [m]')
    f.set_ylabel('y [m]')
    f.set_title('Cubature Kalman Filter - CTRV Model')
    f.legend(loc='upper left', shadow=True, fontsize='large')
    plt.grid(True)
    plt.show()


if __name__ == '__main__':
    main()
