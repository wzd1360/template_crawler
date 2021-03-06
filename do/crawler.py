# -*- coding: utf-8 -*-
from module.config.crawler import CrawlerConfigReader
from module.request.test import HTTPProxiesTest
from module.request.http import HTTPListRequest, HTTPDetailRequest
from module.parser.detail import ParserDetail
from module.parser.list import ParserList
from module.output.rds_to_xlsx import RdsToXlsx
from module.mail.mail import Mail

from util.redis import RedisController
from util.common.logger import LogBase
from util.common.date import Time

class Do(LogBase):

    @staticmethod
    def test():
        '''test
        Request IP test URL to ensure the proxies is enabled.
        '''
        HTTPProxiesTest.test()

    def __init__(self, crawler_name):
        '''Do object
            You may get much info from appointed crawler files.
            It may include request's type, parser's type and
            so on.
        params:
            crawler_name: Crawler's name, which turns to config
            files in ./config folders.
        '''
        # var
        self.crawler_name = crawler_name
        self.req_order    = list()
        self.crawler_conf = dict()

        # log
        self.project_name      = "cw_%s"%crawler_name
        LogBase.__init__(self, self.project_name, "main")
        
        # init
        self.__load__

    def do(self):
        '''do
        Start Process from here. Here is the task list:
        - Gather list data.
        - Gather detail data.
        - Send process email.

        '''
        self.list_res_iter      = self.__req_list__
        self.__parser_list__
        
        self.detail_res_iter    = self.__req_detail__
        self.__parser_detail__

        self.__send_mail__

        self.info("Process End.")

    @property
    def __load__(self):
        '''__load__
        Load crawler config detail info from config files.
        '''
        self.crawler_conf = CrawlerConfigReader.crawler_config(self.crawler_name)
        self.rds          = RedisController(int(self.crawler_conf['sys_conf']['redis_db']), self.project_name)
        self.rds_key      = self.crawler_conf['sys_conf']['redis_key']
        
        self.debug("Here is crawler config => ", **self.crawler_conf)

    @property
    def __req_list__(self):
        '''__req_list__
        Start a request to get list info from list websites/APIs.
        '''

        self.info("Process 1 Start")
        self.p1s = Time.ISO_time_str()

        req = HTTPListRequest(self.crawler_conf, self.project_name)
        yield from req.list_res_iter

        self.p1e = Time.ISO_time_str()

    @property
    def __req_detail__(self):
        '''__req_detail__
        Start a request to get detail info from web page.
        '''

        self.info("Process 2 Start")
        self.p2s = Time.ISO_time_str()

        req = HTTPDetailRequest(self.rds, self.crawler_conf, self.project_name)
        yield from req.detail_res_cookie_iter

        self.p2e = Time.ISO_time_str()


    @property
    def __parser_list__(self):
        '''__parser_list__
        Parse the data from req of list websites/APIs.
        '''
        parser = ParserList(self.project_name, self.list_res_iter, self.crawler_conf, self.rds, self.rds_key)
        parser.save

    @property
    def __parser_detail__(self):
        '''__parser_detail__
        Parse the data from req of detail websites/APIs
        '''
        parser = ParserDetail(self.project_name, self.crawler_name, self.detail_res_iter, self.crawler_conf, self.rds)
        parser.save

    @property
    def __send_mail__(self):
        msg = None
        sub = "Report for {} => {}".format(self.project_name, Time.ISO_date_str())
        
        with open("./constant/crawler_report.tpl") as r:
            msg = r.read()

        msg = msg.format(
            sub=sub, p1s=self.p1s, p1e=self.p1e,
            p2s=self.p2s, p2e=self.p2e            
        )

        attachment = {
            "{}.log".format(
                self.project_name
            ):"./log/{}/{}.log".format(
                self.project_name, Time.now_date_str()
            )
        }

        Mail.send(msg, sub, attachment)

    def rds_to_xlsx(self, file_name, sheet_name):
        '''rds_to_xlsx
        Data from redis database to xlsx file.
        '''
        RdsToXlsx.save(self.rds, file_name, sheet_name)