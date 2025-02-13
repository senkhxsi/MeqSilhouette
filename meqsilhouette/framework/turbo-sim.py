# -*- coding: utf-8 -*-
#% $Id$
#
#
# Copyright (C) 2002-2007
# The MeqTree Foundation &
# ASTRON (Netherlands Foundation for Research in Astronomy)
# P.O.Box 2, 7990 AA Dwingeloo, The Netherlands
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>,
# or write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

 # standard preamble
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from Timba.TDL import *
from Timba.Meq import meq
import math
import random

import Meow
import Meow.StdTrees

# MS options first
mssel = Meow.Context.mssel = Meow.MSUtils.MSSelector(has_input=False,has_model=False,tile_sizes=[8,16,32],flags=False);
# MS compile-time options
TDLCompileOptions(*mssel.compile_options());
TDLCompileOption("run_purr","Start Purr on this MS",False);
# MS run-time options
TDLRuntimeOptions(*mssel.runtime_options());
## also possible:
# TDLRuntimeMenu("MS selection options",open=True,*mssel.runtime_options());

# UVW
TDLCompileOptions(*Meow.IfrArray.compile_options());

# simulation mode menu
SIM_ONLY = "sim only";
ADD_MS   = "add to MS";
SUB_MS   = "subtract from MS";
simmode_opt = TDLCompileOption("sim_mode","Simulation mode",[SIM_ONLY,ADD_MS,SUB_MS]);
simmode_opt.when_changed(lambda mode:mssel.enable_input_column(mode!=SIM_ONLY));
model_opt = TDLCompileOption("read_ms_model","Read additional uv-model visibilities from MS",False,doc="""
  <P>If enabled, then an extra set of model visibilities will be read from a column
  of the MS, and added to whatever is predicted by the sky model <i>in the uv-plane</i> (i.e. subject to uv-Jones but not sky-Jones corruptions).</P>
  """);
model_opt.when_changed(mssel.enable_model_column);

# now load optional modules for the ME maker
from Meow import TensorMeqMaker
meqmaker = TensorMeqMaker.TensorMeqMaker();

# specify available sky models
# these will show up in the menu automatically
from Siamese.OMS import gridded_sky
from Siamese.AGW import azel_sky
from Siamese.OMS import transient_sky
from Siamese.OMS import fitsimage_sky

## OMS: time to retire this one
#import Meow.LSM
#lsm = Meow.LSM.MeowLSM(include_options=False);

models = [ gridded_sky,azel_sky,transient_sky,fitsimage_sky]; # ,lsm ];

try:
  from Siamese.OMS.tigger_lsm import TiggerSkyModel
  models.insert(0,TiggerSkyModel());
except:
  print('Failure to import TiggerSkyModel module')
  print('Is the location of Tigger defined in your PYTHONPATH environment variable?')
  pass;
      
meqmaker.add_sky_models(models);

# now add optional Jones terms
# these will show up in the menu automatically

# Ncorr - correct for N
from Siamese.OMS import oms_n_inverse
meqmaker.add_sky_jones('Ncorr','n-term correction',oms_n_inverse);

# Z - ionosphere
from Lions import ZJones
from Siamese.OMS import oms_ionosphere,oms_ionosphere2
meqmaker.add_sky_jones('Z','ionosphere',[oms_ionosphere,oms_ionosphere2,ZJones.ZJones()]);

# P - Parallactic angle or dipole projection
from Siamese.OMS.rotation import Rotation
from Siamese.OMS import oms_dipole_projection
meqmaker.add_sky_jones('L','parallactic angle or dipole rotation',[Rotation('L',feed_angle=False),oms_dipole_projection]);


# E - beam
from Siamese.OMS import analytic_beams
from Siamese.OMS import fits_beams0
from Siamese.OMS import pybeams_fits
from Siamese.OMS.emss_beams import emss_polar_beams
from Siamese.OMS import paf_beams
##OMS: retiting this one: from Siamese.OMS import wsrt_beams
from Siamese.OMS import vla_beams
from Siamese.SBY import lofar_beams
from Siamese.OMS import oms_pointing_errors
meqmaker.add_sky_jones('E','beam',[analytic_beams,pybeams_fits,emss_polar_beams,paf_beams,fits_beams0,vla_beams,lofar_beams],
                          pointing=oms_pointing_errors);

# P - Parallactic angle
from Siamese.OMS import feed_angle
meqmaker.add_uv_jones('P','feed orientation',[feed_angle]);
# meqmaker.add_uv_jones('P','feed angle',Rotation('P'));

# D - direction-independent leakage
from Siamese.OMS.leakage import Leakage
meqmaker.add_uv_jones('D','leakage',Leakage('D'));

# G - gains
from Siamese.OMS import oms_gain_models
meqmaker.add_uv_jones('G','gains/phases',oms_gain_models);

# P - Parallactic angle
meqmaker.add_uv_jones('iP','feed angle correction',Rotation('iP'));


