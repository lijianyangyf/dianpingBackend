import Database
import jwt
import time
import os
secret_key = "salt256"
algorithm = "HS256"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMGREPO_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../imgRepo"))

def checkToken(token):
    db=Database.Database()
    response={}
    ID=""
    password=""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        ID = payload.get("ID")
        password = payload.get("password")
        db.connect()
        with Database.Redislock(Database.rcli,f"admin:{ID}"):
            response=db.execute_query("select * from Admin where ID=%(ID)s and password=%(password)s",{"ID":ID,"password":password})
        db.disconnect()
    except Exception as e:
        print(e)
        raise
    if response is not None:
        return {"code": 200}
    else:
        return {"code": 997}

#@21 后台用户信息获取函数(老唐版)————OK
def getUserList(userName,nickName,status,numPerPage,pageIndex,token):
    db=Database.Database()
    response={}
    userName = str(userName) if userName is not None else ""
    nickName = str(nickName) if nickName is not None else ""
    state = str(status) if status is not None else ""
    numPerPage_int = int(numPerPage)
    pageIndex_int = int(pageIndex)
    numPerPage = str(numPerPage) if numPerPage else "10"
    pageIndex = str(pageIndex) if pageIndex else "1"
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        where_conditions = []
        if userName and userName != "":
            where_conditions.append(f"userName = '{userName}'")
        if nickName and nickName != "":
            where_conditions.append(f"nickName = '{nickName}'")
        if state and state != "全部":
            where_conditions.append(f"state = '{state}'")
        where_clause = ""
        if where_conditions:
            where_clause = "where " + " and ".join(where_conditions)
        else:
            where_clause = ""
        base_query = f"select userName, nickName, state, avatarUrl from User {where_clause}"
        offset = (pageIndex_int - 1) * numPerPage_int
        paginated_query = base_query + f" limit {numPerPage_int} offset {offset}"
        response = db.execute_query(paginated_query)
        response_rows = db.execute_query(f"select count(*) as total_rows from User {where_clause}")
        db.disconnect()
        total_rows = 0
        if response_rows and len(response_rows) > 0:
            if isinstance(response_rows[0], tuple):
                total_rows = response_rows[0][0] if len(response_rows[0]) > 0 else 0
            elif isinstance(response_rows[0], dict):
                total_rows = response_rows[0].get("total_rows", 0)
            else:
                try:
                    total_rows = int(response_rows[0])
                except:
                    total_rows = 0
        totalPageNum = total_rows // numPerPage_int
        if total_rows % numPerPage_int > 0:
            totalPageNum += 1
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getUserList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getUserList: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        userList = []
        if response and len(response) > 0:
            for row in response:
                if isinstance(row, dict):
                    user = {
                        "userName": str(row.get("userName")),
                        "nickName": str(row.get("nickName")),
                        "status": str(row.get("state")),
                        "avatarUrl": str(row.get("avatarUrl"))
                    }
                else:
                    user = {
                        "userName": str(row[0]) if len(row) > 0 else "",
                        "nickName": str(row[1]) if len(row) > 1 else "",
                        "status": str(row[2]) if len(row) > 2 else "",
                        "avatarUrl": str(row[3]) if len(row) > 3 else ""
                    }
                userList.append(user)
        return {"code":200, "data": {"userList":userList, "totalPageNum":totalPageNum, "pageIndex":pageIndex}}
    else:
        return {"code":999}
    
#@22 后台重置用户密码函数(老唐版)————OK
def retSetPassword(userName, token):
    db=Database.Database()
    response={}
    newPassword = "123456"
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("update User set password=%(newPassword)s where userName=%(userName)s",{"newPassword":newPassword, "userName":userName})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"retSetPassword: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"retSetPassword: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200, "class": {"newPassword": newPassword}}
    else:
        return {"code":999, "msg":"用户密码重置失败"}
    
#@23 后台冻结用户账号函数(老唐版)————OK
def freezeAccount(userName, token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("update User set state='冻结' where userName=%(userName)s",{"userName":userName})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"freezeAccount: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"freezeAccount: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"用户账号冻结失败"}
    
#@24 后台解冻用户账号函数(老唐版)
def defrostAccount(userName, token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("update User set state='启用' where userName=%(userName)s",{"userName":userName})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"freezeAccount: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"freezeAccount: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"用户账号解冻失败"}