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
    
#@32 后台获取管理员列表函数(老唐版)
def getAdminList(adminID,name,permission,numPerPage,pageIndex,token):
    db=Database.Database()
    response={}
    adminID = str(adminID) if adminID is not None else ""
    name = str(name) if name is not None else ""
    permission = str(permission) if permission is not None else ""
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
        if adminID and adminID != "":
            where_conditions.append(f"ID = '{adminID}'")
        if name and name != "":
            where_conditions.append(f"name = '{name}'")
        if permission and permission != "":
            where_conditions.append(f"authority = '{permission}'")
        where_clause = ""
        if where_conditions:
            where_clause = "where " + " and ".join(where_conditions)
        else:
            where_clause = ""
        base_query = f"select ID, name, authority as permission, avatarUrl from Admin {where_clause}"
        offset = (pageIndex_int - 1) * numPerPage_int
        paginated_query = base_query + f" limit {numPerPage_int} offset {offset}"
        response = db.execute_query(paginated_query)
        response_rows = db.execute_query(f"select count(*) as total_rows from Admin {where_clause}")
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
        print(f"getAdminList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getAdminList: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        adminList = []
        if response and len(response) > 0:
            for row in response:
                if isinstance(row, dict):
                    admin = {
                        "ID": row.get("ID"),
                        "name": row.get("name"),
                        "permission": row.get("permission"),
                        "pictureUrl": row.get("pictureUrl")
                    }
                else:
                    admin = {
                        "ID": row[0] if len(row) > 0 else "",
                        "name": row[1] if len(row) > 1 else "",
                        "permission": row[2] if len(row) > 2 else "",
                        "pictureUrl": row[3] if len(row) > 3 else ""
                    }
                adminList.append(admin)
        return {"code":200, "data": {"adminList":adminList, "totalPageNum":int(totalPageNum), "pageIndex":int(pageIndex)}}
    else:
        return {"code":999, "msg":"管理员列表获取失败"}
    
#@33 后台重置管理员密码函数(老唐版)
def resetPassword(ID,token):
    db=Database.Database()
    response={}
    newPassword = "114514"
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("update Admin set password=%(newPassword)s where ID=%(ID)s",{"newPassword":newPassword, "ID":ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"resetPassword: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"resetPassword: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200, "data": {"newPassword": newPassword}}
    else:
        return {"code":999, "msg":"管理员密码重置失败"}
    
#@34 后台删除管理员函数(老唐版)
def deleteAdmin(ID,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("delete from Admin where ID=%(ID)s",{"ID":ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"deleteAdmin: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"deleteAdmin: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"管理员删除失败"}
    
#@35 后台新增管理员函数(老唐版)
def addAdmin(name,token):
    db=Database.Database()
    response={}
    password = "114514"
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("insert into Admin (password,name,authority) values (%(password)s,%(name)s,普通管理员)",{"password":password,"name":name})
        response_id = db.execute_query("select ID from Admin where name=%(name)s and password=%(password)s",{"name":name,"password":password})
        db.disconnect()
        print(response)
        print(response_id)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"addAdmin: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"addAdmin: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None and response_id is not None:
        if isinstance(response_id, dict):
            ID = str(response_id.get("ID"))
        else:
            ID = str(response_id[0]) if len(response_id) > 0 else ""
        return {"code":200, "data": {"ID":ID, "password":password}}
    else:
        return {"code":999, "msg":"管理员新增失败"}