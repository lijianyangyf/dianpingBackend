import Database
import jwt
import time
import os
secret_key = "salt256"
algorithm = "HS256"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMGREPO_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../imgRepo"))
""" test:
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/checkToken -Method Get -Body '{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYyOTMzODIzLjcwODg3ODV9.bzDpOP5azzsaj5T61XSqYXCm3N1mEOqyvJkN-6IDgo8"}' -ContentType "application/json"
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
        with Database.Redislock(Database.rcli,f"user:{userName}"):
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
 -Method Post -Body '{"userName":"ljy","password":"123456"}' `
 -ContentType "application/json"
"""

#@2 登录函数(老李版)————测试成功
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
#@3 注册函数(老唐版)————测试成功
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
    
#@4 用户信息修改函数(老唐版)————测试成功
""" test:
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/user/editInfo'  -Method POST  -Body '{"nickName":"NewNick","avatarUrl":"http://example.com/csb.png","token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYyOTMzODIzLjcwODg3ODV9.bzDpOP5azzsaj5T61XSqYXCm3N1mEOqyvJkN-6IDgo8"}' -ContentType 'application/json' -Verbose
"""
#$headers = @{ "Cookie" = "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYyODU0Njk2LjUwOTY1NX0.H7AchVyuGZCYi6oRiPQx7QHA6uO7irJKegjsXEhkVI0" }; Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/editInfo -Method Post -Body '{"nickName":"NewNick","avatarUrl":"http://example.com/avatar.png"}' -Headers $headers -ContentType 'application/json' -Verbose
def editInfo(nickName, avatar, token):
    db = Database.Database()
    response = {}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        # 解码 token 获取用户名
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        if avatar:
            saveUrl = os.path.join(IMGREPO_DIR, f"{userName}_avatar.png")
            avatar.save(saveUrl)
            avatarUrl = f"/imgRepo/{userName}_avatar.png"
        db.connect()
        response = db.execute_query(
            "update User set nickName = %(nickName)s, avatarUrl = %(avatarUrl)s where userName = %(userName)s",
            {"nickName": nickName, "avatarUrl": avatarUrl, "userName": userName}
        )
        db.disconnect()
    #若token出现问题
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"editInfo: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"editInfo: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    
    # 检查更新是否成功
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
        return {"code":999, "msg":"用户信息修改失败"}
    
""" test:
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/editPassword -Method Post -Body '{"password":"123456","newPassword":"123456","token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYyOTM1NzM4LjY5ODMyNzN9._GB-Eqn8BBpESAnqgz-LqbUYGV3aBbalAf91aYPHYs8"}' -ContentType "application/json"
"""

#@5 用户密码修改函数(老唐版)————测试成功
def editPassword(newPassword, token):
    db=Database.Database()
    response={}
    userName=""
    password=""
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        # 解码 token 获取用户名
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")    
        db.connect()
        #使用数据库进行更新
        response = db.execute_query("update User set password=%(newPassword)s where userName=%(userName)s",{"newPassword": newPassword, "userName": userName})
        db.disconnect()
        print(response)
    #若token出现问题
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
        return {"code":999, "msg":"用户信息修改失败"}
    
""" test:
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/getInfo -Method Post -Body '{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYyOTQxNjMyLjkwMDIwMTN9.lxxo4QIhmitZg8WkcVD42TO90Q9nY3MttqSYRbCOJwI"}' -ContentType "application/json"
"""

