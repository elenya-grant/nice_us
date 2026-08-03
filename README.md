# nice_us

Repo for loading, analyzing, and mapping EGridData


1. Install from source:

```bash
git clone https://github.com/elenya-grant/nice_us.git
cd nice_us


conda create --name nice python=3.11 -y
conda activate nice
conda install geopandas

pip install -e ".[all]"

pre-commit install

```

2. Download necessary data by following the instructions in the `data_folder` README.md
