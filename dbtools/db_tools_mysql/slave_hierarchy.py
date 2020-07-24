#!/usr/local/bin/python2.7

#description:Find and print replication hierarchy tree of MySQL subordinates.
#version=1.0
#modify:

import getopt, sys
import MySQLdb
import ConfigParser
import re
import traceback

user_name="db_admin"
user_pass="BZs*gIyVeH4o0q!f"
user_port=3306
user_host=""

def usage():
    print """
        usage:scriptname.py -u root -p root  -P 3306 -H 192.168.7.1
        --host=hostname|-H hostname
        --user=username|-u username
        --password=password|-p password
        --port=port|-P port
        --help|-h  print this
    """

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hH:P:u:p:", ["help", "host=","user=","password=","port="])
    except getopt.GetoptError, err:
        print str(err) 
        usage()
        sys.exit(2)
    if opts:
        global user_name
        global user_pass
        global user_port
        global user_host
        for o, a in opts:
            if o in  ("-u","--user"):
                user_name = a
            elif o in ("-h", "--help"):
                usage()             
                sys.exit()
            elif o in ("-P", "--port"):
                user_port=int(a)
            elif o in ("-p","--password"):
                 user_pass=a
            elif o in ("-H","--host"):
                 user_host=a
            else:
                 usage()



#mysql connect and execute and return the result

def mysql_conn(user_host,user_name,user_pass,user_port,user_sql):
    try:
        conn=MySQLdb.connect(host=user_host,user=user_name,passwd=user_pass,port=user_port,connect_timeout=10)
    except:
        print user_host,"connection error"
	print traceback.print_exc()
        return -1
    cursor=conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    try:    
        cursor.execute(user_sql)
        rows = cursor.fetchall ()
        cursor.close ()
        conn.close ()
        return rows
    except:
        print user_sql ,"error"
        return -1 


#select binlog dump subordinate
def subordinate_process(user_host,user_name,user_pass,user_port,user_sql="show processlist"):
    subordinate_process=[]
    results=mysql_conn(user_host,user_name,user_pass,user_port,user_sql)
    if results==-1:
        pass   
    else: 
        for row in results:
            if re.match(r".*Binlog Dump.*",row['Command']):
                subordinate_host=row['Host'].split(':')
                if subordinate_host[0]!="127.0.0.1" and subordinate_host[0]!=user_host:
                     subordinate_process.append(subordinate_host[0])
    return subordinate_process
    
  
#Find main is not Exception Handling  
def select_main(user_host,user_name,user_pass,user_port,user_sql="show subordinate status",result_host=[]): 
    results=mysql_conn(user_host,user_name,user_pass,user_port,user_sql)  
    print results
    if results==-1:
        return result_host  
    else:
        for row in results:
            if row[1] and row[10]=='Yes': 
                result_host.append(row[1])
                if len(result_host)>3:
                    if result_host[-1]==result_host[-3]:
                        break
                select_main(row[1],user_name,user_pass,user_port)
        return result_host

       
#main relay subordinate Recursive
def mrs_Recursive(user_host,user_name,user_pass,user_port,second_host='',rank=1,space_null=' '):
    results=mysql_conn(user_host,user_name,user_pass,user_port,user_sql="show subordinate status") 
    if results==-1:
        pass
    elif results:
        for row in results:
            print "                              "
            print space_null*rank,user_host,"(","%s,%s,%s,%s,%s,%s" % (row[1],row[5],str(row[21])[-3:],row[10],row[11],row[32]),")"
    else:
        print space_null*rank,user_host
    relay_host=subordinate_process(user_host,user_name,user_pass,user_port)
    if second_host:
        relay_host.remove(second_host)
        second_host=''
    for host_item in relay_host:
        rank+=3  
        subordinate_host=subordinate_process(host_item,user_name,user_pass,user_port)
        if(subordinate_host):
            mrs_Recursive(host_item,user_name,user_pass,user_port,second_host,rank)
        else:
            results=mysql_conn(host_item,user_name,user_pass,user_port,user_sql="show subordinate status")
            if results==-1:
                pass
            else:
                for row in results:
		    main_uuid=row['Main_UUID']
		    gtid_exec=row['Executed_Gtid_Set'].split('\n')
		    for i in gtid_exec:
		    	i=i.split(':')
		    	if main_uuid==i[0]:
				gtid_exec=int(i[1].split('-')[-1].split(',')[0])
		    if row['Retrieved_Gtid_Set']:
		    	gtid_rec=row['Retrieved_Gtid_Set'].split(':')[1].split('-')[-1]
		    	gtid_diff=int(gtid_rec)-gtid_exec
		    else:
			gtid_diff=0
                    print space_null*rank,host_item,"(","%s,%s,%s,%s,%s,%s,%s" % (row['Main_Host'],row['Relay_Main_Log_File'],row['Exec_Main_Log_Pos'],gtid_diff,row['Subordinate_SQL_Running'],row['Subordinate_SQL_Running'],row['Seconds_Behind_Main']),")"
        rank-=3  

main()
results=mysql_conn(user_host,user_name,user_pass,user_port,"show subordinate status")
if results:
    for row in results:
        if row[10]=='Yes':
             main_host=select_main(user_host,user_name,user_pass,user_port)
        else:
             main_host=[]    
             main_host.append(user_host)
else:
     main_host=[]
     main_host.append(user_host)
if not main_host:
    usage()
    sys.exit()  
if len(main_host)>2: 
    mrs_Recursive(main_host[-1],user_name,user_pass,user_port,second_host=main_host[-2])
    mrs_Recursive(main_host[-2],user_name,user_pass,user_port,second_host=main_host[-1])
else:
    mrs_Recursive(main_host[-1],user_name,user_pass,user_port)
