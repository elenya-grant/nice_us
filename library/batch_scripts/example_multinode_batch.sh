#!/bin/bash                                                                                                             
#SBATCH --job-name=existing_wind_add_solar_subset0
#SBATCH --output=/projects/surint/campd_spheres/national_analysis/batch_logs/%u-%x.%j.out
#SBATCH --partition=standard
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=41
#SBATCH --time=1:30:00
#SBATCH --account=surint
#SBATCH --mail-user egrant@nlr.gov
#SBATCH --mail-type BEGIN,END,FAIL
module load conda
module load PrgEnv-cray
module load cray-mpich/8.1.28
export PYTHONNOUSERSITE=1
export TMPDIR=/scratch/egrant/sc_tmp/

conda activate /projects/surint/campd_spheres/national_analysis/environment_folder/h2i_env_cray

srun -N 4 --ntasks-per-node=41  /projects/surint/campd_spheres/national_analysis/environment_folder/h2i_env_cray/bin/python /projects/surint/campd_spheres/national_analysis/software/nice_us/nice/simulation/run_h2i_ep.py wind solar --library_subdir h2i_sweep_0 --driver_subset_desc subset0 --iprint_setting 0 --debug_print 0 --verbose 1 --overwrite_recorder 1 --max_iter_slc 50