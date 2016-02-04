try:
    import msvcrt  # used on windows to catch keyboard input
except:
    print('Warning: Could not import msvcrt (used for detecting keystrokes)')

import types
import logging
import time
import sys
import os
import numpy as np
import pyqtgraph as pg
import pyqtgraph.multiprocess as pgmp
from scipy.optimize import fmin_powell
from modules.measurement import hdf5_data as h5d
from modules.utilities import general
from modules.utilities.general import dict_to_ordered_tuples
from qcodes.plots.pyqtgraph import QtPlot


class MeasurementControl:
    '''
    New version of Measurement Control that allows for adaptively determining
    data points.
    '''
    def __init__(self, name, plot_theme=((60, 60, 60), 'w'), **kw):
        self.name = name
        # starting the process for the pyqtgraph plotting
        # You do not want a new process to be created every time you start a run
        self.plot_theme = plot_theme
        pg.mkQApp()
        self.proc = pgmp.QtProcess()  # pyqtgraph multiprocessing
        self.rpg = self.proc._import('pyqtgraph')
        self.win = self.rpg.GraphicsWindow(title='Plot monitor of %s' % self.name)
        self.win.setBackground(self.plot_theme[1])

    ##############################################
    # Functions used to control the measurements #
    ##############################################

    def run(self, name=None, mode='1D', **kw):
        '''
        Core of the Measurement control.
        '''
        self.set_measurement_name(name)
        self.print_measurement_start_msg()
        self.mode = mode
        with h5d.Data(name=self.get_measurement_name()) as self.data_object:
            self.get_measurement_begintime()
            #Commented out because requires git shell interaction from python
            # self.get_git_hash()
            # Such that it is also saved if the measurement fails
            # (might want to overwrite again at the end)
            self.save_instrument_settings(self.data_object)

            self.create_experimentaldata_dataset()
            if self.mode == '1D':
                self.measure()
            elif self.mode == '2D':
                self.measure_2D()
            elif self.mode == 'adaptive':
                self.measure_soft_adaptive()
            else:
                raise ValueError('mode %s not recognized' % self.mode)
            result = self.dset[()]
        return result

    def measure(self, *kw):
        self.initialize_plot_monitor()
        if (self.sweep_functions[0].sweep_control !=
                self.detector_function.detector_control):
                # FIXME only checks first sweepfunction
            raise Exception('Sweep and Detector functions not of the same type.'
                            + 'Aborting measurement')
            print(self.sweep_function.sweep_control)
            print(self.detector_function.detector_control)

        for sweep_function in self.sweep_functions:
            sweep_function.prepare()

        if self.sweep_functions[0].sweep_control == 'soft':
            self.detector_function.prepare()
            self.measure_soft_static()
        if self.sweep_functions[0].sweep_control == 'hard':
            self.iteration = 0
            if len(self.sweep_functions) == 1:
                self.detector_function.prepare(
                    sweep_points=self.get_sweep_points())
                self.measure_hard()
            elif len(self.sweep_functions) == 2:
                self.detector_function.prepare(
                    sweep_points=self.get_sweep_points()[0: self.xlen, 0])
                self.complete = False
                for j in range(self.ylen):
                    # added specifically for 2D hard sweeps
                    if not self.complete:
                        for i, sweep_function in enumerate(self.sweep_functions):
                            x = self.get_sweep_points()[
                                self.iteration*self.xlen]
                            if i != 0:
                                sweep_function.set_parameter(x[i])
                        self.measure_hard()
            else:
                raise Exception('hard measurements have not been generalized to N-D yet')
        for sweep_function in self.sweep_functions:
            sweep_function.finish()
        self.detector_function.finish()

        self.get_measurement_endtime()
        return

    def measure_soft_static(self):
        for i, sweep_point in enumerate(self.sweep_points):
            self.measurement_function(sweep_point)
            self.print_progress_static_soft_sweep(i)

    def measure_soft_adaptive(self, method=None):
        '''
        Uses the adaptive function and keywords for that function as
        specified in self.af_pars()
        '''
        self.save_optimization_settings()
        adaptive_function = self.af_pars.pop('adaptive_function')
        print('Adaptive function passed: %s' % adaptive_function)

        self.initialize_plot_monitor()
        for sweep_function in self.sweep_functions:
            sweep_function.prepare()
        self.detector_function.prepare()

        if adaptive_function == 'Powell':
            print('Optimizing using scipy.fmin_powell')
            adaptive_function = fmin_powell
        if type(adaptive_function) == types.FunctionType:
            try:
                adaptive_function(self.optimization_function, **self.af_pars)
            except StopIteration:
                print('Reached f_termination: %s' % (self.f_termination))
        else:
            raise Exception('optimization function: "%s" not recognized'
                            % adaptive_function)

        for sweep_function in self.sweep_functions:
            sweep_function.finish()
        self.detector_function.finish()

        self.get_measurement_endtime()
        return

    def measure_hard(self):
        '''
        ToDo: integrate soft averaging into MC
        '''
        # note, checking after the data comes in is pointless in hard msmt
        new_data = np.array(self.detector_function.get_values()).T

        if len(np.shape(new_data)) == 1:
            single_col = True
            shape_new_data = (len(new_data), 1)
        else:
            single_col = False
            shape_new_data = np.shape(new_data)

        # resizing only for 1 set of new_data  now... needs to improve
        shape_new_data = (shape_new_data[0], shape_new_data[1]+1)

        datasetshape = self.dset.shape

        self.iteration = datasetshape[0]/shape_new_data[0] + 1
        start_idx = int(shape_new_data[0]*(self.iteration-1))
        new_datasetshape = (shape_new_data[0]*self.iteration, datasetshape[1])
        self.dset.resize(new_datasetshape)
        len_new_data = shape_new_data[0]
        if single_col:
            self.dset[start_idx:,
                      len(self.sweep_functions)] = new_data
        else:
            self.dset[start_idx:,
                      len(self.sweep_functions):] = new_data

        sweep_len = len(self.get_sweep_points().T)
        # Only add sweep points if these make sense (i.e. same shape as new_data)
        if sweep_len == len_new_data:  # 1D sweep
            self.dset[:, 0] = self.get_sweep_points().T
        elif self.mode is '2D':  # 2D sweep
            # always add for a 2D sweep
            relevant_swp_points = self.get_sweep_points()[
                start_idx:start_idx+len_new_data:]
            self.dset[start_idx:, 0:len(self.sweep_functions)] = \
                relevant_swp_points

        self.update_plotmon()
        # for i in range(len(self.detector_function.value_names)):
        #     self.update_plotmon(
        #         mon_nr=i+1, x_ind=0,
        #         y_ind=-len(self.detector_function.value_names)+i)
        if hasattr(self, 'TwoD_array'):
            self.update_plotmon_2D_hard()
            self.print_progress_static_2D_hard()

        return new_data

    def measurement_function(self, x):
        '''
        Core measurement function used for soft sweeps
        '''

        if np.size(x) == 1:
            x = [x]
        if np.size(x) != len(self.sweep_functions):
            raise ValueError('size of x "%s" not equal to # sweep functions' % x)
        for i, sweep_function in enumerate(self.sweep_functions[::-1]):
            sweep_function.set_parameter(x[::-1][i])
            # x[::-1] changes the order in which the parameters are set, so
            # it is first the outer sweep point and then the inner.This
            # is generally not important except for specifics: f.i. the phase
            # of an agilent generator is reset to 0 when the frequency is set.

        datasetshape = self.dset.shape
        self.iteration = datasetshape[0] + 1

        # TODO: REMOVE THIS ONLY FOR BENCHMARKING
        # if self.iteration > 2:
        #     print('Time of iteration: {:.4g}'.format(time.time()-self.it_time))
        # self.it_time = time.time()

        vals = self.detector_function.acquire_data_point()

        # Resizing dataset and saving
        new_datasetshape = (self.iteration, datasetshape[1])
        self.dset.resize(new_datasetshape)
        savable_data = np.append(x, vals)
        self.dset[self.iteration-1, :] = savable_data
        # update plotmon
        self.update_plotmon()
        if hasattr(self, 'TwoD_array'):
            self.update_plotmon_2D()
        return vals

    def optimization_function(self, x):
        '''
        A wrapper around the measurement function.
        It takes the following actions based on parameters specified
        in self.af_pars:
        - Rescales the function using the "x_scale" parameter, default is 1
        - Inverts the measured values if "minimize"==False
        - Compares measurement value with 'f_termination' and raises an
        exception, that gets caught outside of the optimization loop, if
        the measured value is smaller than this f_termination.

        Measurement function with scaling to correct physical value
        '''
        if hasattr(self.x_scale, '__iter__'):  # to check if
            for i in range(len(x)):
                x[i] = float(x[i])/float(self.x_scale[i])
        elif self.x_scale != 1:  # only rescale if needed
            for i in range(len(x)):
                x[i] = float(x[i])/float(self.x_scale[i])
        if self.minimize_optimization:
            vals = self.measurement_function(x)
            if (self.f_termination is not None):
                if (vals < self.f_termination):
                    raise StopIteration()
        else:
            vals = self.measurement_function(x)
            # when maximizing interrupt when larger than condition before
            # inverting
            if (vals > self.f_termination) & (self.f_termination is not None):
                raise StopIteration()
            vals = np.multiply(-1, vals)

        # TODO: re add the extra plotmon that shows the progress of the
        # optimization
        # self.update_plotmon(
        #     mon_nr=5, x_ind=None,
        #     y_ind=-len(self.detector_function.value_names))
        # to check if vals is an array with multiple values
        if hasattr(vals, '__iter__'):
            if len(vals) > 1:
                vals = vals[0]
        return vals

    def finish(self):
        '''
        Deletes arrays to clean up memory
        (Note better way to do is also overload the remove function and make
        sure all attributes are removed.
        '''
        try:
            del(self.TwoD_array)
        except AttributeError:
            pass
        try:
            del(self.dset)
        except AttributeError:
            pass
        try:
            del(self.sweep_points)
        except AttributeError:
            pass


    ###################
    # 2D-measurements #
    ###################

    def run_2D(self, name=None, **kw):
        self.run(name=name, mode='2D', **kw)

    def measure_2D(self, **kw):
        '''
        Sweeps over two parameters set by sweep_function and sweep_function_2D.
        The outer loop is set by sweep_function_2D, the inner loop by the
        sweep_function.

        Soft(ware) controlled sweep functions require soft detectors.
        Hard(ware) controlled sweep functions require hard detectors.
        '''

        if np.size(self.get_sweep_points()[0]) == 2:
            self.measure(**kw)
        elif np.size(self.get_sweep_points()[0]) == 1:
            print('Reshaping sweep points')
            self.xlen = len(self.get_sweep_points())
            self.ylen = len(self.sweep_points_2D)

            # create inner loop pts
            self.sweep_pts_x = self.get_sweep_points()
            x_tiled = np.tile(self.sweep_pts_x, self.ylen)
            # create outer loop
            self.sweep_pts_y = self.sweep_points_2D
            y_rep = np.repeat(self.sweep_pts_y, self.xlen)
            c = np.column_stack((x_tiled, y_rep))
            self.set_sweep_points(c)
            self.preallocate_2D_plot()
            self.measure(**kw)
            # del self.TwoD_array
        return

    def set_sweep_function_2D(self, sweep_function):
        if len(self.sweep_functions) != 1:
            raise KeyError('Specify sweepfunction 1D before specifying sweep_function 2D')
        else:
            self.sweep_functions.append(sweep_function)
            self.sweep_function_names.append(
                str(sweep_function.__class__.__name__))

    def set_sweep_points_2D(self, sweep_points_2D):
        self.sweep_points_2D = sweep_points_2D

    ###########
    # Plotmon #
    ###########
    '''
    There are (will be) three kinds of plotmons, the regular plotmon,
    the 2D plotmon (which does a heatmap) and the adaptive plotmon.
    '''
    def initialize_plot_monitor(self):

        self._monitor_refresh_time = .5  # used when there is more than 200 pts
        self.win.clear()  # clear out previous data
        self.curves = []
        xlabels = self.column_names[0:len(self.sweep_function_names)]
        ylabels = self.column_names[len(self.sweep_function_names):]
        for ylab in ylabels:
            for xlab in xlabels:
                p = self.win.addPlot(pen=self.plot_theme[0])
                b_ax = p.getAxis('bottom')
                p.setLabel('bottom', xlab, pen=self.plot_theme[0])
                b_ax.setPen(self.plot_theme[0])
                l_ax = p.getAxis('left')
                l_ax.setPen(self.plot_theme[0])
                p.setLabel('left', ylab, pen=self.plot_theme[0])
                c = p.plot(symbol='o', symbolSize=7, pen=self.plot_theme[0])
                self.curves.append(c)
            self.win.nextRow()
        return self.win, self.curves

    def update_plotmon(self):
        i = 0
        try:
            time_since_last_mon_update = time.time() - self._mon_upd_time
        except:
            self._mon_upd_time = time.time()
            time_since_last_mon_update = 1e9
        # Update always if just a few points otherwise wait for the refresh
        # timer
        if (self.dset.shape[0] < 20 or time_since_last_mon_update >
                self._monitor_refresh_time):
            nr_sweep_funcs = len(self.sweep_function_names)
            for y_ind in range(len(self.detector_function.value_names)):
                for x_ind in range(nr_sweep_funcs):
                    x = self.dset[:, x_ind]
                    y = self.dset[:, nr_sweep_funcs+y_ind]
                    self.curves[i].setData(x, y)
                    i += 1
            self._mon_upd_time = time.time()

    def new_plotmon_window(self, plot_theme=None):
        '''
        respawns the pyqtgraph plotting window
        '''
        if plot_theme is not None:
            self.plot_theme = plot_theme
        self.win = self.rpg.GraphicsWindow(
            title='Plot monitor of %s' % self.name)
        self.win.setBackground(self.plot_theme[1])

    def preallocate_2D_plot(self):
        '''
        Preallocates a data array to be used for the update_plotmon_2D command.

        Made to work with at most 2 2D arrays (as this is how the labview code
        works). It should be easy to extend this function for more vals.
        '''
        self.time_last_2Dplot_update = time.time()
        n = len(self.sweep_pts_y)
        m = len(self.sweep_pts_x)
        if len(self.detector_function.value_names) == 1:
            self.TwoD_array = np.empty(n, m)
        else:
            self.TwoD_array = np.empty(
                [n, m, len(self.detector_function.value_names)])
        self.TwoD_array[:] = np.NAN

        self.QC_QtPlot = QtPlot(x=self.sweep_pts_x,
                                y=self.sweep_pts_y, z=self.TwoD_array,
                                cmap='Viridis')

    def update_plotmon_2D(self):
        '''
        Adds latest measured value to the TwoD_array and sends it
        to the plotmon.

        '''
        i = self.iteration-1
        x_ind = i % self.xlen
        y_ind = i / self.xlen
        if len(self.detector_function.value_names) == 1:
            z_ind = len(self.sweep_functions)
            self.TwoD_array[y_ind, x_ind] = self.dset[i, z_ind]

            # this is a workaround for updating the data in the live plot
            self.QC_QtPlot.traces[0]['config']['z'] = self.TwoD_array.T
        else:
            for j in range(2):
                z_ind = len(self.sweep_functions) + j
                self.TwoD_array[y_ind, x_ind, j] = self.dset[i, z_ind]
            self.QC_QtPlot.traces[0]['config']['z'] = self.TwoD_array[:, :, 0]

        if time.time() - self.time_last_2Dplot_update > self.QC_QtPlot.interval:
            self.time_last_2Dplot_update = time.time()
            self.QC_QtPlot.update_plot()

    def update_plotmon_2D_hard(self):
        '''
        Adds latest datarow to the TwoD_array and send it
        to the plotmon.
        Note that the plotmon only supports evenly spaced lattices.

        Made to work with at most 2 2D arrays (as this is how the labview code
        works). It should be easy to extend this function for more vals.
        '''
        i = self.iteration-1
        y_ind = i
        if len(self.detector_function.value_names) == 1:
            z_ind = len(self.sweep_functions)
            self.TwoD_array[:, y_ind] = self.dset[i*self.xlen:(i+1)*self.xlen,
                                                  z_ind]
            if self.Plotmon is not None:
                self.Plotmon.plot3D(1, data=self.TwoD_array,
                                    axis=(self.x_start, self.x_step,
                                          self.y_start, self.y_step))
        else:
            for j in range(2):
                z_ind = len(self.sweep_functions) + j
                self.TwoD_array[:, y_ind, j] = self.dset[
                    i*self.xlen:(i+1)*self.xlen, z_ind]
                if self.Plotmon is not None:
                    self.Plotmon.plot3D(j+1, data=self.TwoD_array[:, :, j],
                                        axis=(self.x_start, self.x_step,
                                              self.y_start, self.y_step))

    ##################################
    # Small helper/utility functions #
    ##################################

    def get_data_object(self):
        '''
        Used for external functions to write to a datafile.
        This is used in time_domain_measurement as a hack and is not
        recommended.
        '''
        return self.data_object

    def get_column_names(self):
        self.column_names = []
        self.sweep_par_names = []
        self.sweep_par_units = []

        for sweep_function in self.sweep_functions:
            self.column_names.append(sweep_function.parameter_name+' (' +
                                     sweep_function.unit+')')
            self.sweep_par_names.append(sweep_function.parameter_name)
            self.sweep_par_units.append(sweep_function.unit)

        for i, val_name in enumerate(self.detector_function.value_names):
            self.column_names.append(val_name+' (' +
                self.detector_function.value_units[i] + ')')
        return self.column_names

    def create_experimentaldata_dataset(self):
        data_group = self.data_object.create_group('Experimental Data')
        self.dset = data_group.create_dataset(
            'Data', (0, len(self.sweep_functions) +
                     len(self.detector_function.value_names)),
            maxshape=(None, len(self.sweep_functions) +
                      len(self.detector_function.value_names)))
        self.get_column_names()
        self.dset.attrs['column_names'] = h5d.encode_to_utf8(self.column_names)
        # Added to tell analysis how to extract the data
        data_group.attrs['datasaving_format'] = h5d.encode_to_utf8('Version 2')
        data_group.attrs['sweep_parameter_names'] = h5d.encode_to_utf8(self.sweep_par_names)
        data_group.attrs['sweep_parameter_units'] = h5d.encode_to_utf8(self.sweep_par_units)

        data_group.attrs['value_names'] = h5d.encode_to_utf8(self.detector_function.value_names)
        data_group.attrs['value_units'] = h5d.encode_to_utf8(self.detector_function.value_units)

    def save_optimization_settings(self):
        '''
        Saves the parameters used for optimization
        '''
        opt_sets_grp = self.data_object.create_group('Optimization settings')
        param_list = dict_to_ordered_tuples(self.af_pars)
        for (param, val) in param_list:
            opt_sets_grp.attrs[param] = str(val)

    def save_instrument_settings(self, data_object=None, *args):
        '''
        uses QCodes station snapshot to save the last known value of any
        parameter. Only saves the value and not the update time (which is
        known in the snapshot)
        '''
        if data_object is None:
            data_object = self.data_object
        if not hasattr(self, 'station'):
            logging.warning('No station object specified, could not save',
                            ' instrument settings')
        else:
            set_grp = data_object.create_group('Instrument settings')
            inslist = dict_to_ordered_tuples(self.station.instruments)
            for (iname, ins) in inslist:
                instrument_grp = set_grp.create_group(iname)
                par_snap = ins.snapshot()['parameters']
                parameter_list = dict_to_ordered_tuples(par_snap)
                for (p_name, p) in parameter_list:
                    try:
                        val = str(p['value'])
                    except KeyError:
                        val = ''
                    instrument_grp.attrs[p_name] = str(val)

    def print_progress_static_soft_sweep(self, i):
        percdone = (i+1)*1./len(self.sweep_points)*100
        elapsed_time = time.time() - self.begintime
        progress_message = "{percdone}% completed, elapsed time: "\
            "{t_elapsed} s, time left: {t_left} s".format(
                percdone=int(percdone),
                t_elapsed=round(elapsed_time, 1),
                t_left=round((100.-percdone)/(percdone) *
                             elapsed_time, 1) if
                percdone != 0 else '')
        if percdone != 100:
            end_char = '\r'
        else:
            end_char = '\n'
        print(progress_message, end=end_char)

    def print_progress_static_hard(self):
        acquired_points = self.dset.shape[0]
        total_nr_pts = self.sweep_points.shape[0]
        if acquired_points == total_nr_pts:
            self.complete = True
        elif acquired_points > total_nr_pts:
            self.complete = True
            logging.warning(
                'Warning nr of acq points is larger nr of sweep points')
            logging.warning('Acq pts: %s, total_nr_pts: %s' % (
                            acquired_points, total_nr_pts))

        percdone = acquired_points*1./total_nr_pts*100
        elapsed_time = time.time() - self.begintime
        scrmes = "{percdone}% completed, elapsed time: "\
            "{t_elapsed} s, time left: {t_left} s".format(
                percdone=int(percdone),
                t_elapsed=round(elapsed_time, 1),
                t_left=round((100.-percdone)/(percdone) *
                             elapsed_time, 1) if
                percdone != 0 else '')
        sys.stdout.write(60*'\b'+scrmes)

    def print_measurement_start_msg(self):
        if len(self.sweep_functions) == 1:
            print('\n')
            print('Starting measurement: %s' % self.get_measurement_name())
            print('Sweep function: %s' % self.get_sweep_function_names()[0])
            print('Detector function: %s' % self.get_detector_function_name())
        else:
            print('Starting measurement: %s' % self.get_measurement_name())
            for i, sweep_function in enumerate(self.sweep_functions):
                print('Sweep function %d: %s' % (
                    i, self.sweep_function_names[i]))
            print('Detector function: %s' % self.get_detector_function_name())

    def get_datetimestamp(self):
        return time.strftime('%Y%m%d_%H%M%S', time.localtime())

    ####################################
    # Non-parameter get/set functions  #
    ####################################

    def set_sweep_function(self, sweep_function):
        '''
        Used if only 1 sweep function is set.
        '''
        self.sweep_functions = [sweep_function]
        self.set_sweep_function_names(
            [str(sweep_function.name)])

    def get_sweep_function(self):
        return self.sweep_functions[0]

    def set_sweep_functions(self, sweep_functions):
        '''
        Used to set an arbitrary number of sweep functions.
        '''
        self.sweep_functions = sweep_functions

        sweep_function_names = []
        for swf in sweep_functions:
            sweep_function_names.append(str(swf.__class__.__name__))
            # input str(swf.__class__.__name__)
        self.set_sweep_function_names(sweep_function_names)

    def get_sweep_functions(self):
        return self.sweep_functions

    def set_sweep_function_names(self, swfname):
        self.sweep_function_names = swfname

    def get_sweep_function_names(self):
        return self.sweep_function_names

    def set_detector_function(self, detector_function):
        self.detector_function = detector_function
        self.set_detector_function_name(detector_function.name)

    def get_detector_function(self):
        return self.detector_function

    def set_detector_function_name(self, dfname):
        self._dfname = dfname

    def get_detector_function_name(self):
        return self._dfname

    ################################
    # Parameter get/set functions  #
    ################################

    def get_git_hash(self):
        self.git_hash = general.get_git_revision_hash()
        return self.git_hash

    def get_measurement_begintime(self):
        self.begintime = time.time()
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def get_measurement_endtime(self):
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def set_sweep_points(self, sweep_points):
        self.sweep_points = np.array(sweep_points)
        # line below is because some sweep funcs have their own sweep points attached
        self.sweep_functions[0].sweep_points = np.array(sweep_points)

    def get_sweep_points(self):
        return self.sweep_functions[0].sweep_points

    def set_adaptive_function_parameters(self, adaptive_function_parameters):
        self.af_pars = adaptive_function_parameters

        # scaling should not be used if a "direc" argument is available
        # in the adaptive function itself, if not specified equals 1
        self.x_scale = self.af_pars.pop('x_scale', 1)
        # Determines if the optimization will minimize or maximize
        self.minimize_optimization = self.af_pars.pop('minimize', True)
        self.f_termination = self.af_pars.pop('f_termination', None)
        print(self.f_termination)

    def get_adaptive_function_parameters(self):
        return self.af_pars

    def set_measurement_name(self, measurement_name):
        if measurement_name is None:
            self.measurement_name = 'Measurement'
        else:
            self.measurement_name = measurement_name

    def get_measurement_name(self):
        return self.measurement_name

    def set_optimization_method(self, optimization_method):
        self.optimization_method = optimization_method

    def get_optimization_method(self):
        return self.optimization_method
