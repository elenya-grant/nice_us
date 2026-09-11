# Workflow for running batch scripts

Kestrel has 2378 nodes. Each node has 104 CPUs and 256 GB of memory. Each CPU is given a "task" when running stuff in parallel. You can run multiple tasks on part of a node, or multiple tasks across multiple nodes. If you're running a simulation that requires less than 256 GB and less than 104 tasks, you should run on the `shared` partition (as long as the expected wall-time is less than 2 hours). The below sections detail how to update the example batch scripts for the two following cases:

1. running a full-node or multi-node batch script (example file is `example_multinode_batch.sh`)
2. running a partial node, multi-cpu batch script (example file is `example_shared_batch.sh`)

But first, theres a few things to update in the batch script regardless of which case you're running.

## Updating SBATCH commands

### SBATCH commands for all cases

The following SBATCH commands should be updated for each user and/or project:
- `--mail-user`: update to your email account associated with the HPC. In the example file, replace `egrant@nlr.gov` with your email account. In the example file, the line is `#SBATCH --mail-user egrant@nlr.gov`
- `--account`: update with the project allocation handle that you're charging for this batch script. replace `surint` with your project allocation handle. In the example file, the line is `#SBATCH --account=surint`


The following SBATCH commands should be updated for each job (regardless of type):
- `--time`: update the expected time to run the simulation. If you think the job will take 1 hour, request at least 1.5 hours. The time format is `HH:MM:SS`, so for a 1 hour time request, set `--time=1:00:00`. For a 30 minute time request, set `--time=30:00`. In the example file, the line is `SBATCH--time=1:15:00`
- `--job-name`: update the job name as something descriptive for you. This job name is used to name the output log file and is also included on the email updates about your job. Replace `example_run` with your job name. In the example file, the line is `#SBATCH --job-name=example_run`.

### SBATCH commands for less than 1 node job

An example of this case is shown in `example_shared_batch.sh`

Below are the SBATCH commands specific to running jobs that require less than 1 full node:

```bash
#SBATCH --partition=shared
#SBATCH --ntasks=21
#SBATCH --mem=64GB
```

If you're running less than 1 node, then you should make sure the `--partition` is `shared`. There may be a time limit on this partition, so probably only submit jobs that are expected to take less than 2 hours. When you're running on a shared node, you have to specify the number of CPUs (or tasks) you want to run. You need multiple CPUs to run simulations in parallel. You need to also specify the memory, this is the memory that is shared across all the CPUs. If I want to run 21 tasks and I think that each task will require about 3 GB of memory, I will need about 64 GB of memory.
- `--ntasks`: update based on the number of parallel simulations you want to run. In the example file, replace `21` with the number of CPUs you need. In the example file, the line is `#SBATCH --ntasks=21`
- `--mem`: update the number of memory you need for all your CPUs in GB. This should not exceed 256GB. In the example file, replace `64` with the gigabytes of memory you need. In the example file, the line is `#SBATCH --mem=64GB`



### SBATCH commands for at least 1 node job

An example of this case is shown in `example_multinode_batch.sh`

Below are example SBATCH commands specific to running jobs that require less than 1 full node:

```bash
#SBATCH --partition=standard
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=78
```

If you're running at least 1 node, then you should make sure the `--partition` is `standard`. There may be a time limit on this partition, so probably only submit jobs that are expected to take less than 8 hours. When you're running on multiple nodes, you have to specify the number of nodes you want to use and the number of tasks (or CPUs) per node you need. You get all 256 GB of memory for each node, so you should specify the number of tasks per node based on the memory you expect each task to require. If I think each task will require about 3.3GB of memory, then take 256/3.3 to get the approximate number of tasks per node you should have (in this case, thats 78 tasks per node). If I have 8 nodes, with 78 tasks per node, then I'm running 624 simulations in parallel.

- `--nodes`: update based on the number of nodes you want to use. In the example file, replace `8` with the number of CPUs you need. In the example file, the line is `#SBATCH --nodes=8`
- `--ntasks-per-node`: update the number of tasks you want to run on each node. This should not exceed 104. In the example file, replace `78` with the number of tasks you want to run on each node. In the example file, the line is `#SBATCH --ntasks-per-node=78`


## Updating the rest of the batch script

For all cases, make sure to update the TMP_DIR to the TMP_DIR in your scratch folder. Replace `egrant` with your hpc username in the line shown below:

```
export TMPDIR=/scratch/egrant/sc_tmp/
```

Depending on if the python script you're running has args, you may need to update those (those will be the last parts of the line that starts with `srun`)

### Updating SRUN command for less than 1 node job
An example of this case is shown in `example_shared_batch.sh`


### Updating SRUN command for at least 1 node job
An example of this case is shown in `example_multinode_batch.sh`
