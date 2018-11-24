import matplotlib.pyplot as plt
import numpy as np
import json
from struct import *
from scipy import integrate
from scipy.signal import butter, lfilter, gausspulse, periodogram
from matplotlib.widgets import RadioButtons
import sys


class Signal:
    def __init__(self, filename):
        with open(filename, "r") as f:
            sig = unpack('cccc', f.read(4))
            self.channels_count = unpack('i', f.read(4))[0]
            self.sample_size = unpack('i', f.read(4))[0]
            self.spectrum_lines_count = unpack('i', f.read(4))[0]
            self.slice_frequency = unpack('i', f.read(4))[0]
            self.frequency_resolution = unpack('f', f.read(4))[0]
            self.receive_time = unpack('f', f.read(4))[0]
            self.total_receive_time = unpack('i', f.read(4))[0]
            self.user_blocks_count = unpack('i', f.read(4))[0]
            self.data_size = unpack('i', f.read(4))[0]
            self.blocks_count = unpack('i', f.read(4))[0]
            self.max = unpack('f', f.read(4))[0]
            self.min = unpack('f', f.read(4))[0]
            self.values = [unpack('f', f.read(4))[0] for i in range(0, self.sample_size, 1)]

    def rms(self):
        return np.sqrt(np.mean(np.square(self.values)))

    def peak_factor(self):
        return self.max / self.rms()

    def peak(self):
        return self.max - self.min

    def params_description(self):
        return 'MIN: {0:.2f}, MAX: {1:.2f}, PEAK: {2:.2f}, RMS: {3:.2f}, PEAK FACTOR: {4:.2f}' \
            .format(self.min, self.max, self.peak(), self.rms(), self.peak_factor())

    def butter_bandpass(self, lowcut, highcut, fs, order=5):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        return b, a

    def butter_bandpass_filter(self, lowcut, highcut, fs, order=5):
        b, a = self.butter_bandpass(lowcut, highcut, fs, order=order)
        y = lfilter(b, a, self.values)
        return y


