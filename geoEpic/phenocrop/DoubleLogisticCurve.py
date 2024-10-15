from scipy.optimize import least_squares
from scipy.special import expit
from scipy import signal
import numpy as np


class DoubleLogisticCurve:
    def __init__(self):
        # Parameters for the first and second logistic curves
        self.params = 5.5, 0.12, 150, 0.12, 250  
    
    def double_logistic(self, x, c, k1, x0_1, k2, x0_2):
        """Double logistic curve equation, representing the sum of two logistic curves."""
        return c * (expit(k1 * (x - x0_1)) - expit(k2 * (x - x0_2)))

    def derivative(self, x, n=1):
        """Calculate the n-th derivative of the double logistic curve at point x."""
        c, k1, x0_1, k2, x0_2 = self.params
        if n == 1:
            return 1e2 * (c * (k1 * np.exp(-k1 * (x - x0_1)) / (1 + np.exp(-k1 * (x - x0_1)))**2 
                                - k2 * np.exp(-k2 * (x - x0_2)) / (1 + np.exp(-k2 * (x - x0_2)))**2))
        elif n == 2:
            return 1e4 * (c * k1**2 * (1 - np.exp(k1 * (x - x0_1))) * np.exp(k1 * (x - x0_1)) / (np.exp(k1 * (x - x0_1)) + 1)**3 -
                          c * k2**2 * (1 - np.exp(k2 * (x - x0_2))) * np.exp(k2 * (x - x0_2)) / (np.exp(k2 * (x - x0_2)) + 1)**3)
        elif n == 3:
            return 1e6 * (c * k1**3 * ((np.exp(k1 * (x - x0_1)) + 1)**2 - 6 * np.exp(k1 * (x - x0_1))) * np.exp(k1 * (x - x0_1)) / (np.exp(k1 * (x - x0_1)) + 1)**4 -
                          c * k2**3 * ((np.exp(k2 * (x - x0_2)) + 1)**2 - 6 * np.exp(k2 * (x - x0_2))) * np.exp(k2 * (x - x0_2)) / (np.exp(k2 * (x - x0_2)) + 1)**4)
        else:
            raise ValueError("Derivative order n must be 1, 2, or 3.")
    
    def fit(self, xdata, ydata):
        """Fit the double logistic model to the data."""
        loss = lambda args: self.double_logistic(xdata, *args) - ydata
        popt = least_squares(loss, self.params, loss='cauchy', f_scale=0.5, max_nfev=100000, bounds=([3, 0.01, 0, 0.01, 50], 
                                                                         [8.5, 0.12, 250, 0.15, 365]))
 
        self.params = popt.x
    
    def __call__(self, x):
        """Predict y values using the fitted model."""
        return self.double_logistic(x, *self.params)
    
    def get_dates(self):
        """Calculate Phenological doys"""
        doy = np.arange(365)
        diff3 = self.derivative(doy, 3)
        peaks, _ = signal.find_peaks(diff3, height = 0)
        # print()
        emergence = peaks[0]
        peaks, _ = signal.find_peaks(-diff3, height = 0)
        harvest = peaks[-1]

        return emergence, harvest