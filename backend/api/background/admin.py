import Database
import jwt
import time
import os
secret_key = "salt256"
algorithm = "HS256"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMGREPO_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../imgRepo"))

#@16 校验管理员token函数(老唐版)————OK
def checkToken(token):
    db = Database.Database()
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        ID = payload.get("ID")
        password = payload.get("password")
        db.connect()
        response = db.execute_query("select * from Admin where ID=%(ID)s and password=%(password)s", {"ID": ID, "password": password})
        db.disconnect()
    except jwt.ExpiredSignatureError as e:
        print(f"Token 过期: {e}")
        return {"code": 997, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"Token 无效: {e}")
        return {"code": 997, "msg": "Token 无效"}
    except Exception as e:
        print(f"其他错误: {e}")
        return {"code": 997, "msg": f"服务器错误: {str(e)}"}
    if response and len(response) > 0:
        print("验证成功")
        return {"code": 200}
    else:
        print("验证失败")
        return {"code": 997, "msg": "用户不存在或密码错误"}
    
#@17 管理员登录函数(老唐版)————OK
def login(ID,password):
    db=Database.Database()
    db.connect()
    response=db.execute_query("select * from Admin where ID=%(ID)s and password=%(password)s",{"ID":ID,"password":password})
    db.disconnect()
    print(response)
    payload ={
        "ID":ID,
        "password":password,
        "exp":time.time()+3600
    }
    token = jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm
    )
    if response is not None:
        return {"code": 200, "data": {"token": token}}
    else:
        return {"code": 999, "msg": "用户不存在|密码错误"}
    
#@18 管理员信息修改函数(老唐版)————not yet
def editInfo(name,avatar,token):
    db = Database.Database()
    response = {}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        ID = payload.get("ID")
        password = payload.get("password")
        if avatar:
            saveUrl = os.path.join(IMGREPO_DIR, f"{ID}_avatar.png")
            avatar.save(saveUrl)
            avatarUrl = f"/imgRepo/{ID}_avatar.png"
        db.connect()
        response = db.execute_query(
            "update Admin set name = %(name)s, avatarUrl = %(avatarUrl)s where ID = %(ID)s",
            {"name": name, "avatarUrl": avatarUrl, "ID": ID}
        )
        db.disconnect()
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"editInfo: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"editInfo: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        new_payload = {
            "ID": ID,
            "password": password,
            "exp": time.time() + 3600
        }
        new_token = jwt.encode(
            new_payload,
            secret_key,
            algorithm=algorithm
        )
        return {"code": 200,"data":{"token":new_token}}
    else:
        return {"code":999, "msg":"管理员信息修改失败"}

#@19 管理员密码修改函数(老唐版)————OK
def editPassword(password,newPassword,token):
    db=Database.Database()
    response={}
    ID=""
    password=""
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        ID = payload.get("ID")
        password = payload.get("password")    
        db.connect()
        response = db.execute_query("update Admin set password=%(newPassword)s where ID=%(ID)s",{"newPassword": newPassword, "ID": ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"editPassword: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"editPassword: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        new_payload = {
            "ID": ID,
            "password": password,
            "exp": time.time() + 3600
        }
        new_token = jwt.encode(
            new_payload,
            secret_key,
            algorithm=algorithm
        )
        return {"code": 200,"data":{"token":new_token}}
    else:
        return {"code":999, "msg":"用户密码修改失败"}

#@20 管理员信息获取函数(老唐版)————OK
def getInfo(token):
    db = Database.Database()
    response={}
    ID=""
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        ID = payload.get("ID")
        db.connect()
        response = db.execute_query("select ID, name, authority as permission, avatarUrl from Admin where ID=%(ID)s",{"ID":ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getInfo: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getInfo: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        row = response[0]
        dataList = {
            "ID": row[0],
            "name": row[1],
            "permission": row[2],
            "avatarUrl": row[3]
        }
        return {"code":200, "data": dataList}
    else:
        return {"code":999, "msg":"用户信息获取失败"}
    