class SignalPlot:

    def __init__(self, signals, options=None):
        if options is None:
            options = {}
        fig = plt.figure()
        rect = [0.1, 0.1, 0.7, 0.8]
        ax = fig.add_axes(rect)
        ax.grid()

        self.fig = fig
        self.ax = ax
        self.signals = signals

        if 'filter' in options and options['filter'] == True:
            self.plot_filtered(options['min'], options['max'])
        elif 'distr' in options and options['distr'] == True:
            self.plot_distr(bins=options['bins'])
        else:
            self.sax = fig.add_axes([0.8, 0.7, 0.2, 0.2])
            self.radio = RadioButtons(self.sax, ('default', 'spectr', 'int', 'dint'))
            self.radio.on_clicked(self.select_mode)
            self.plot_linear()

    def select_mode(self, label):
        if label == 'default':
            self.plot_linear()
        elif label == 'spectr':
            self.plot_af()
        elif label == 'int':
            self.plot_integrated()
        elif label == 'dint':
            self.plot_double_integrated()

    def plot_linear(self):
        self.ax.clear()

        info = len(self.signals) == 1
        for signal in self.signals:
            self.plot_linear_signal(signal, info=info)

        self.fig.canvas.draw_idle()

    def plot_linear_signal(self, signal, info=False):
        # plt.clf()
        step = float(signal.receive_time) / float(len(signal.values))
        t = np.arange(0, signal.receive_time, step)
        # plt.figure(1)

        title = ''
        if info:
            title = signal.params_description()

        self.ax.plot(t, signal.values)
        self.ax.set(xlabel='time (s)', title=title)

    def plot_af(self):
        self.ax.clear()

        for signal in self.signals:
            self.plot_af_signal(signal)

        self.fig.canvas.draw_idle()

    def plot_af_signal(self, signal):
        Fs = len(signal.values)  # sampling rate
        Ts = signal.receive_time / Fs  # sampling interval
        t = np.arange(0, 1, Ts)  # time vector

        ff = signal.slice_frequency  # frequency of the signal
        y = np.array(signal.values)

        n = len(y)  # length of the signal
        k = np.arange(n)
        T = n / Fs
        frq = k / T  # two sides frequency range
        frq = frq[range(n / 2)]  # one side frequency range

        Y = np.fft.fft(y) / (n / 2)  # fft computing and normalization
        Y = Y[range(n / 2)]

        # plt.figure(2)
        # n = len(signal.values)
        # d = signal.receive_time / n
        # ampl = np.fft.fft(signal.values)
        # freq = np.fft.fftfreq(n, d)
        self.ax.plot(frq, abs(Y))  # plotting the spectrum
        self.ax.set_xlabel('Freq (Hz)')
        self.ax.set_ylabel('Ampl')

    def plot_filtered_signal(self, signal, min, max):
        step = float(signal.receive_time) / float(len(signal.values))
        t = np.arange(0, signal.receive_time, step)
        y = signal.butter_bandpass_filter(lowcut=min, highcut=max, fs=len(signal.values), order=1)
        self.ax.plot(t, y, label='Filtered signal')
        self.ax.set_xlabel('time (s)')

    def plot_filtered(self, min, max):
        self.ax.clear()

        for signal in self.signals:
            self.plot_filtered_signal(signal, min, max)

        self.fig.canvas.draw_idle()

    def plot_int_signal(self, signal):
        step = float(signal.receive_time) / float(len(signal.values))
        t = np.arange(0, signal.receive_time, step)
        y_int = integrate.cumtrapz(signal.values, t, initial=0)
        self.ax.plot(t, y_int, label='Integrated signal')
        self.ax.set_xlabel('time (s)')

    def plot_integrated(self):
        self.ax.clear()

        for signal in self.signals:
            self.plot_int_signal(signal)

        self.fig.canvas.draw_idle()

    def plot_dint_signal(self, signal):
        step = float(signal.receive_time) / float(len(signal.values))
        t = np.arange(0, signal.receive_time, step)
        y_int = integrate.cumtrapz(signal.values, t, initial=0)
        y_int_d = integrate.cumtrapz(y_int, t, initial=0)
        self.ax.plot(t, y_int_d, label='Integrated signal')
        self.ax.set_xlabel('time (s)')

    def plot_double_integrated(self):
        self.ax.clear()

        for signal in self.signals:
            self.plot_dint_signal(signal)

        self.fig.canvas.draw_idle()

    def plot_distr_signal(self, signal, bins=4):
        self.ax.hist(signal.values, bins=bins)

    def plot_distr(self, bins=4):
        self.ax.clear()

        for signal in self.signals:
            self.plot_distr_signal(signal, bins=bins)

        self.fig.canvas.draw_idle()

    def plot_wavelet_signal(self, signal):
        step = float(signal.receive_time) / float(len(signal.values))
        t = np.arange(0, signal.receive_time, step)
        i = gausspulse(t, fc=5)
        self.ax.plot(t, i)

    def plot_wavelet(self):
        self.ax.clear()

        for signal in self.signals:
            self.plot_wavelet_signal(signal)

        self.fig.canvas.draw_idle()


def read_signal_data(filename):
    with open(filename, "r") as f:
        lines = f.readlines()
        values = [float(line.strip()) for line in lines]
        return values


plots = []


def main(argv):
    filename = "/Users/abastun/Library/Containers/com.stunba.DSP/Data/Library/Application Support/config.json"

    # matplotlib.use('TkAgg')
    # plt.interactive(False)

    with open(filename, "r") as f:
        signals = []
        one_window = True

        data = json.load(f)

        for filepath in data["files"]:
            signals.append(Signal(filepath))

        one_window = data["draw_in_one_window"]

        if one_window:
            plots.append(SignalPlot(signals, options=data))
        else:
            for signal in signals:
                plots.append(SignalPlot([signal], options=data))

        plt.show()

def plot():
    n = 4
    st = 0.025
    x = np.arange(-n, n, st)
    t = 2
    pf = x * np.pi
    tpf = pf * 2 * t
    sinx = np.sin(tpf) * t * 2
    y = sinx / tpf
    plt.plot(x, y)
    t = 3
    pf = x * np.pi
    tpf = pf * 2 * t
    sinx = np.sin(tpf) * t * 2
    y = sinx / tpf
    plt.plot(x, y)
    plt.show()


if __name__ == "__main__":
    plot()
    # main(sys.argv[1:])
