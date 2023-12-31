#!/usr/bin/env python

from os import path
from time import perf_counter as clock
from urllib import request

from astropy.io import fits
import numpy as np
import matplotlib.pyplot as plt

from ppxf.ppxf import ppxf
import ppxf.ppxf_util as util
import ppxf.sps_util as lib

def ppxf_example_kinematics_sauron(file, degree):

    ppxf_dir = path.dirname(path.realpath(util.__file__))

    # Read a galaxy spectrum and define the wavelength range
    #
    hdu = fits.open(file)
    gal_lin = hdu[0].data
    h1 = hdu[0].header

    lamRange1 = h1['CRVAL1'] + np.array([0., h1['CDELT1']*(h1['NAXIS1'] - 1)])
    fwhm_gal = 4.2  # SAURON has an instrumental resolution FWHM of 4.2A.
    
    # Use these lines if your spectrum is at low-z (z<0.01)
    redshift_0 = 0                  # Ignore cosmological redshift for local galaxies
    redshift = 0.0015               # Initial redshift estimate of the galaxy

    galaxy, ln_lam1, velscale = util.log_rebin(lamRange1, gal_lin)
    galaxy = galaxy/np.median(galaxy)  # Normalize spectrum to avoid numerical issues
    noise = np.full_like(galaxy, 0.0047)           # Assume constant noise per pixel here

    sps_name = 'emiles'

    # The templates span a much larger wavelength range. To save some
    # computation time, I truncate the spectra to a similar but slightly larger
    # range than the galaxy.
    lam_range_temp = [lamRange1[0]/1.02, lamRange1[1]*1.02]

    # Read SPS models file from my GitHub if not already in the ppxf package dir.
    # The SPS model files are also available here https://github.com/micappe/ppxf_data
    basename = f"spectra_{sps_name}_9.0.npz"
    filename = path.join(ppxf_dir, 'sps_models', basename)
    sps = lib.sps_lib(filename, velscale, fwhm_gal, wave_range=lam_range_temp)

    # Compute a mask for gas emission lines
    goodPixels = util.determine_goodpixels(ln_lam1, lam_range_temp, redshift)

    # Here the actual fit starts. The best fit is plotted on the screen. Gas
    # emission lines are excluded from the pPXF fit using the GOODPIXELS
    # keyword.
    c = 299792.458
    vel = c*np.log(1 + redshift)   # eq.(8) of Cappellari (2017, MNRAS)
    start = [vel, 200.]  # (km/s), starting guess for [V, sigma]
    t = clock()

    pp = ppxf(sps.templates, galaxy, noise, velscale, start,
              goodpixels=goodPixels, plot=True, moments=4, lam=np.exp(ln_lam1),
              lam_temp=sps.lam_temp, degree=degree)

    # The updated best-fitting redshift is given by the following
    # lines (using equations 5 of Cappellari 2022, arXiv, C22)
    errors = pp.error*np.sqrt(pp.chi2)  # Assume the fit is good chi2/DOF=1
    redshift_fit = (1 + redshift_0)*np.exp(pp.sol[0]/c) - 1  # eq. (5c) C22
    redshift_err = (1 + redshift_fit)*errors[0]/c            # eq. (5d) C22

    print("Formal errors:")
    print("     dV    dsigma   dh3      dh4")
    print("".join("%8.2g" % f for f in errors))
    print('Elapsed time in pPXF: %.2f s' % (clock() - t))
    prec = int(1 - np.floor(np.log10(redshift_err)))  # two digits of uncertainty
    print(f"Best-fitting redshift z = {redshift_fit:#.{prec}f} "
          f"+/- {redshift_err:#.{prec}f}")
    plt.pause(5)

##############################################################################

if __name__ == '__main__':
    file = '/home/daniel/Documents/Swinburne/ultra-diffuse-galaxies/results/NGC_247/5P/obj1/mean.fits'
    degree = 5
    ppxf_example_kinematics_sauron(file, degree)
