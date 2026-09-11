#!/bin/bash
#SBATCH --job-name=example_run
#SBATCH --output=R-%x.%j.out
#SBATCH --partition=shared
#SBATCH --ntasks=21
#SBATCH --mem=64GB
#SBATCH --time=1:15:00
#SBATCH --account=surint
#SBATCH --mail-user egrant@nlr.gov
#SBATCH --mail-type BEGIN,END,FAIL
module purge
module load conda
conda activate /projects/surint/campd_spheres/national_analysis/environment_folder/h2i_env
module load PrgEnv-intel
module load craype-x86-spr intel-oneapi-compilers intel-oneapi-mpi intel-oneapi-mkl fftw/3.3.10-intel-oneapi-mpi-intel
module load hdf5/1.14.1-2-intel-oneapi-mpi-intel netcdf-c/4.9.2-intel-oneapi-mpi-intel petsc/3.20.4-intel-oneapi-mpi-intel

export TMPDIR=/scratch/egrant/sc_tmp/
srun -n 21 /projects/surint/campd_spheres/national_analysis/environment_folder/h2i_env/bin/python /projects/surint/campd_spheres/national_analysis/software/nice_us/simulation/run_plants.py
