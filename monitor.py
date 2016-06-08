#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys,os,re,json,smtplib,time,logging,string
logging.basicConfig(level=logging.DEBUG)
from email.mime.text import MIMEText

class Monitor(object):

    def __init__(self, config_path):
        self.context = {'config_path' : config_path}
        self.position = -1
        self.load_config()

        filename_config = self.context['config']['log_file_syntax']
        police_config = self.context['config']['police']
        handler_config = self.context['config']['handler']

        self.file = eval(filename_config['type'] + '(filename_config)')
        self.police = eval(police_config['type'] + '(police_config)')
        self.handler = eval(handler_config['type'] + '(handler_config)')

    def load_config(self):

        _file_content = "";
        with open(self.context['config_path']) as _file:
            for line in _file.readlines():
                if not line.strip().startswith('#'):
                    _file_content += line
        logging.debug("read config file content : %r" % (_file_content))

        try:
            config = json.loads(_file_content)
        except Exception , e:
            raise ValueError, "config file content error"

        logging.debug("convert config file : %r" % (config))
        self.context['config'] = config;

    def monitor_file(self):
        file_ = None
        file_path = self.file.fullpath()

        while True:
            file_ = open(file_path)
            try:
                if os.access(file_path, os.F_OK):
                    file_ = open(file_path)

                    file_.seek(0, 2)
                    file_size = file_.tell()

                    last = self.position;

                    logging.debug("last_pos %d, file_size %d" % (last, file_size))

                    if last == -1:
                        self.position = file_size
                        continue
                    elif last > file_size:
                        self.position = 0
                        continue
                    else:
                        file_.seek(last)

                    lines = file_.readlines()

                    if lines:
                        self.position = file_.tell()
                        for line in lines:
                            if self.police.handle(line):
                                self.handler.handle({'line':line})
            finally:
                if file_ and not file_.closed:
                    file_.close()
                time.sleep(self.context['config']['monitor_interval'])

class SimpleFile(object):
    def __init__(self, config):
        self.config = config
        self.file_path = config['file_path'] + '/' + self.config['syntax']

    def fullpath(self):
        return self.file_path

class SimpleDateFile(object):
    def __init__(self, config):
        self.config = config

    def fullpath(self):
        file_name = time.strftime(self.config['syntax'],time.localtime(time.time()))
        return self.file_path = config['file_path'] + '/' + file_name

class PatternPolice(object):

    def __init__(self, config):
        self.config = config
        patterns = self.config['handle_line_pattern']
        self.matches = [re.compile(pattern) for pattern in patterns]

    def handle(self, line):

        def _compile(x, y):
            return x or y

        return reduce(_compile, [m.match(line) for m in self.matches])

class MailHandler(object):

    def __init__(self, config):
        self.config = config
        self.lastsend = 0

    def handle(self, context={}):

        cutime = time.time()
        if cutime - self.lastsend <= self.config['send_interval']:
            logging.debug("interval less than %r, ignore" % (self.config['send_interval']))
            return

        mail_from=self.config['mail_from']
        mail_to_list=self.config['mail_to_list']
        mail_host=self.config['mail_to_list']
        mail_user=self.config['mail_user']
        mail_pass=self.config['mail_pass']
        mail_sub=self.format_str(self.config['mail_sub'], context)
        mail_content=self.format_str(self.config['mail_content'], context)

        msg = MIMEText(mail_content,_subtype='plain',_charset='utf-8')  
        msg['Subject'] = mail_sub  
        msg['From'] = mail_from  
        msg['To'] = ";".join(mail_to_list)  
        try:  
            server = smtplib.SMTP()  
            server.connect(mail_host)  
            server.login(mail_user,mail_pass)  
            server.sendmail(mail_from, mail_to_list, msg.as_string())
            self.lastsend = cutime
            server.close()  
            return True  
        except Exception, e:  
            print str(e)  
            return False

    def format_str(self, str, context):
        return str % context

if __name__=='__main__':

    args = sys.argv

    if len(args)<2:
        logging.error('need one config filepath parameter')
        exit(1)
    logging.debug("config filepath is %r" % (args[1]))

    monitor = Monitor(args[1])

    try:
        monitor.monitor_file()
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt, exit!")
