import json
from flask import render_template, request, jsonify, g, current_app, redirect, url_for
from dacapo.experiments import RunConfig
from flask_login.utils import login_required
from dashboard import socketio
from dashboard.nextflow import Nextflow

from .blue_print import bp
from .helpers import (
    get_checklist_data,
    get_evaluator_score_names,
)
from dacapo import train
from dacapo.options import parse_options

import itertools

from dacapo.plot import plot_runs
import time


@bp.route("/plot", methods=["POST"])
def plot():
    if request.method == "POST":
        plot_info = request.json
        return plot_runs(
            plot_info["runs"],
            validation_scores=plot_info["scoreNames"],
            higher_is_betters=plot_info["higherIsBetters"],
            plot_losses=plot_info["plotLosses"],
            return_json=True,
        )


@bp.route("/runs", methods=["GET", "POST"])
@login_required
def get_runs():
    if request.method == "GET":
        context = get_checklist_data()
        return render_template("dacapo/runs.html", **context)
    if request.method == "POST":
        request_data = request.json

        config_store = current_app.config["stores"].config
        run_config_names = config_store.retrieve_run_config_names(
            task_names=request_data["tasks"],
            datasplit_names=request_data["datasplits"],
            architecture_names=request_data["architectures"],
            trainer_names=request_data["trainers"],
        )
        run_configs = [
            config_store.retrieve_run_config(run_name) for run_name in run_config_names
        ]
        runs = [
            {
                "name": run_name,
                "task_config_name": run_config.task_config.name,
                "datasplit_config_name": run_config.datasplit_config.name,
                "architecture_config_name": run_config.architecture_config.name,
                "trainer_config_name": run_config.trainer_config.name,
                "evaluator_score_names": get_evaluator_score_names(
                    run_config.task_config.name
                ),
                "neuroglancer_link": url_for(".visualize.training", run=run_name),
            }
            for run_name, run_config in zip(run_config_names, run_configs)
        ]
        return jsonify(runs)

    return render_template("dacapo/runs.html")


@bp.route("/apply_config", methods=["GET"])
def apply_config():
    if request.method == "GET":
        return render_template("dacapo/apply_config.html")

    return render_template("dacapo/apply_config.html")


@bp.route("/start_runs", methods=["POST"])
def start_runs():
    if request.method == "POST":
        config_json = request.json
        config_store = current_app.config["stores"].config
        for run in config_json.pop("runs"):
            for i in range(int(config_json["repetitions"])):
                run_config_name = ("_").join(
                    [
                        run["task_config_name"],
                        run["datasplit_config_name"],
                        run["architecture_config_name"],
                        run["trainer_config_name"],
                    ]
                ) + f"__{i}"

                run_config = RunConfig(
                    name=run_config_name,
                    task_config=config_store.retrieve_task_config(
                        run["task_config_name"]
                    ),
                    architecture_config=config_store.retrieve_architecture_config(
                        run["architecture_config_name"]
                    ),
                    trainer_config=config_store.retrieve_trainer_config(
                        run["trainer_config_name"]
                    ),
                    datasplit_config=config_store.retrieve_datasplit_config(
                        run["datasplit_config_name"]
                    ),
                    repetition=0,
                    num_iterations=int(config_json["num_iterations"]),
                    validation_interval=int(config_json["validation_interval"]),
                )

                try:
                    config_store.store_run_config(run_config)
                    nextflow = Nextflow(g.user_info)
                    params_text = {
                        "run_name": run_config_name,
                        "cpus": 5,
                        "options": parse_options()
                    }
                    nextflow.launch_workflow(
                        params_text,
                        config_json["chargegroup"],
                        config_json["compute_queue"],
                    )
                except Exception as e:
                    pass
                    socketio.emit(
                        "message",
                        json.dumps(
                            {
                                "username": g.user_info["username"],
                                "type": "Error",
                                "message": str(e),
                            }
                        ),
                    )

                # train(run_config_name)

    return jsonify({"success": True})