#@6 用户信息获取函数(老唐版)————测试成功
def getInfo(token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        # 解码token获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #使用数据库进行查询
        response = db.execute_query("select userName, nickName, avatarUrl from User where userName=%(userName)s",{"userName":userName})
        db.disconnect()
        print(response)
    #若token出现问题
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getInfo: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getInfo: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
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
        row = response[0]
        dataList = {
            "userName": row[0],
            "nickName": row[1],
            "avatarUrl": row[2],
            "token": token
        }
        return {"code":200, "data": dataList}
    else:
        return {"code":999, "msg":"用户信息获取失败"}

""" test:
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/getCommentList -Method Post -Body '{"numPerPage":"2","pageIndex":"1","token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYyOTUzODg3LjgzMzU1NjJ9.xtvEJKcnm4xm3EtxIF660pSq0QH2zGoQHKBr_4_7jRc"}' -ContentType "application/json"
"""
        
#@7 评论获取函数(老唐版)————测试成功
def getCommentList(numPerPage, pageIndex, token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    numPerPage_int = int(numPerPage)
    pageIndex_int = int(pageIndex)
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        # 解码token获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #使用数据库进行查询
        response = db.execute_query("select sc.ID,s.name as stall_name,s.canteen,sc.dateTime,sc.rating,sc.recommendCount,sc.content,sc.picture1Url,sc.picture2Url,sc.picture3Url from StallComment sc inner join Stall s on sc.stallID = s.ID where sc.userName = %(userName)s order by sc.dateTime desc",{"userName":userName})
        response_rows = db.execute_query("select count(*) as total_rows from StallComment sc inner join Stall s on sc.stallID = s.ID where sc.userName = %(userName)s;", {"userName": userName})
        db.disconnect()
        if response_rows and len(response_rows) > 0:
            if isinstance(response_rows[0], tuple):
                total_rows = response_rows[0][0]  # 元组格式
            else:
                total_rows = response_rows[0].get("total_rows", 0)  # 字典格式
        else:
            total_rows = 0
        totalPageNum = int(total_rows) // numPerPage_int
        if total_rows % numPerPage_int > 0:
            totalPageNum += 1
        print(response)
    #若token出现问题
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getCommentList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getCommentList: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
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
        comments = []
        if response and len(response) > 0:
            for row in response:
                if isinstance(row, dict):
                    # 字典格式
                    comment = {
                        "ID": row.get("ID"),
                        "stallName": row.get("stall_name"),
                        "canteen": row.get("canteen"),
                        "dateTime": row.get("dateTime").isoformat() if row.get("dateTime") else None,
                        "rating": float(row.get("rating", 0)),
                        "recommendCount": row.get("recommendCount", 0),
                        "content": row.get("content", ""),
                        "picture1Url": row.get("picture1Url"),
                        "picture2Url": row.get("picture2Url"),
                        "picture3Url": row.get("picture3Url")
                    }
                else:
                    # 元组格式
                    comment = {
                        "ID": row[0] if len(row) > 0 else None,
                        "stallName": row[1] if len(row) > 1 else "",
                        "canteen": row[2] if len(row) > 2 else "",
                        "dateTime": row[3].isoformat() if len(row) > 3 and row[3] else None,
                        "rating": float(row[4]) if len(row) > 4 else 0.0,
                        "recommendCount": row[5] if len(row) > 5 else 0,
                        "content": row[6] if len(row) > 6 else "",
                        "picture1Url": row[7] if len(row) > 7 else None,
                        "picture2Url": row[8] if len(row) > 8 else None,
                        "picture3Url": row[9] if len(row) > 9 else None
                    }
                comments.append(comment)
        return {"code":200, "data": {"comments":comments, "totalPageNum":totalPageNum, "pageIndex":pageIndex, "token": token}}
    else:
        return {"code":999, "msg":"用户评论获取失败"}

""" test:
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/user/deleteComment -Method Post -Body '{"commentID":"1","token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYyOTk3ODgzLjA4NDg1MTV9.wPHIG3SSa1LTRBZN_5m9y-iEWa_2dqZeyLyJiZcrbkc"}' -ContentType "application/json"
"""

#@8 删除评论函数(老唐版)————测试成功
def deleteComment(commentID, token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    commentID_int = int(commentID)
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        # 解码token获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #使用数据库进行删除
        check_response = db.execute_query(
            "select ID from StallComment where ID = %(commentID)s AND userName = %(userName)s",
            {"commentID": commentID_int, "userName": userName}
        )
        if not check_response or len(check_response) == 0:
            db.disconnect()
            return {"code": 999, "msg": "评论不存在或无权删除"}
        response_userComment = db.execute_query("delete from UserComment where commentID=%(commentID)s",{"commentID":commentID_int})
        print(f"UserComment 删除结果: {response_userComment}")
        response = db.execute_query("delete from StallComment where ID=%(commentID)s and userName=%(userName)s",{"commentID":commentID_int,"userName":userName})
        db.disconnect()
        print(f"StallComment 删除结果: {response}")
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"deleteComment: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"deleteComment: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response and isinstance(response, dict) and response.get("rowcount", 0) > 0:
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
        return {"code":999, "msg":"用户评论删除失败"}
