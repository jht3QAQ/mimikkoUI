 #!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import os
import sys
import logging
import requests
import hashlib
import datetime
from io import StringIO
from dotenv import dotenv_values

host='https://api1.mimikko.cn'
appid='wjB7LOP2sYkaMGLC'
version='3.4.0'
userAgent='okhttp/3.12.1'

dingtalkUrl=''

class MimikkoUI():
    def __init__(self,username:str,password:str,servantName:str) -> None:
        self.__username=username
        self.__password=password
        self.__servantName=servantName
        
        self.__setLogger()
        self.__getSession()

        self.__logger.info('mimikkoUI签到脚本')

        try:
            self.__getToken()
            self.__getUserOwnInformation()
            self.__getServantList()
            self.__getServantId()
            self.__setDefaultServant()
            self.__getExchangeReward()
            self.__signAndSignInformationV3()
            self.__rollReward()
            self.__receiveMemberLevelWelfare()
        except Exception as e:
            logging.exception(e)

        self.__removeLogger()

    def __setLogger(self) -> None:
        logging.basicConfig(format='[%(asctime)s] [%(levelname)s] %(message)s',datefmt='%H:%M:%S')
        self.__logger = logging.getLogger()
        self.__logger.setLevel(logging.INFO)

        if not os.path.exists('logs'):
            os.mkdir('logs')
        self.__logger.addHandler(logging.FileHandler("logs/%s.log"%datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d %H-%M-%S')))
        self.__loggerFile=StringIO()
        self.__logger.addHandler(logging.StreamHandler(stream=self.__loggerFile))

        def handle_exception(exc_type, exc_value, exc_traceback):
            self.__logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

        sys.excepthook = handle_exception
    
    def __removeLogger(self):
        sys.excepthook = None
        if dingtalkUrl !='':
            response=requests.post(dingtalkUrl,json={
                "msgtype":"text",
                "text":{
                    "content":self.__loggerFile.getvalue()
                }
            }).json()
            assert response['errcode'] == 0 , response['errmsg']

    def __getSession(self) -> None:
        self.__session = requests.Session()
        httpAdapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.__session.mount('', httpAdapter)
        self.__session.headers={
            'cache-control':'no-cache',
            'appid':appid,
            'version':version,
            'accept-encoding':'gzip',
            'user-agent':userAgent
        }

    def __getToken(self) -> None:
        '''获取 token 并在 header 里设置 Authorization'''
        response=self.__session.post(host+'/client/user/LoginWithPayload',json={
            "password":hashlib.sha256(self.__password.encode('utf-8')).hexdigest(),
            "id":self.__username
        },headers={
            'Content-Type':'application/json',
            'accept':'application/json'
        }).json()
        assert response['code'] in ['0'] , response['msg']
        self.__session.headers['Authorization']=response['body']['Token']
        self.__logger.info('UserName: %s'%response['body']['UserName'])
        self.__logger.info('getToken success')

    def __getUserOwnInformation(self) -> None:
        '''获取用户信息'''
        response=self.__session.get(host+'/client/user/GetUserOwnInformation').json()
        assert response['code'] in ['0'] , response['msg']
        self.__logger.info('Level: %d %d/%d'%(response['body']['Value']['Level'],response['body']['Value']['Exp'],response['body']['Value']['MaxExp']))
        self.__logger.info('Coin: %d'%response['body']['Value']['Coin'])
        self.__logger.info('getUserOwnInformation success')

    def __getServantList(self) -> None:
        '''获取助手列表'''
        response=self.__session.get(host+'/client/Servant/GetServantList?startIndex=0&count=120&version=3').json()
        assert response['code'] in ['0'] , response['msg']
        self.__logger.info('servant count: %d'%response['body']['Total'])
        servants:list=response['body']['Items']
        for servant in servants:
            self.__logger.info('ServantName: %s\tLevel:%d %d/%d'%(servant['ServantName'],servant['Level'],servant['Favorability'],servant['MaxFavorability']))
            if servant['ServantName'] == self.__servantName:
                self.__code=servant['code']
        assert self.__code != None  
        self.__logger.info('getServantList success')

    def __getServantId(self) -> None:
        '''获取助手详细信息'''
        response=self.__session.get(host+'/client/love/GetUserServantInstance?code='+self.__code).json()
        assert response['code'] in ['0'] , response['msg']
        self.__logger.info('Energy: %d/%d'%(response['body']['Energy'],response['body']['MaxEnergy']))
        self.__logger.info('getServantId success')

    def __setDefaultServant(self) -> None:
        '''设置默认助手'''
        response=self.__session.get(host+'/client/Servant/SetDefaultServant?code='+self.__code).json()
        assert response['code'] in ['0'] , response['msg'] 
        self.__logger.info('DefaultServant: %s'%self.__servantName)
        self.__logger.info('setDefaultServant success')
    
    def __getExchangeReward(self) -> None:
        '''兑换能量值'''
        response=self.__session.get(host+'/client/love/ExchangeReward?code='+self.__code).json()
        assert response['code'] in ['0','000316'] ,response['msg']
        if response['code'] != '0':
            self.__logger.warning(response['msg'])
        self.__logger.info('getExchangeReward success')

    def __signAndSignInformationV3(self) -> None:
        '''签到'''
        response=self.__session.get(host+'/client/RewardRuleInfo/SignAndSignInformationV3').json()
        assert response['code'] in ['0'] , response['msg']
        self.__logger.info('signInformation: %s %s'%(response['body']['Description'],response['body']['Name']))
        self.__logger.info('signAndSignInformationV3 success')

    def __rollReward(self) -> None:
        '''VIP抽奖'''
        response=self.__session.post(host+'/client/roll/RollReward').json()
        assert response['code'] in ['0','000237'] , response['msg']
        if response['code'] !='0':
            self.__logger.warning(response['msg'])
        self.__logger.info('rollReward success')

    def __receiveMemberLevelWelfare(self) -> None:
        '''VIP能量'''
        response=self.__session.post(host+'/client/mission/ReceiveMemberLevelWelfare').json()
        assert response['code'] in ['0'] , response['msg']
        if response['body']['Value']['success'] == False:
            self.__logger.warning(response['body']['Value']['message'])
        self.__logger.info('receiveMemberLevelWelfare success')

usernames,passwords,servantNames=([],[],[])

if os.path.isfile(".env"):
    config = dotenv_values(".env")
    usernames=eval(config['usernames'])
    passwords=eval(config['passwords'])
    servantNames=eval(config['servantNames'])
    dingtalkUrl=config['dingtalkUrl']

if 'usernames' in os.environ:
    usernames+=eval(os.getenv('usernames'))
if 'passwords' in os.environ:
    passwords+=eval(os.getenv('passwords'))
if 'servantNames' in os.environ:
    servantNames+=eval(os.getenv('servantNames'))
if 'dingtalkUrl' in os.environ and dingtalkUrl == '':
    dingtalkUrl=os.getenv('dingtalkUrl')

accounts=zip(usernames,passwords,servantNames)
for username,password,servantName in accounts:
    MimikkoUI(username,password,servantName)