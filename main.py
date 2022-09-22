import logging
import os
import sys

import requests
from tencentcloud.common import credential
from tencentcloud.common.common_client import CommonClient
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
# from tencentcloud.lighthouse.v20200324 import lighthouse_client, models

from telegram import Bot

log_level = os.getenv("log_level", "info")  # info, warning, debug
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='%(asctime)s <%(filename)s:%(lineno)d:%(funcName)s> [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(log_level.upper())


class tencentcloud:
    def __init__(self, ak, sk, region, credtype="ak"):
        self.ak = ak
        self.sk = sk
        self.region = region
        # logger.debug("%s ,%s ,%s,%s"%(ak,sk,region,credtype))
        if credtype == "ak":
            self.cred = credential.Credential(ak, sk)
        elif credtype == "cvmrole":
            self.cred = credential.CVMRoleCredential()

    def tk_client(self, service, region, version="2017-03-12"):
        httpProfile = HttpProfile()
        # 域名首段必须和下文中CommonClient初始化的产品名严格匹配
        httpProfile.endpoint = service + ".tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        # 实例化要请求的common client对象，clientProfile是可选的。
        common_client = CommonClient(service, version, self.cred, region, profile=clientProfile)
        # 接口参数作为json字典传入，得到的输出也是json字典，请求失败将抛出异常
        return common_client
        # print(common_client.call_json("DescribeInstances", {"Limit": 10}))


class Lighthouse(tencentcloud):
    _service = "lighthouse"
    _version = "2020-03-24"

    def DescribeInstances(self):
        logger.debug("get instances list")
        params = {
            "Offset": 0,
            "Limit": 100
        }
        filters = []
        if filters:
            params["Filters"] = filters
        client = self.tk_client(service=self._service, region=self.region, version=self._version)
        try:
            logger.debug("params is :")
            logger.debug(params)
            resp = client.call_json("DescribeInstances", params)
            logger.debug(resp)

            instances = []
            if resp.get("Response").get("InstanceSet"):
                instances = resp.get("Response").get("InstanceSet")
            logger.info("got %s Lighthouse instance" % len(instances))
            return instances
        except TencentCloudSDKException as err:
            logger.error(err)
            exit(1)

    def DescribeInstancesTrafficPackages(self, InstanceIds: list):
        logger.debug("get instances bandwidth packages")
        params = {
            "InstanceIds": InstanceIds,
            "Offset": 0,
            "Limit": 100
        }
        client = self.tk_client(service=self._service, region=self.region, version=self._version)
        try:
            logger.debug("params is :")
            logger.debug(params)
            resp = client.call_json("DescribeInstancesTrafficPackages", params)
            logger.debug(resp)

            InstanceTrafficPackageSet = []
            if resp.get("Response").get("InstanceTrafficPackageSet"):
                InstanceTrafficPackageSet = resp.get("Response").get("InstanceTrafficPackageSet")
            logger.info("got %s TrafficPackage info" % len(InstanceTrafficPackageSet))
            return InstanceTrafficPackageSet
        except TencentCloudSDKException as err:
            logger.error(err)
            exit(2)

    def StopInstances(self, InstanceIds: list):
        logger.debug("stop instances")
        params = {
            "InstanceIds": InstanceIds
        }
        client = self.tk_client(service=self._service, region=self.region, version=self._version)
        try:
            logger.debug("params is :")
            logger.debug(params)
            resp = client.call_json("StopInstances", params)
            logger.debug(resp)
            logger.info("stop %s instance successfully" % len(InstanceIds))

            return resp
        except TencentCloudSDKException as err:
            logger.error(err)
            exit(3)

    def StartInstances(self, InstanceIds: list):
        logger.debug("start instances")
        params = {
            "InstanceIds": InstanceIds
        }
        client = self.tk_client(service=self._service, region=self.region, version=self._version)
        try:
            logger.debug("params is :")
            logger.debug(params)
            resp = client.call_json("StartInstances", params)
            logger.debug(resp)
            logger.info("start %s instance successfully" % len(InstanceIds))

            return resp
        except TencentCloudSDKException as err:
            logger.error(err)
            exit(4)


class Telegram:
    def __init__(self, token):
        self.token = token
        self.bot = Bot(token)
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        try:
            resp = requests.get(url).json()
            if len(resp['result']) > 0:
                chat_id = resp['result'][0]['message']['chat']['id']
                self.chat_id = chat_id
            else:
                logger.error("can't get the Telegram bot chat_id, please send a message to that bot")
        except requests.exceptions.Timeout as e:
            logger.error("get telegram chat_id Timeout: %s" % e)
            exit(5)
        except requests.exceptions.ConnectionError:
            logger.error("get telegram chat_id ConnectionError")
            exit(5)

    def sendMsg(self, msg: str):
        self.bot.send_message(chat_id=self.chat_id, text=msg)


