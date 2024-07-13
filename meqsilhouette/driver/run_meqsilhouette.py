# coding: utf-8
import time
PYXIS_ROOT_NAMESPACE=True # INI: For Python3 compatibility
import Pyxis
from Pyxis.ModSupport import *
#import ms # INI: 29-oct-2018: not used anywhere!
import im.argo as argo
import glob
import re
import os
import sys
import pyrap.tables as pt
import meqsilhouette.framework
from meqsilhouette.framework.process_input_config import setup_keyword_dictionary, load_json_parameters_into_dictionary
from meqsilhouette.framework.create_ms import create_ms, create_msv2
from meqsilhouette.framework.SimCoordinator import SimCoordinator
from meqsilhouette.framework.meqtrees_funcs import make_dirty_image_lwimager
from meqsilhouette.utils.comm_functions import *

def run_meqsilhouette(config=None):
    """
    Standard script to perform radio interferometric synthetic data generation.
    Variables prefixed by "v" indicate new global variables.

    Parameters
    ----------
    config : str, optional
        Path to the input JSON parset file. If not provided, the function will
        check command line arguments for the file. If still not found, the
        function will abort.

    Raises
    ------
    Exception
        If no input JSON parset file is provided and none is found in command
        line arguments, an exception is raised and the function aborts.

    """
    start = time.time()
    
    # Check for input file
    if config==None:
        if len(sys.argv) != 2:
            abort('MeqSilhouette needs an input JSON parset file. Aborting...')
        else:
            config = sys.argv[1]

    ### load input configuration file parameters ###
    config_abspath = os.path.abspath(config)
    parameters = load_json_parameters_into_dictionary(config_abspath)
    ms_dict = setup_keyword_dictionary('ms_', parameters)
    im_dict = setup_keyword_dictionary('im_', parameters)
    trop_dict = setup_keyword_dictionary('trop_', parameters)
    
    # make sure that correct number of bandpass tables is provided for number of observing frequencies provided
    if type(ms_dict['nu']) is not list and type(parameters['bandpass_table']) is list:
        abort('If only one observing frequency is chosen, "bandpass_table" should not be a list. Aborting...')
    elif type(ms_dict['nu']) is list and type(parameters['bandpass_table']) is not list:
        abort('If more than one observing frequency is chosen, "bandpass_table" should be a list. Aborting...')
    else:
        pass
    
    if type(ms_dict['nu']) is not list
        ms_dict['nu'] = [ms_dict['nu']]
        parameters['bandpass_table'] = [parameters['bandpass_table']]
        
    for n, nu in enumerate(ms_dict['nu']):
        ms_config_string = str(ms_dict['antenna_table'].split('/')[-1]) + '_' \
                + re.sub("\.fits$|\.txt$","",parameters['input_fitsimage'].split('/')[-1])\
                + '_RA%.0fdeg_DEC%.0fdeg_pol%s_%.0fGHz-BW%iMHz-%ichan-%is-%.0fhrs'\
                %(ms_dict['RA'],ms_dict['DEC'],ms_dict['polproducts'].replace(' ','-'),\
                nu,ms_dict['dnu']*1e3,ms_dict['nchan'],ms_dict['tint'],\
                ms_dict['obslength'])
                        # attached to base (output_msname_base ) to name MS
        
        
        ### set directory paths ###
        #v.CODEDIR = os.environ['MEQS_DIR']
        #v.FRAMEWORKDIR = os.path.dirname(framework.__file__)
        #v.OUTDIR = os.path.join(v.CODEDIR,parameters['outdirname']) # full output path of current simulation
        v.FRAMEWORKDIR = os.path.dirname(meqsilhouette.framework.__file__)
        v.OUTDIR = parameters['outdirname']
        v.PLOTDIR = os.path.join(v.OUTDIR,'plots')
        v.MS = os.path.join(v.OUTDIR, ms_config_string + '.MS')  # name of output Measurement Set

        #input_fitsimage = os.path.join(v.CODEDIR,parameters['input_fitsimage'])
        input_copy_path = v.OUTDIR+'/inputs' # directory in which to copy all the input files
        input_fitsimage = os.path.join(input_copy_path, parameters['input_fitsimage'].split('/')[-1]) # use this path for input_fitsimage since this directory must be writable

        # Check if input sky model exists
        if not os.path.exists(parameters['input_fitsimage']+'.txt') and not os.path.exists(parameters['input_fitsimage']+'.lsm.html') and not os.path.isdir(parameters['input_fitsimage']):
            abort("NO INPUT LSM FOUND. Verify if 'input_fitsimage' in input .json configuration file \n"+"is the prefix of a sky model ending with '.txt'/'.html', or a dir containing fits image(s).\n")

        # Create output directory if it does not exist
        if not os.path.exists(v.OUTDIR):
            os.makedirs(v.PLOTDIR)
            os.makedirs(input_copy_path)
        else:
            info('%s exists; overwriting contents.'%(v.OUTDIR))

        # INI: Copy all input files to the output directory
        os.system('cp -r %s %s'%(config_abspath, input_copy_path))
        if os.path.isdir(parameters['input_fitsimage']):
            os.system('cp -r %s %s'%(parameters['input_fitsimage'], input_copy_path))
        else:
            if os.path.exists(parameters['input_fitsimage']+'.txt'):
                os.system('cp -r %s %s'%(parameters['input_fitsimage']+'.txt', input_copy_path))
            elif os.path.exists(parameters['input_fitsimage']+'.lsm.html'):
                os.system('cp -r %s %s'%(parameters['input_fitsimage']+'.lsm.html', input_copy_path))
        os.system('cp -r %s %s'%(parameters['station_info'], input_copy_path))
        os.system('cp -r %s %s'%(parameters['bandpass_table'][n], input_copy_path))
        os.system('cp -r %s %s'%(ms_dict['antenna_table'], input_copy_path))

        input_fitspol = parameters['input_fitspol']
        input_changroups = parameters['input_changroups']
        
        info('Loaded input configuration file: \n%s'%config_abspath)
        info('Input FITS image: \n%s'%input_fitsimage)
        print_simulation_summary(ms_dict,im_dict)

    #    else:
    #        abort('Selected output directory exists! \n\t[%s]'%OUTDIR + \
    #              '\n\tChange parameter <outdirname> in input configuration file:'+\
    #              '\n\t[%s]'%config_abspath)'''
        
        info('Input sky model: %s'%input_fitsimage)

        if (parameters['output_to_logfile']):
            v.LOG = OUTDIR + "/meqsilhouette-logfile.txt" 
        else:
            info('All output will be printed to terminal.')
            info('Print to log file by setting <output_to_logfile> parameter in input configuration file.')

        info('Loading station info table %s'%parameters['station_info'])
        T_rx, pwv, gpress, gtemp, coherence_time, pointing_rms, PB_FWHM230, aperture_eff, gR_mean, gR_std,\
        gL_mean, gL_std, dR_mean, dR_std, dL_mean, dL_std, feed_angle = \
        np.swapaxes(np.loadtxt(parameters['station_info'],\
        skiprows=1, usecols=[1, 2, 3, 4, 5+n, 6+n, 7+n, 9+n, 10+n, 11+n, 12+n, 13+n, 14+n, 15+n, 16+n, 17+n, 18+n], dtype=np.complex128), 0, 1)
        # extract real parts
        T_rx = T_rx.real
        pwv = pwv.real
        gpress = gpress.real
        gtemp = gtemp.real
        coherence_time = coherence_time.real
        pointing_rms = pointing_rms.real
        PB_FWHM230 = PB_FWHM230.real
        aperture_eff = aperture_eff.real
        feed_angle = feed_angle.real
        
        station_names_txt = np.loadtxt(parameters['station_info'],\
                                    usecols=[0],dtype=str,skiprows=1).tolist()
        anttab = pt.table(ms_dict['antenna_table'],ack=False)
        station_names_anttab = anttab.getcol('STATION')
        anttab.close()
        if (len(station_names_txt) != len(station_names_anttab)):
            abort('Mis-matched number of antennas in %s and %s'\
                %(parameters['station_info'],ms_dict['antenna_table']))
        if (station_names_txt != station_names_anttab):
            warn('Mis-matched station name order in %s versus %s (see comparison):'\
                %(parameters['station_info'],ms_dict['antenna_table']))
            for c1,c2 in zip(station_names_txt,station_names_anttab):
                print("%s\t\t%s" % (c1, c2))
            abort('Correct input station_info file and/or antenna table')
    

        info('Station info table %s corresponds correctly to antenna table %s'\
            %(parameters['station_info'],ms_dict['antenna_table']))

        if parameters['bandpass_enabled']:
            if not os.path.isfile(parameters['bandpass_table'][n]):
                abort("File '%s' does not exist. Aborting..."%(parameters['bandpass_table'][n]))
            station_names_txt = np.loadtxt(parameters['bandpass_table'][n],\
                                        usecols=[0],dtype=str,skiprows=1).tolist()
            if (len(station_names_txt) != len(station_names_anttab)):
                abort('Mis-matched number of antennas in %s and %s'\
                    %(parameters['bandpass_table'][n],ms_dict['antenna_table']))
            if (station_names_txt != station_names_anttab):
                warn('Mis-matched station name order in %s versus %s (see comparison):'\
                    %(parameters['bandpass_table'][n],ms_dict['antenna_table']))
                for c1,c2 in zip(station_names_txt,station_names_anttab):
                    print("%s\t\t%s" % (c1, c2))
                abort('Correct input station_info file and/or antenna table')

        bandpass_table = parameters['bandpass_table'][n]
        bandpass_freq_interp_order = parameters['bandpass_freq_interp_order']

        # INI: Determine correlator efficiency based on the number of bits used for quantization (refer TMS (2017) sec 8.3)
        if parameters['corr_quantbits'] == 1: corr_eff = 0.636
        elif parameters['corr_quantbits'] == 2: corr_eff = 0.88
        else: abort('Invalid number of bits used for quantization. Value of "corr_quantbits" in input json file must be 1 or 2')

        info('Creating empty MS')
        #create_ms(MS, input_fitsimage, ms_dict)
        create_msv2(MS, input_fitsimage, ms_dict)

        # Move simms log into the output directory
        #os.system('mv %s %s'%('log-simms.txt', input_copy_path.rsplit('/',1)[0]))

        # INI: Write mount types into the MOUNT column in the empty MS prior to generating synthetic data.
        station_mount_types = np.loadtxt(parameters['station_info'], usecols=[19], dtype=str, skiprows=1)
        tab = pt.table(v.MS)
        anttab = pt.table(tab.getkeyword('ANTENNA'), readonly=False)
        anttab.putcol('MOUNT', station_mount_types)
        anttab.close()
        tab.close()

        info('Simulating sky model into %s column in %s'%(ms_dict['datacolumn'],MS))
        sim_coord = SimCoordinator(MS,ms_dict["datacolumn"],input_fitsimage, input_fitspol, input_changroups, bandpass_table, bandpass_freq_interp_order, T_rx, corr_eff, parameters['predict_oversampling'], \
                                parameters["predict_seed"], parameters["atm_seed"], aperture_eff,\
                                parameters["elevation_limit"], parameters['trop_enabled'], parameters['trop_wetonly'], pwv, gpress, gtemp, \
                                coherence_time, parameters['trop_fixdelay_max_picosec'], parameters['uvjones_g_on'], parameters['uvjones_d_on'], parameters['parang_corrected'],\
                                gR_mean, gR_std, gL_mean, gL_std, dR_mean, dR_std, dL_mean, dL_std, feed_angle, parameters['add_thermal_noise'])

        sim_coord.interferometric_sim()

        info('Start corrupting the perfect visibilities. The corruptions (if enabled) are applied in the following order:\n'+
        '1. Pointing errors\n2. Tropospheric effects\n3. Parallactic angle and polarization leakage\n4. Receiver gains\n5. Bandpass effects\n6. Additive thermal noise')
        
        if parameters['pointing_enabled']:
            info('Pointing errors are enabled, applying antenna-based amplitudes errors')
            info('Current pointing error model is a constant offset that changes on a user-specified time interval, current setting = %.1f minutes'%\
                parameters['pointing_time_per_mispoint'])
            
            sim_coord.pointing_constant_offset(pointing_rms,parameters['pointing_time_per_mispoint'],PB_FWHM230)
            sim_coord.apply_pointing_amp_error()

            if parameters['pointing_makeplots']:
                sim_coord.plot_pointing_errors()

            
        ### TROPOSPHERE COMPONENTS ###
        combined_phase_errors = 0 #init for trop combo choice

        if parameters['trop_enabled']:
            info('Tropospheric module is enabled, applying corruptions...')
            if parameters['trop_wetonly']:
                info('... using only the WET component')
            else:
                info('... using both WET and DRY components')
            
            if parameters['trop_attenuate']:
                info('TROPOSPHERE ATTENUATE: attenuating signal using PWV-derived opacity...')
                sim_coord.trop_opacity_attenuate() 

            if parameters['trop_mean_delay']:
                info('TROPOSPHERE DELAY: computing mean delay (time-variability from elevation changes)...')
                sim_coord.trop_calc_mean_delays()
                combined_phase_errors += sim_coord.phasedelay_alltimes
        
            if parameters['trop_turbulence']:
                info('TROPOSPHERE TURBULENCE: computing Kolmogorov turbulence phase errors...')
                sim_coord.trop_generate_turbulence_phase_errors()
                combined_phase_errors += sim_coord.turb_phase_errors
                
            if parameters['trop_fixdelays']:
                info('TROPOSPHERE INSERT FIXED DELAY: non-variable delay calculated')
                sim_coord.trop_calc_fixdelay_phase_offsets()
                combined_phase_errors += sim_coord.fixdelay_phase_errors

            if not isinstance(combined_phase_errors, int):
                info('TROPOSPHERE: applying desired combination of phase errors...')
                sim_coord.apply_phase_errors(combined_phase_errors) 

            info('All selected tropospheric corruptions applied.')

            if parameters['trop_makeplots']:
                sim_coord.trop_plots()
                info('Generated troposphere plots')

        ### PARALLACTIC ANGLE AND POLARIZATION LEAKAGE ###
        if parameters['uvjones_d_on']:
            info('Introducing parallactic angle rotation and polarization leakage effects')
            sim_coord.add_pol_leakage_manual()
            info('Polarization leakage and parallactic angle effects added successfully.')
            info('Generating parallactic angle plots...')
            sim_coord.make_pol_plots()

        ### RECEIVER GAINS ###
        if parameters['uvjones_g_on']:
            info('Introducing complex (direction-independent) gain effects')
            sim_coord.add_gjones_manual()
            info('Complex gains added successfully.')

        ### BANDPASS COMPONENTS ###
        if parameters['bandpass_enabled']:
            info('BANDPASS: incorporating bandpass (B-Jones) effects')
            sim_coord.add_bjones_manual()
            info('B-Jones terms applied.')       
            if parameters['bandpass_makeplots']:
                info('Generating bandpass plots...')
                sim_coord.make_bandpass_plots()

        ### Add all noise components and fill in the weight columns
        if parameters['trop_enabled']:
            sim_coord.add_noise(parameters['trop_noise'], parameters['add_thermal_noise'])
        elif parameters['add_thermal_noise']:
            # do not add trop_noise regardless of its value since trop_enabled is False
            sim_coord.add_noise(parameters['trop_enabled'], parameters['add_thermal_noise'])

        ### IMAGING, PLOTTING, DATA EXPORT ###        
        if parameters['make_image']:
            info('Imaging the %s column'%ms_dict['datacolumn'])
            make_dirty_image_lwimager(im_dict,ms_dict) #, v.OUTDIR)
            if not os.path.exists(II('${OUTDIR>/}${MS:BASE}')+'-dirty_map.fits'):
                abort('OUTPUT IMAGE NOT FOUND')
                abort('Looks like imaging, or something upstream of that failed.')

        if parameters['ms_makeplots']:
            info('Generating MS-related plots...')
            sim_coord.make_ms_plots()
        # insert new plot here of coloured baselines and legend

        if parameters['exportuvfits']:
            info('Exporting %s to uvfits file %s'%(MS,MS.replace('.ms','.uvfits')))
            im.argo.icasa('exportuvfits', mult=[{'vis': v.MS, 'fitsfile': os.path.join(OUTDIR,v.MS.replace('.ms','.uvfits').replace('.MS','.uvfits'))}])

        # #Cleanup
        info('Cleaning up...')
        if (os.path.exists('./core')): x.sh('rm core')
        finish_string = "Pipeline finished in %.1f seconds" % (time.time()-start)
        info(finish_string)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        abort('MeqSilhouette needs an input JSON parset file. Aborting...')
    else:
        conf = sys.argv[1]
        run_meqsilhouette(conf)
