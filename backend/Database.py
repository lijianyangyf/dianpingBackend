import mysql.connector
from mysql.connector import errorcode,pooling
import redis
import time
import uuid
class Redislock:
    _UNLOCK_SCRIPT = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
    """
    def __init__(self, redis_client,name:str,ttl_ms:int=10000,wait_timeout:int=5,retry_interval:float=0.5):
        self.redis_client = redis_client
        self._key = f"lock:{name}"
        self._ttl_ms = ttl_ms
        self._token=str(uuid.uuid4())
        self._wait_timeout = wait_timeout
        self._retry_interval = retry_interval
        self._unlock = self.redis_client.register_script(self._UNLOCK_SCRIPT)
    def acquire(self):
        deadline = time.time()+self._wait_timeout
        while time.time() < deadline:
            ok = self.redis_client.set(self._key,self._token,nx=True,px=self._ttl_ms)
            if ok:
                return True
            time.sleep(self._retry_interval)
        return False
    def release(self):
        try:
            self._unlock(keys=[self._key], args=[self._token])
        except redis.RedisError:
            raise
    def __enter__(self):
        if not self.acquire():
            raise TimeoutError(f"Failed to acquire lock: {self._key}")
        return self
    def __exit__(self,exc_type,exc,tb):
        self.release()

class Database:
    def __init__(self):
        self.connection = None
    def connect(self):
        try:
            self.connection = db_pool.get_connection()
            print("Connected to MySQL database")
            return self.connection
        except mysql.connector.Error as err:
            print(err)
    def disconnect(self):
        if self.connection:
            self.connection.close()
            print("Disconnected from MySQL database")
    """ input example
        eg1: query: "select columnName1,columnName2 from tableName where circumstanName1=%(cir1Name)s and circumstanName2=%(cir2Name)s"
             params:{"cir1Name":cir1Value,"cir2Name":cir2Value}
        eg2: query: "insert into tableName(columnName1,columnName2) values(%(col1Name)s,%(col2Name)s)"
             params:{"col1Name":col1Value,"col2Name":col2Value}
    """
    def execute_query(self, query, params=None, commit=None):
        try:
            cursor = self.connection.cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            verb = query.strip().split(None, 1)[0].upper()
            is_write = verb in {"INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER", "TRUNCATE"}
            do_commit = commit or is_write
            if is_write:
                if do_commit:
                    self.connection.commit()
                return {"rowcount": cursor.rowcount, "lastrowid": getattr(cursor, "lastrowid", None)}
            else:
                result = cursor.fetchall()
                return result
        except mysql.connector.Error as err:
            try:
                self.connection.rollback()
            except Exception as err:
                print(err)
            return None
        finally:
            cursor.close()
"""
use example:
lock_name=f"user:{user_id}"
with Redislock(rcli,lock_name,ttl_ms):
    db.execute_query(query,params,commit)
"""
db_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    pool_reset_session=True,
    host="localhost",
    user="laotang", #自行修改为自己的用户名
    password="123456", #自行修改为自己的密码
    database="test"
)
rcli = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
def unitTest():
    db=Database()
    userId="user:test"
    db.connect()
    response={}
    with Redislock(rcli,userId):
        response=db.execute_query("select * from user where userName=%(userName)s AND nickName=%(nickName)s",{"userName":"admin","nickName":"ljy"})
    print(response)
    db.disconnect()
