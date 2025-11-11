import Database
import jwt
import time
secret_key = "salt256"
algorithm = "HS256"

""" test:
$headers = @{ "Cookie" = "token=..." }
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/checkToken -Method Get -Headers $headers
"""
#@1 校验token函数(老李版)
def checkToken(token):
    db=Database.Database()
    response={}
    userName=""
    password=""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        response=db.execute_query("select * from User where userName=%(userName)s AND password=%(password)s",{"userName":userName,"password":password})
        db.disconnect()
    except Exception as e:
        print(e)
        raise
    if response is not None:
        new_payload = {
            "userName": userName,
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
        return {"code": 999}
""" test:
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/login `
 -Method Post -Body '{"userName":"admin","password":"123456"}' `
 -ContentType "application/json"
"""

#@2 登录函数(老李版)
def login(userName,password):
    db=Database.Database()
    db.connect()
    response=db.execute_query("select * from User where userName=%(userName)s AND password=%(password)s",{"userName":userName,"password":password})
    db.disconnect()
    print(response)
    payload ={
        "userName":userName,
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
        return {"code": 999, "msg": "用户名或密码错误"}

""" test:
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/signUp `
 -Method Post -Body '{"userName":"ljy","nickName":"New","password":"123456"}' `
 -ContentType "application/json"
"""
#@3 注册函数(老唐版)
def signUp(userName, nickName, password):
    db = Database.Database()
    db.connect()
    #try:
        #response = db.execute_query("select * from user where userName=%(userName)s", {"userName": userName})
    # 如果查询到用户（SELECT 返回非空列表），则认为已存在
    #except Exception as e:
        #db.disconnect()
        #return {"code": 999, "msg": "用户名已存在"}
    response = db.execute_query(
        "insert into User (userName,nickName,password) values (%(userName)s,%(nickName)s,%(password)s)",
        {"userName": userName, "nickName": nickName, "password": password}
    )
    db.disconnect()
    print(response)
    payload = {
        "userName": userName,
        "password": password,
        "exp": time.time() + 3600
    }
    token = jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm
    )

    # 对写操作返回值做更严格的校验（expect dict with rowcount）
    if isinstance(response, dict) and response.get("rowcount", 0) > 0:
        return {"code": 200, "data": {"token": token}}
    else:
        return {"code": 888, "msg": "用户注册失败"}
    
#@4 用户信息修改函数(老唐版)
""" test:
$headers = @{ "Cookie" = "token=..." }
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/editInfo `
 -Method Post -Body '{"nickName":"NewNick","avatar":"http://example.com/avatar.png"}' `
 -Headers $headers -ContentType "application/json"
"""
def editInfo(nickName,avatarUrl,token):
    db=Database.Database()
    response={}
    userName=""
    password=""
    try:
        # 解码 token 获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        db.connect()
        #使用数据库进行更新
        response = db.execute_query("update User set nickName=%(nickName)s,avatarUrl=%(avatarUrl)s where userName=%(userName)s",{"nickName": nickName, "avatarUrl": avatarUrl, "userName": userName})
        db.disconnect()
        print(response)
    except Exception as e:
        print(e)
        raise
    if response is not None:
        payload = {
            "userName":userName,
            "password":password,
            "exp":time.time()+3600
        }
        token = jwt.encode(
            payload,
            secret_key,
            algorithm=algorithm
        )
        return {"code":200, "data": {"token": token}}
    else:
        return {"code":999, "msg":"用户信息修改失败"}
    
#@5 用户密码修改函数(老唐版)
def editPassword(newPassword, token):
    db=Database.Database()
    response={}
    userName=""
    password=""
    try:
        # 解码token获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        db.connect()
        #使用数据库进行更新
        response = db.execute_query("update User set password=%(newPassword)s where userName=%(userName)s",{"newPassword": newPassword, "userName": userName})
        db.disconnect()
        print(response)
    except Exception as e:
        print(e)
        raise
    if response is not None:
        new_payload = {
            "userName": userName,
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

#@6 用户信息获取函数(老唐版)
def getInfo(token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    try:
        # 解码token获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #使用数据库进行查询
        response = db.execute_query("select userName, nickName, avatarUrl from User where userName=%(userName)s",{"userName":userName})
        db.disconnect()
        print(response)
    except Exception as e:
        print(e)
        raise
    if response is not None:
        payload = {
            "userName":userName,
            "password":password,
            "exp":time.time()+3600
        }
        token = jwt.encode(
            payload,
            secret_key,
            algorithm=algorithm
        )
        uname=response[0]["userName"]
        nick=response[0]["nickName"]
        avatar=response[0]["avatarUrl"]
        return {"code":200, "data": {"userName":uname, "nickName":nick,"avatarUrl":avatar,"token": token}}
    else:
        return {"code":999, "msg":"用户信息获取失败"}
        
#@7 评论获取函数(老唐版)
def getCommentList(numPerPage, pageIndex, token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    try:
        # 解码token获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #使用数据库进行查询
        response = db.execute_query("select sc.ID,s.name as stall_name,s.canteen,sc.dateTime,sc.rating,sc.recommendCount,sc.content,sc.picture1Url,sc.picture2Url,sc.picture3Url form StallComment sc inner join Stall s on sc.stallID = s.ID where sc.userName = %(userName)s order by sc.dateTime desc",{"userName":userName})
        response_rows = db.execute_query("select count(*) as total_rows from StallComment sc inner join Stall s on sc.stallID = s.ID where sc.userName = %(userName)s;", {"userName": userName})
        db.disconnect()
        total_rows = response_rows[0]['total_rows']
        totalPageNum = total_rows // numPerPage + (1 if total_rows % numPerPage > 0 else 0)
        print(response)
    except Exception as e:
        print(e)
        raise
    if response is not None:
        payload = {
            "userName":userName,
            "password":password,
            "exp":time.time()+3600
        }
        token = jwt.encode(
            payload,
            secret_key,
            algorithm=algorithm
        )
        return {"code":200, "data": {"comments":response, "totalPageNum":totalPageNum, "pageIndex":pageIndex, "token": token}}
    else:
        return {"code":999, "msg":"用户评论获取失败"}

#@8 删除评论函数(老唐版)
def deleteComment(commentID, token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    try:
        # 解码token获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #使用数据库进行删除
        response = db.execute_query("delete from comment where ID=%(commentID)s",{"commentID":commentID})
        db.disconnect()
        print(response)
    except Exception as e:
        print(e)
        raise
    if response is not None:
        payload = {
            "userName":userName,
            "password":password,
            "exp":time.time()+3600
        }
        token = jwt.encode(
            payload,
            secret_key,
            algorithm=algorithm
        )
        return {"code":200, "data": {"token": token}}
    else:
        return {"code":999, "msg":"用户评论获取失败"}
