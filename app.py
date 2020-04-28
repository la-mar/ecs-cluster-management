# isort:skip_file
import ssm  # noqa

import logging

from chalice import Chalice, Rate
import boto3

import loggers
from ecs import ClusterManager
from util import raise_for_status

loggers.config()

app_name = "ecs-cluster-management"

logger = logging.getLogger()

app = Chalice(app_name=app_name)

ecs = boto3.client("ecs")


@app.schedule(Rate(10, unit=Rate.MINUTES), name="check-agents")
def check_agents(event):

    response = ecs.list_clusters()
    raise_for_status(response)
    clusters = response["clusterArns"]

    for cluster in clusters:
        ClusterManager(cluster).check_agents()