def check_traffic(instances_list: list, traffic_instance_list: list):
    start_instance_list = list()
    stop_instance_list = list()
    notice_list = list()

    GB = 1024 * 1024 * 1024
    TB = 1024 * 1024 * 1024 * 1024

    for ins in instances_list:
        for traffic in traffic_instance_list:
            if ins.get('InstanceId') == traffic.get('InstanceId'):
                if traffic.get('Usage') < threshold and ins.get('InstanceState') == "STOPPED":
                    start_instance_list.append(traffic.get('InstanceId'))
                    d = {
                        'InstanceId': ins.get('InstanceId'),
                        'InstanceName': ins.get('InstanceName'),
                        'TrafficUsed_GB': round(traffic.get('TrafficUsed') / GB, 1),  # Gigabit
                        'TrafficPackageTotal_TB': round(traffic.get('TrafficPackageTotal') / TB, 1),  # Terabyte
                        'Ratio': traffic.get('Usage') * 100,  # percent
                        'Flag': 1  # 1,start; 0, stop
                    }
                    notice_list.append(d)
                elif traffic.get('Usage') >= threshold and ins.get('InstanceState') == "RUNNING":
                    stop_instance_list.append(traffic.get('InstanceId'))
                    d = {
                        'InstanceId': ins.get('InstanceId'),
                        'InstanceName': ins.get('InstanceName'),
                        'TrafficUsed_GB': round(traffic.get('TrafficUsed') / GB, 1),  # Gigabit
                        'TrafficPackageTotal_TB': round(traffic.get('TrafficPackageTotal') / TB, 1),  # Terabyte
                        'Ratio': traffic.get('Usage') * 100,  # percent
                        'Flag': 0  # 1,start; 0, stop
                    }
                    notice_list.append(d)

    return start_instance_list, stop_instance_list, notice_list


def notify(notice_list: list):
    stop = list()
    start = list()
    tg = Telegram(tgtoken)
    # tg.sendMsg('测试消息\n123')

    t = """
-------------------------------------------------
InstanceId  Name  TrafficUsed   Bandwidth Ratio
-------------------------------------------------
"""

    for i in notice_list:
        if i.get('Flag') == 0:
            stop.append(i)
        elif i.get('Flag') == 1:
            start.append(i)

    stop_str = str()
    if len(stop) > 0:
        for s in stop:
            stop_str += f"""
{s.get('InstanceId')} {s.get('InstanceName')} {s.get('TrafficUsed_GB')}G {s.get('TrafficPackageTotal_TB')}T {s.get('Ratio')}
"""
        stop_msg = t + "\n" + stop_str + "\n"
        tg.sendMsg(stop_msg)
    else:
        logger.info("No instance need to stop")

    start_str = str()
    if len(start) > 0:
        for s in start:
            start_str += f"""
{s.get('InstanceId')} {s.get('InstanceName')} {s.get('TrafficUsed_GB')}G {s.get('TrafficPackageTotal_TB')}T {s.get('Ratio')}
"""
        start_msg = t + "\n" + start_str + "\n"
        tg.sendMsg(start_msg)
    else:
        logger.info("No instance need to start")


def tcmain():
    for i in range(len(aks)):
        instances_list = list()
        instance_id_list = list()
        traffic_instance_list = list()

        lt = Lighthouse(aks[i], sks[i], regs[i])
        instances = lt.DescribeInstances()

        for ins in instances:
            ins_dict = {
                "InstanceId": ins.get('InstanceId'),
                "InstanceName": ins.get('InstanceName'),
                "PublicAddresses": ins.get('PublicAddresses'),
                "InstanceState": ins.get('InstanceState'),
                "ExpiredTime": ins.get('ExpiredTime')
            }
            instances_list.append(ins_dict)
            instance_id_list.append(ins.get('InstanceId'))

        traffics = lt.DescribeInstancesTrafficPackages(InstanceIds=instance_id_list)

        for traffic in traffics:
            traffic_dict = {"InstanceId": traffic.get('InstanceId'),
                            "TrafficUsed": traffic['TrafficPackageSet'][0]['TrafficUsed'],
                            "TrafficPackageTotal": traffic['TrafficPackageSet'][0]['TrafficPackageTotal'],
                            "Usage": round(
                                traffic['TrafficPackageSet'][0]['TrafficUsed'] / traffic['TrafficPackageSet'][0][
                                    'TrafficPackageTotal'],
                                4)
                            }
            traffic_instance_list.append(traffic_dict)

        start_instance_list, stop_instance_list, notice_list = check_traffic(instances_list, traffic_instance_list)
        logger.debug(stop_instance_list)
        logger.debug(start_instance_list)
        if len(stop_instance_list) > 0:
            stop = lt.StopInstances(InstanceIds=stop_instance_list)
            logger.debug(stop)
        if len(start_instance_list) > 0:
            start = lt.StartInstances(InstanceIds=start_instance_list)
            logger.debug(start)

        notify(notice_list)


if __name__ == '__main__':
    ak = os.getenv("ak")
    sk = os.getenv("sk")
    tgtoken = os.getenv("tgtoken")
    regs = os.getenv("regs", "ap-hongkong")
    # regs = ["ap-beijing", "ap-chengdu", "ap-guangzhou", "ap-hongkong", "ap-nanjing", "ap-shanghai", "ap-singapore", "ap-tokyo", "eu-moscow", "na-siliconvalley"]
    threshold = float(os.getenv("threshold", 0.98))  # 流量限额，1表示使用到100%关机，默认设置为98%
    aks = ak.split(",")
    sks = sk.split(",")
    regs = regs.split(",")
    if len(ak) == 0 or len(sk) == 0 or len(tgtoken) == 0:
        logger.info("Please set the environment variables !")
        exit(0)
    tcmain()
