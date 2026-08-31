from pathlib import Path

import numpy as np
import openmdao.api as om
import pandas as pd
from attrs import define, field
from h2integrate.core.utilities import BaseConfig, merge_shared_inputs

n_timesteps = 8760


@define(kw_only=True)
class CAMPDConfig(BaseConfig):
    """Configuration for the CAMPD model.

    Args:
        data_directory (Path): Directory where all the CAMPD data files are saved.
        eia_923_data (Path): Path to the EIA 923 data file.
        maintenance_nans (int): Number of consecutive NaN values to use for maintenance periods.
            If the number of consecutive NaN values in the CAMPD data is greater than this value,
            it will be considered a maintenance period and the corresponding gross load time steps
            will be set to 0 in the output. All NaN values below this threshold will be set to max
            gross load for the generator. This is to account for missing data in the CAMPD dataset.

    """

    data_directory: Path = field()
    eia_923_data: Path = field()
    maintenance_nans: int = field()


class CAMPDPerformance(om.ExplicitComponent):
    _time_step_bounds = (
        3600,
        3600,
    )  # (min, max) time step lengths (in seconds) compatible with this model

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = CAMPDConfig.from_dict(
            merge_shared_inputs(
                self.options["tech_config"]["model_inputs"], "performance"
            )
        )

        self.add_input(
            "facility_id",
            val=0.0,
            shape=1,
            desc="Facility ID",
        )

        self.add_output(
            "electricity_out",
            shape=n_timesteps,
            units="MW",
            desc="Electricity produced from the facility",
        )

        # read in EIA 923 data here
        self.eia_923_df = pd.read_csv(self.config.eia_923_data)

    def compute(self, inputs, outputs):
        # read csv file using facility_id

        facility_id = int(inputs["facility_id"][0])
        df = pd.read_csv(
            Path(self.config.data_directory) / f"facility_{facility_id}.csv"
        )
        # pull out all the generator IDs for the given facility_id
        generator_ids = df["Unit ID"].unique()

        # make a dictionary to hold the net generation for each generator_id
        net_generation_dict = {}
        # filter the EIA 923 data for the specific facility_id and generator_id
        eia_923_filtered_df = self.eia_923_df[
            self.eia_923_df["facility_id"] == facility_id
        ]
        for gen_id in generator_ids:
            eia_923_filtered_df = eia_923_filtered_df[
                eia_923_filtered_df["generator_id"] == gen_id
            ]

            # take the net generation for the given generator_id
            net_generation = eia_923_filtered_df["net_generation"].values

            # check number of nans in a row in the gross load data for the given generator_id
            # if greater than the maintenance_nans threshold, set the gross load to 0 for those timesteps
            # else set the gross load to max gross load for the generator for those timesteps
            # TODO add code

            # get the gross generation from the df for the given generator_id
            # the rows are individual timesteps, so we need to get the gross generation for each timestep
            gross_generation = df[df["Unit ID"] == gen_id]["Gross Load (MW)"].values

            # calculate total gross generation for the generator
            total_gross_generation = np.sum(gross_generation)

            # calculate the ratio of net generation to gross generation for the generator
            ratio = net_generation / total_gross_generation

            # apply the ratio to the gross generation to get the net generation for each timestep
            net_generation_timestep = gross_generation * ratio

            # add the net generation for the generator to the dictionary
            net_generation_dict[gen_id] = net_generation_timestep

        # sum the net generation for all generators to get the total net generation for the facility
        total_net_generation = np.sum(list(net_generation_dict.values()), axis=0)

        outputs["electricity_out"] = total_net_generation
