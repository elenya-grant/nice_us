from pathlib import Path

import numpy as np
import pandas as pd
from attrs import define, field
from h2integrate.core.model_baseclasses import CostModelBaseClass, CostModelBaseConfig
from h2integrate.core.utilities import merge_shared_inputs


@define(kw_only=True)
class CustomGridCostModelConfig(CostModelBaseConfig):
    """Configuration for the grid cost model.

    Attributes:
        interconnection_size: Maximum power capacity for grid connection in kW
        interconnection_capex_per_kw: Capital cost per kW of interconnection ($/kW)
        interconnection_opex_per_kw: Annual O&M cost per kW of interconnection ($/kW/year)
        fixed_interconnection_cost: One-time fixed cost regardless of size ($)
        data_directory: Directory where all the grid data files are saved.
    """

    interconnection_size: float = field()  # kW
    interconnection_capex_per_kw: float = field()  # $/kW
    interconnection_opex_per_kw: float = field()  # $/kW/year
    fixed_interconnection_cost: float = field()  # $
    data_directory: Path = field()  # Directory where all the grid data files are saved.


class CustomGridCostModel(CostModelBaseClass):
    """
    An OpenMDAO component that computes costs for grid connections.

    This component handles:
    - CapEx based on interconnection size ($/kW)
    - OpEx based on interconnection size ($/kW/year)
    - Variable costs for electricity purchases (buy mode)
    - Revenue from electricity sales (sell mode)
    - Support for time-varying electricity prices

    This model is compatible with time steps ranging from 5-minutes to 1-hour.

    """

    _time_step_bounds = (
        300,
        3600,
    )  # (min, max) time step lengths (in seconds) compatible with this model

    def setup(self):
        self.config = CustomGridCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost"),
            additional_cls_name=self.__class__.__name__,
        )
        super().setup()

        # Common input for sizing costs
        self.add_input(
            "interconnection_size",
            val=self.config.interconnection_size,
            units="kW",
            desc="Interconnection capacity for cost calculation",
        )

        # plant code
        self.add_input(
            "plant_code",
            val=0.0,
            shape=1,
            units="unitless",
            desc="Plant code for the grid interconnection point",
        )

        self.add_input(
            "electricity_out",
            val=0.0,
            shape=self.n_timesteps,
            units="kW",
            desc="Electricity flowing out of grid (buying from grid)",
        )

        self.add_input(
            "electricity_sold",
            val=0.0,
            shape=self.n_timesteps,
            units="kW",
            desc="Electricity flowing into grid (selling to grid)",
        )

        self.add_output(
            "electricity_buy_price",
            shape=self.n_timesteps,
            units="USD/(kW*h)",
            desc="Price to buy electricity from grid",
        )
        self.add_output(
            "gross_electricity_cost",
            shape=1,
            units="USD",
            desc="Total electricity cost for buying from the grid",
        )
        self.add_output(
            "electricity_sell_price",
            shape=self.n_timesteps,
            units="USD/(kW*h)",
            desc="Price to sell electricity to grid",
        )
        self.add_output(
            "gross_electricity_revenue",
            shape=1,
            units="USD",
            desc="Total electricity revenue from selling to the grid",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # load correct price file for the facility from data directory
        price_file = (
            self.config.data_directory
            + f"/{int(inputs['plant_code'][0])}_2025_price_profile.csv"
        )
        price_data = pd.read_csv(price_file)  # combined day-ahead LMP + capacity value
        price_data["price_data"] = (
            price_data["LMP ($/MWh)"] + price_data["Capacity Payment ($/MWh)"]
        )

        interconnection_size = inputs["interconnection_size"]

        # Capital costs based on interconnection size
        capex_per_kw = self.config.interconnection_capex_per_kw
        fixed_cost = self.config.fixed_interconnection_cost
        outputs["CapEx"] = (interconnection_size * capex_per_kw) + fixed_cost

        # Fixed operating costs based on interconnection size
        opex_per_kw = self.config.interconnection_opex_per_kw
        outputs["OpEx"] = interconnection_size * opex_per_kw

        # Variable operating costs (positive cost for buying, negative for selling)
        varopex = np.zeros(self.plant_life)

        # Add buying costs if buy price is configured
        # if self.config.electricity_buy_price is not None:
        buy_price = price_data["price_data"].values / 1000  # $/MWh to $/kWh
        outputs["electricity_buy_price"] = buy_price
        # Scalar or per-timestep: same cost each year
        varopex += np.sum((self.dt / 3600) * inputs["electricity_out"] * buy_price)
        outputs["gross_electricity_cost"] = np.sum(
            (self.dt / 3600) * inputs["electricity_out"] * buy_price
        )

        # Add selling revenue if sell price is configured
        # if self.config.electricity_sell_price is not None:
        sell_price = price_data["price_data"].values / 1000  # $/MWh to $/kWh
        outputs["electricity_sell_price"] = sell_price
        varopex -= np.sum((self.dt / 3600) * inputs["electricity_sold"] * sell_price)
        outputs["gross_electricity_revenue"] = np.sum(
            (self.dt / 3600) * inputs["electricity_sold"] * sell_price
        )

        outputs["VarOpEx"] = varopex
