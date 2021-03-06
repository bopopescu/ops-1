#! /usr/bin/python2.7

#Created zolker

import sys
import os
import stat
import socket
import time
import threading
import re
import logging
import copy
import MySQLdb
import subprocess 
import traceback
from warnings import filterwarnings
filterwarnings('ignore', category = MySQLdb.Warning)

#global variables
db_black_list = ["mysql","performance_schema","zjmdmm","information_schema",\
                 "nagiosdmm","xddmm","tcdmm",]
admin_user='db_admin'
admin_passwd='BZs*gIyVeH4o0q!f'
admin_port=3307
admin_host='127.0.0.1'
VERSION='1.0'

##################################
LOG_PREFIX = "/tmp/"
logger_s = None #log for program internal
logger_u = None #log for user
##################################

def run_command(command):
    p = subprocess.Popen(command, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    return p.communicate()


def getLogger(user_log, log_level):
    system_log = "/tmp/mysql-login_YnzAtZxuldXq.log"
    if user_log and user_log.startswith("/"):
        log_dest = user_log
    elif user_log:
        log_dest = LOG_PREFIX + user_log
    else:
        log_dest = None
    logger_s = logging.getLogger("intertal-"+str(VERSION))
    logger_s.setLevel(logging.DEBUG)

    logger_u = logging.getLogger("user-"+str(VERSION))
    logger_u.setLevel(log_level)

    #if path is a dir, exit the program
    if log_dest and os.path.isdir(log_dest):
        print "system log destination(%s) is a dir, not a file!" % log_dest
        sys.exit(-1)
    if log_dest and os.path.isdir(system_log):
        print "user log destination(%s) is a dir, not a file!" % system_log 
        sys.exit(-1)
    #if file not exists, touch it  and it's permisson to 777
    if log_dest and not os.path.exists(log_dest):
        os.mknod(log_dest)
        os.chmod(log_dest, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
    if log_dest and not os.path.exists(system_log):
        os.mknod(system_log)
        os.chmod(system_log, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
    if not log_dest:
        file_handler_u = logging.StreamHandler(sys.stdout)
    else:
        file_handler_u = logging.FileHandler(log_dest)
    print "System log redirect to %s" % system_log
    print "User log redirect to %s" % (log_dest if log_dest else "STDOUT")
    print ""
    file_handler_s = logging.FileHandler(system_log)
    
    formatter_s = logging.Formatter("%(asctime)s - [%(levelname)s] - "+
           "[%(name)s/%(filename)s: %(lineno)d] - %(message)s")
    formatter_u = logging.Formatter("%(message)s")
    file_handler_s.setFormatter(formatter_s)
    file_handler_u.setFormatter(formatter_u)
    logger_s.addHandler(file_handler_s)
    logger_u.addHandler(file_handler_u)
    return logger_s, logger_u


class Connection:

    def __init__(self, *args, **kargs):
        self.args = args
        self.kargs = kargs
        self.kargs['user'] = kargs['user'] if kargs.has_key('user') \
                                           else opts.user
        self.kargs['passwd'] = kargs['passwd'] if kargs.has_key('passwd') \
                                               else opts.passwd
        self.kargs['connect_timeout'] = kargs['connect_timeout'] \
                                        if kargs.has_key('connect_timeout') \
                                        else 5
        # TODO: we need to overwrite other argument. 
        #      such interactive_timeout/wait_tiemout/charset and so on

    def get_connection(self,):
        ret = {'errno':0, 'errmsg':"", 'value':None}
        conn = None

        try:
            # TODO: add a connect retry mechaniam
	    #print self.kargs
            conn = MySQLdb.connect(*self.args, **self.kargs)
            ret['value'] = conn
        except Exception, err:
            ret['errno'] = 1
            ret['errmsg'] = str(err)
        finally:
            return ret

# Wrapper for MySQL connection
def get_conn(*args, **kargs):
    #must *args, **kargs, not args, kargs
    __conn__ = Connection(*args, **kargs)
    return __conn__.get_connection()

def close_connection(conn):
    ret = {'errno':0, 'msg':"close connection success", 'value':None}
    try:
        if conn:
            conn.close()
    except Exception, err:
        ret['errno'] = 1
        ret['msg'] = str(err)
    finally:
        return ret

def close_cursor(cursor):
    ret = {'errno':0, 'msg':"close cursor succuss", 'value':None}
    try:
        if cursor:
            cursor.close()
    except Exception, err:
        ret['errno'] = 1
        ret['msg'] = str(err)
    finally:
        return ret

def exec_sql(conn,sql):
	try:
		cursor=conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute(sql)
		sql_rt=cursor.fetchall()
		rt={}
		rt['status']=0
		rt['result']=sql_rt
		return rt
	except Exception,error:
		rt={}
		rt['status']=-1
		rt['result']='SQL exec Error'
		return rt
def get_all_port():
    try:
        conn=get_conn(user=admin_user,passwd=admin_passwd,host=admin_host,port=admin_port)
        conn=conn['value']
        #sql='select distinct port,product_info,db_role from meitu_db_admin.db_instance_info;'	
        #sql='select  port,host,product_info,db_role from meitu_db_admin.db_instance_info where is_online=1 and db_role=1;'	
        sql='select distinct hostname,port from cmdb.mysql_ins;'
        sql_rt=exec_sql(conn,sql)
        return sql_rt
    except Exception,error:
	    print traceback.print_exc()
	    rt={}
	    rt['status']=-1
	    rt['result']='SQL exec Error'
	    return rt
		
    
def get_slave_ip():
	return 0


#connect = Connect = get_connection


def get_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def get_hour():
    return time.strftime("%Y-%m-%d %H:00:00", time.localtime())

def collect_com_data(host,port):
	conn=get_conn(user=admin_user,passwd=admin_passwd,host=host,port=port)
	com_keys=['Com_delete','Com_insert','Com_update','Com_select']
	conn=conn['value']
	sql='show global status like "%com_%";'
	sql_rt=exec_sql(conn,sql)
	rt={}
	com_rt={}
	if sql_rt['status']!=0:
		return sql_rt
	sql_rt=sql_rt['result']
	for i in sql_rt:
		if i['Variable_name']=='Com_insert':
			com_rt['insert_ops']=int(i['Value'])
		if i['Variable_name']=='Com_update':
			com_rt['update_ops']=int(i['Value'])
		if i['Variable_name']=='Com_delete':
			com_rt['delete_ops']=int(i['Value'])
		if i['Variable_name']=='Com_select':
			com_rt['select_ops']=int(i['Value'])
	rt['status']=0
	rt['result']=com_rt
	return rt
			
#print rt
def main():
    try:
        all_port=get_all_port()
        all_port=all_port['result']
        for i in all_port:
            hostname=i['hostname']
            port=i['port']
            per_com_rt=collect_com_data(hostname,port)
            if per_com_rt['status']==-1:
                continue
            temp_ops=per_com_rt['result']
            cur_time=get_hour()
            sql="replace into cmdb.mysql_hour_ops (port,hostname,day_time,insert_ops,update_ops,delete_ops,select_ops) values (%d,'%s','%s',%d,%d,%d,%d)"%(int(port),hostname,cur_time,temp_ops['insert_ops'],temp_ops['update_ops'],temp_ops['delete_ops'],temp_ops['select_ops'])
            conn=get_conn(user=admin_user,passwd=admin_passwd,host=admin_host,port=admin_port)
            conn=conn['value']
            conn.autocommit(1) 
            rt_sql=exec_sql(conn,sql)
    except Exception,e:
        print traceback.print_exc() 

main()
