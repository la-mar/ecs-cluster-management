from __future__ import annotations

import logging
import random
from datetime import datetime
from functools import cached_property
from typing import Dict, List, Tuple, TypeVar

import boto3
import humanize
import pytz
from util import raise_for_status, utcnow
from util.iterables import query, reduce

logger = logging.getLogger(__name__)

ec2 = boto3.resource("ec2")
Instance = TypeVar("Instance", bound=ec2.Instance)  # type: ignore


class ContainerInstance:
    def __init__(
        self,
        arn: str,
        status: str,
        ec2id: str,
        agent_connected: bool,
        registered_at: datetime = None,
        details: dict = None,
    ):
        self.arn = arn
        self.status = status
        self.ec2id = ec2id
        self.registered_at = (
            registered_at.astimezone(pytz.UTC) if registered_at else registered_at
        )
        self.agent_connected = agent_connected
        self._details = details or {}

    def __repr__(self):
        return (
            f"{self.short_id}: "
            + f"{self.status} agent={str(self.agent_connected).upper()} "
            + f"uptime={self.uptime}"
        )

    @property
    def id(self):
        return str(self.arn).split("/")[-1]

    @property
    def short_id(self):
        return str(self.arn).split("/")[-1][:8]

    @property
    def ipv4(self) -> str:
        return reduce(  # type: ignore
            [
                x["value"]
                for x in query("attachments.0.details", self._details)
                if x["name"] == "privateIPv4Address"
            ]
        )

    @property
    def uptime_seconds(self) -> float:
        return (utcnow() - self.registered_at).total_seconds()

    @property
    def uptime(self) -> str:
        return humanize.naturaldelta(self.uptime_seconds)

    @property
    def ec2_instance(self) -> Instance:
        return ec2.Instance(self.ec2id)
        # dir(inst)
        # inst.terminate()

    def terminate(self) -> Tuple[str, str]:
        instance = self.ec2_instance
        response = instance.terminate()
        raise_for_status(response)
        state = query("TerminatingInstances.0.CurrentState.Name", response)
        logger.info(f"terminated {instance.id}: state={state}")
        return instance.id, state

    def dict(self) -> Dict:
        d: Dict = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        d["id"] = self.id
        d["uptime_seconds"] = self.uptime_seconds
        d["ipv4"] = self.ipv4
        return d

    @classmethod
    def from_response(cls, details: Dict) -> ContainerInstance:
        return cls(
            arn=query("containerInstanceArn", details),
            status=query("status", details),
            ec2id=query("ec2InstanceId", details),
            registered_at=query("registeredAt", details),
            agent_connected=query("agentConnected", details),
            details=details,
        )


class ClusterManager:
    def __init__(self, cluster: str, client: boto3.client = None):
        """ Get details about and issue various commands to an ECS cluster

        Arguments:
            cluster {str} -- cluster name or arn

        Keyword Arguments:
            client {boto3.client} -- instance of boto3.client('ecs') (default: None)
        """

        self.cluster_name = cluster.split("/")[-1] if "/" else cluster
        self.client = client or boto3.client("ecs")
        details = self._cluster_details
        self.arn = query("clusterArn", details)
        self.instance_count = query("registeredContainerInstancesCount", details)
        self.services = query("activeServicesCount", details)
        self.tasks = query("runningTasksCount", details)

    def __repr__(self):
        agents = self.agent_status["connected"]
        return (
            f"{self.cluster_name}: instances={self.instance_count} "
            + f"services={self.services} tasks={self.tasks} agents={agents}"
        )

    def __iter__(self):
        for instance in self.instances:
            yield instance

    @property
    def agent_status(self) -> Dict[str, int]:
        connected = sum([inst.agent_connected for inst in self.instances])
        return {"connected": connected, "disconnected": self.instance_count - connected}

    @cached_property
    def _cluster_details(self) -> Dict:
        response = self.client.describe_clusters(clusters=[self.cluster_name])
        raise_for_status(response)
        cluster: Dict = reduce(query("clusters", response))  # type: ignore
        return cluster

    @cached_property
    def _container_instance_arns(self) -> List[str]:
        response = self.client.list_container_instances(cluster=self.cluster_name)
        raise_for_status(response)
        return query("containerInstanceArns", response) or []

    @cached_property
    def instances(self) -> List[ContainerInstance]:
        response = self.client.describe_container_instances(
            cluster=self.cluster_name, containerInstances=self._container_instance_arns
        )
        raise_for_status(response)
        instances = query("containerInstances", response) or []
        return [ContainerInstance.from_response(ins) for ins in instances]

    def check_agents(self):
        targets = [x for x in self.instances if not x.agent_connected]
        target_ct = len(targets)

        if target_ct:
            msg = f"({self.cluster_name}): {target_ct} "
            if target_ct == 0:
                msg += "agent is disconnected"
            else:
                msg += "agents are disconnected"

            logger.info(msg, extra={"targets": [x.dict() for x in targets]})
            target = random.choice(targets)
            self.terminate_instance(target)
        else:
            logger.info(f"({self.cluster_name}): all agents are connected")

    def terminate_instance(self, target: ContainerInstance):
        instance_id, state = target.terminate()
        logger.warning(
            f"terminated {instance_id=} {state=} uptime={target.uptime}",
            extra=target.dict(),
        )
