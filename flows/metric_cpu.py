# pylint: disable=C0114, C0115, C0116
# coding: utf-8


import logging
import os
import sys
from platform import node, platform

from requests import exceptions
from yaml import YAMLError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from common_modules.config.yaml_config import YamlConfig
from common_modules.data.comparison_operator import OperatorMapping
from common_modules.db.influxdb.conn import InfluxDBConnection
from common_modules.db.mariadb.conn import MariaDBConnection
from common_modules.define.code import EvalType, MetricType

BASE_CONFIG_PATH = "config/config_dev.yaml"
CPU_USAGE_PERCENT = "usage_percent"

# Lazy Query 수행 (1분 이내로 데이터 입수가 가능하지 않을 수도 있으므로)
CPU_QUERY = """SELECT time, host, (100 - usage_idle) as usage_percent
                FROM cpu 
                WHERE time > now() - 2m AND time <= now() - 1m
                GROUP BY host limit 1"""


# TODO MetricCPU Class 정의 필요
class MetricCPU:
    def __init__(
        self,
        metric_type_seq: int = 0,
        metric_name: str = "",
        eval_value: int = 0,
        eval_operator_type_seq: int = 0,
        operator_name: str = "",
    ) -> None:
        self.metric_type_seq = metric_type_seq
        self.metric_name = metric_name
        self.eval_value = eval_value
        self.eval_operator_type_seq = eval_operator_type_seq
        self.operator_name = operator_name

    def __str__(self) -> str:
        return (
            f"MetricCPU(metric_type_seq={self.metric_type_seq}, "
            + f"metric_name={self.metric_name}, "
            + f"eval_value={self.eval_value}, "
            + f"eval_operator_type_seq={self.eval_operator_type_seq}, "
            + f"operator_name={self.operator_name})"
        )


def metric_cpu_flow() -> None:
    logger = logging.getLogger("")

    logger.info("Network: %s. ✅", node())
    logger.info("Instance: %s. ✅", platform())

    try:
        yaml_config = YamlConfig(logger=logger, config_path=BASE_CONFIG_PATH)
    except FileNotFoundError as err:
        logger.error("File Not Found : %s", str(err))
        raise
    except YAMLError as err:
        logger.error("Yaml load Error : %s", str(err))
        raise

    influx = InfluxDBConnection(logger, *yaml_config.get_all_config().get("INFLUXDB").values())

    # TODO InfluxDB 데이터 조회
    with influx.get_resource() as conn:
        try:
            results = conn.query(CPU_QUERY)
        except exceptions.ConnectionError as err:
            logger.error("Connection Error : %s", str(err))
            sys.exit(1)

        metric_points = results.get_points()

    # TODO MariaDB 조회 및 InfluxDB 데이터 평가
    mariadb_connection = MariaDBConnection(
        logger, *yaml_config.get_all_config().get("MARIADB").values()
    )

    results = mariadb_connection.implement_query(MetricType.CPU.value, EvalType.COMMON.value)
    for result in results:
        metric_cpu = MetricCPU(*result)

    alert_host_list = []
    for point in metric_points:
        if OperatorMapping.get(metric_cpu.eval_operator_type_seq).compare(
            point.get("usage_percent"), metric_cpu.eval_value
        ):
            print(point)
            logger.info(point)
            alert_host_list.append(point)

    # TODO Alert 발송
    logger.info("Alert Send!")


if __name__ == "__main__":
    metric_cpu_flow()