# very important -- insert meqmaker's options properly
TDLCompileOptions(*meqmaker.compile_options());

# noise option
_noise_option = TDLOption("noise_stddev","Add noise, Jy per visibility",[None,1e-6,1e-3],more=float);
_sefd_options = [ 
    TDLOption("noise_sefd","SEFD, Jy",0,more=float),
    TDLOption("noise_sefd_bw_khz","Channel width, kHz",4,more=float),
    TDLOption("noise_sefd_integration","Integration, s",60,more=float),
];
_sefd_menu = TDLMenu("Compute from SEFD",toggle="noise_from_sefd",
  doc="""To compute per-visibility noise from the system equivalent flux density, enable this option,
and enter correct values for SEFD (per antenna), channel width and integration time in the fields below.
The formula actually used is sigma = SEFD/sqrt(2*bandwidth*integration).
""",
  *_sefd_options);

TDLCompileMenu("Add noise",
  _noise_option,
  _sefd_menu);
  
def _recompute_noise (dum):
  if noise_from_sefd:
    _noise_option.set_value(noise_sefd/math.sqrt(noise_sefd_bw_khz*1e+3*noise_sefd_integration));

for opt in _sefd_options + [_sefd_menu]:
  opt.when_changed(_recompute_noise);
  
TDLCompileOption("random_seed","Random generator seed",["time",0],more=int,
  doc="""<P>To get a reproducible distribution for noise (and other "random" errors), supply a fixed seed value 
  here. The default setting of "time" uses the current time to seed the generator, so the distribution
  is different upon every run.</P>""");

# MPI options
# from Meow import Parallelization
# TDLCompileOptions(*Parallelization.compile_options());

def _define_forest (ns):
  random.seed(random_seed if isinstance(random_seed,int) else None);
  if not mssel.msname:
    raise RuntimeError("MS not set up in compile-time options");
  if run_purr:
    print(mssel.msname);
    import os.path
    purrlog = os.path.normpath(mssel.msname)+".purrlog";
    Timba.TDL.GUI.purr(purrlog,[mssel.msname,'.']);
  # setup contexts properly
  array,observation = mssel.setup_observation_context(ns);

  # setup imaging options (now that we have an imaging size set up)
  imsel = mssel.imaging_selector(npix=512,arcmin=meqmaker.estimate_image_size());
  TDLRuntimeMenu("Imaging options",*imsel.option_list());

  # reading in model?
  if read_ms_model:
    model_spigots = array.spigots(column="PREDICT",corr=mssel.get_corr_index());
    meqmaker.make_per_ifr_bookmarks(model_spigots,"UV-model visibilities");
  else:
    model_spigots = None;

  # get a predict tree from the MeqMaker
  output = meqmaker.make_predict_tree(ns,uvdata=model_spigots);

  # throw in a bit of noise
  if noise_stddev:
    noisedef = Meq.GaussNoise(stddev=noise_stddev,dims=[2,2],complex=True)
    for p,q in array.ifrs():
      ns.noisy_predict(p,q) << output(p,q) + ( ns.noise(p,q)<<noisedef );
    output = ns.noisy_predict;

  # in add or subtract sim mode, make some spigots and add/subtract visibilities
  if sim_mode == ADD_MS:
    spigots = array.spigots(corr=mssel.get_corr_index());
    for p,q in array.ifrs():
      ns.sum(p,q) << output(p,q) + spigots(p,q);
    output = ns.sum;
  elif sim_mode == SUB_MS:
    spigots = array.spigots(corr=mssel.get_corr_index());
    for p,q in array.ifrs():
      ns.diff(p,q) << spigots(p,q) - output(p,q);
    output = ns.diff;
  else:
    spigots = False;

  meqmaker.make_per_ifr_bookmarks(output,"Output visibilities");

  # make sinks and vdm.
  # The list of inspectors comes in handy here
  Meow.StdTrees.make_sinks(ns,output,spigots=spigots,post=meqmaker.get_inspectors(),corr_index=mssel.get_corr_index());

  # very important -- insert meqmaker's options properly
  TDLRuntimeOptions(*meqmaker.runtime_options());

  TDLRuntimeJob(_simulate_MS,"Run simulation",job_id="simulate");

  # close the meqmaker. This produces annotations, etc.
  meqmaker.close();

def _simulate_MS (mqs,parent,wait=False):
  mqs.clearcache('VisDataMux');
  mqs.execute('VisDataMux',mssel.create_io_request(),wait=wait);
  
_tdl_job_1_simulate_MS = _simulate_MS

# this is a useful thing to have at the bottom of the script, it allows us to check the tree for consistency
# simply by running 'python script.tdl'

if __name__ == '__main__':
  ns = NodeScope();
  _define_forest(ns);
  # resolves nodes
  ns.Resolve();

  print(len(ns.AllNodes()),'nodes defined');
