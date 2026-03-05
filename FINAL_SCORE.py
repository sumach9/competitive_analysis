"""
FFP Smart MVP — Final Score Entrypoint
=======================================
Delegates all scoring computation to modules/Scoring_Engine.py.
This file exists as the stable interface for main.py / api.py.
"""
from modules import Scoring_Engine
from typing import Dict


def get_final_scores(startup_data: Dict) -> Dict:
    """
    Run the full composite scoring pipeline and return the final report.

    Parameters
    ----------
    startup_data : dict
        Flat company data dict as loaded from data/sample_startup.json
        (or submitted via the API).

    Returns
    -------
    dict
        Full composite result with composite_score, suitability_label,
        pillar_results, and metadata.
    """
    return Scoring_Engine.run_scoring_pipeline(startup_data)


if __name__ == "__main__":
    from utils.json_io import read_json_input, write_json_output
    data = read_json_input()
    final_report = get_final_scores(data)
    write_json_output(final_report)
