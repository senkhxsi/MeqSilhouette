===========================
Requirements & Installation
===========================

The easiest way to run MeqSilhouette (focalpy38 -- Ubuntu 20.04 + Python 3.8) is to pull the docker image from Docker Hub.

Once you have `Docker <https://www.docker.com/>`_ installed on your Ubuntu system, run::

   $ docker pull iniyannatarajan/meqsilhouette:focalpy38

Instructions for building a new Docker image from the Dockerfile provided with the source can be found in the relevant section below.
If you do not have/want Docker, try one of the other options below.

Ubuntu 20.04 + Python 3.8
-------------------------
  
It is recommended to install the dependencies via the `KERN-7 <https://kernsuite.info>`_ software suite::

   $ sudo apt-get install software-properties-common
   $ sudo add-apt-repository -s ppa:kernsuite/kern-7
   $ sudo apt-add-repository multiverse
   $ sudo apt-add-repository restricted
   $ sudo apt-get update

Install the following dependencies via *apt-get*::

   $ sudo apt-get install meqtrees meqtrees-timba tigger-lsm python3-astro-tigger \
   python3-astro-tigger-lsm casalite wsclean pyxis python3-casacore

.. note:: The casacore data must be kept up-to-date. This can be done by following the instructions on the `CASA website <https://casaguides.nrao.edu/index.php/Fixing_out_of_date_TAI_UTC_tables_(missing_information_on_leap_seconds)>`_.

Optionally, install Latex (for creating paper-quality plots)::

  $ sudo apt-get install texlive-latex-extra texlive-fonts-recommended dvipng cm-super

*AATM v0.5* can be obtained from `here <https://launchpad.net/aatm>`_. AATM cannot create the executables necessary for running MeqSilhouette without the *boost* libraries. In Ubuntu 20.04 install *libboost-program-options-dev* using apt-get. Once this is installed, proceed as follows::

   $ cd /path/to/aatm-source-code
   $ ./configure --prefix=/path/to/aatm-installation
   $ make
   $ make install
   $ export PATH=$PATH:/path/to/install/aatm-installation/bin

If using a virtual environment, the following steps are necessary (skip ahead if not using *virtualenv*)::

   $ virtualenv /path/to/env
   $ source /path/to/env/bin/activate
   $ pip install -U pip setuptools wheel # recommended

.. note:: If --system-site-packages is not passed to virtualenv, the global packages installed via apt-get above will not be available and must be installed manually from source.

Now, check out MeqSilhouette from GitHub and install using pip::

   $ git clone https://github.com/rdeane/MeqSilhouette.git
   $ cd MeqSilhouette
   $ pip install .   

The *turbo-sim.py* script from MeqTrees is included in the *framework* directory. If you do not have it, add a symbolic link to the copy in your *meqtrees-cattery* installation::

   $ ln -s /path/to/meqtrees-cattery/Cattery/Siamese/turbo-sim.py /path/to/MeqSilhouette/framework/turbo-sim.py

Building Singularity image
--------------------------

The recommended way to run MeqSilhouette is via *Singularity*. 
The Singularity definition file *singularity.def* is shipped with the repository. 
If you do not have Singularity installed on your system, follow the installation instructions 
on the `Singularity website <https://sylabs.io/guides/3.5/admin-guide/installation.html>`_. 
Once Singularity is installed, the singularity image file (SIF) can be created as follows::

   $ sudo singularity build meqsilhouette.sif singularity.def

Note that the build process automatically ensures that *casacore* data are up-to-date. If these data
are missing, and if you do not have a working casa installation from which to obtain this
information, simply rebuild the image to eliminate this warning thrown by *CASA*.

Building Docker image
---------------------

*Docker* is also supported. Docker can be installed on your system via *apt-get* and the docker image can be built as follows::

   $ cd /path/to/Dockerfile
   $ docker build -t meqsilhouette .

As before, the build process ensures that *casacore* data are up-to-date.

Known installation issues
-------------------------

.. note:: One or more of the following issues were originally encountered with Ubuntu 18.04 + Python 2.7 and may possibly be never encountered in the future.

1. If MeqTrees cannot see the *TiggerSkyModel* module that ought to load when *turbo-sim.py* is run (i.e. when an ASCII sky model is used), the parent directory of *Tigger* must be added to PYTHONPATH. Bear in mind that this may cause python version conflicts with other packages. In that case, it is recommended to have Tigger installed in a separate directory such as /opt/Tigger. For manual installation of `Tigger <https://github.com/ska-sa/tigger>`_ and `tigger-lsm <https://github.com/ska-sa/tigger-lsm>`_, refer to their respective repositories. Without this, MeqSilhouette will still work with FITS images as input sky models.

2. If MeqSilhouette cannot find aatm, modify LD_LIBRARY_PATH as follows::

    export LD_LIBRARY_PATH=/path/to/aatm-0.5/lib:$LD_LIBRARY_PATH

3. If the error *Incorrect qhull library called* is thrown, ensure **scipy==0.17** is installed.

4. MeqSilhouette will soon be ported to *astropy.fits* and *pyfits* will no longer be a dependency. As of now though, *pyfits* is still required. If *pyfits* throws an ImportError for the modules *gdbm/winreg*, a quick and dirty fix is to open the following file::

    /path-to-virtualenv/lib/python2.7/site-packages/pyfits/extern/six.py

   and comment out the lines::

    MovedModule("dbm_gnu", "gdbm", "dbm.gnu")
    MovedModule("winreg", "_winreg")
