from GenX.tool_logic.resources import classify_resource


def test_canonical_classifier_handles_divergent_cases():
    cases = {
        "natural_gas_cc_new": "Natural Gas",
        "combined_cycle": "Natural Gas",
        "combustion_turbine": "Natural Gas",
        "petroleum": "Natural Gas",
        "oil_generator": "Natural Gas",
        "distributed_generation": "Solar",
        "utilitypv": "Solar",
        "battery_storage": "Battery",
        "hydroelectric": "Hydro",
        "wind_onshore": "Wind",
        "biomass": "Biomass",
        "load_dr": "DR",
        "resource_dr_case": "DR",
        "coal": "Coal",
        "nuclear": "Nuclear",
        "unrecognized_technology": "Other",
        "Total": "Other",
    }
    for resource, expected in cases.items():
        assert classify_resource(resource) == expected


def test_classifier_is_case_and_whitespace_tolerant():
    assert classify_resource("  COMBINED_CYCLE_CC_NEW  ") == "Natural Gas"
    assert classify_resource(" Distributed_Generation_PV ") == "Solar"
