import Database
import jwt
import time
secret_key = "salt256"
algorithm = "HS256"

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
$body = @{
    type = "面食"
    canteen = "榕园"
    collation = "desc"
    numPerPage = "3"
    pageIndex = "1"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYzMDA1ODU4LjM3OTMzMDl9.ya5MjZZEsr2EEMDyiyK15wJxUB3vBBhL0zFal_fmgmQ"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/food/getStallList" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
"""

#@9获取档口列表函数(老唐版)————测试完成
def getStallList(type_str,canteen,collation,numPerPage,pageIndex,token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    numPerPage_int = int(numPerPage)
    pageIndex_int = int(pageIndex)
    type_str = str(type_str) if type_str is not None else ""
    canteen = str(canteen) if canteen is not None else ""
    collation = str(collation) if collation is not None else "desc"
    numPerPage = str(numPerPage) if numPerPage is not None else "10"
    pageIndex = str(pageIndex) if pageIndex is not None else "1"
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
        allowed_collations = ["asc", "desc", "ASC", "DESC"]
        if collation.lower() not in [c.lower() for c in allowed_collations]:
            collation = "desc" 
        response = db.execute_query("select ID,name,rating,meanPrice,canteen,signatureDish,pictureUrl from Stall where type = %(type)s and canteen=%(canteen)s order by rating "+collation,{"type":type_str,"canteen":canteen})
        response_rows = db.execute_query("select count(*) as total_rows from Stall where where type = %(type)s and canteen=%(canteen)s",{"type":type_str,"canteen":canteen})

        db.disconnect()
        total_rows = 0
        if response_rows and len(response_rows) > 0:
            if isinstance(response_rows[0], tuple):
                total_rows = response_rows[0][0] if len(response_rows[0]) > 0 else 0
            elif isinstance(response_rows[0], dict):
                total_rows = response_rows[0].get("total_rows", 0)
            else:
                # 尝试直接转换为整数
                try:
                    total_rows = int(response_rows[0])
                except:
                    total_rows = 0
        
        # 计算总页数
        totalPageNum = total_rows // numPerPage_int
        if total_rows % numPerPage_int > 0:
            totalPageNum += 1
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getStallList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getStallList: 其他错误: {e}")
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
        stalls = []
        if response and len(response) > 0:
            for row in response:
                if isinstance(row, dict):
                    stall = {
                        "ID": row.get("ID"),
                        "name": row.get("name"),
                        "rating": float(row.get("rating", 0)),
                        "meanPrice": float(row.get("meanPrice", 0)),
                        "canteen": row.get("canteen"),
                        "signatureDish": row.get("signatureDish"),
                        "pictureUrl": row.get("pictureUrl")
                    }
                else:
                # 处理元组格式
                    stall = {
                        "ID": row[0] if len(row) > 0 else None,
                        "name": row[1] if len(row) > 1 else "",
                        "rating": float(row[2]) if len(row) > 2 and row[2] is not None else 0.0,
                        "meanPrice": float(row[3]) if len(row) > 3 and row[3] is not None else 0.0,
                        "canteen": row[4] if len(row) > 4 else "",
                        "signatureDish": row[5] if len(row) > 5 else "",
                        "pictureUrl": row[6] if len(row) > 6 else None
                    }
                stalls.append(stall)
        return {"code":200, "data": {"stalls":stalls, "totalPageNum":totalPageNum, "pageIndex":pageIndex, "token": token}}
    else:
        return {"code":999, "msg":"档口列表获取失败"}

""""
test:
$body = @{
    stallID = 1
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYzMDI1ODczLjQ5OTM1MzJ9.nzbtrRe0lsOXVJ05eiQ8u-WWU5REBi6eLGRJZo7X2qE"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/food/getStallInfo" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
"""

#@10 档口详细信息获取函数(老唐版)————测试完成
def getStallInfo(stallID, token):
    db = Database.Database()
    userName = ""
    password = ""
    try:
        # 验证 token
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        # 解码 token 获取当前用户
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        # 查询店铺基本信息
        response_stallInfo = db.execute_query(
            "SELECT ID, name, rating, meanPrice, introduction, canteen, signatureDish, pictureUrl FROM Stall WHERE ID = %(stallID)s", 
            {"stallID": stallID}
        )
        # 检查店铺是否存在
        if not response_stallInfo or len(response_stallInfo) == 0:
            db.disconnect()
            return {"code": 999, "msg": "档口不存在"}
        # 处理店铺信息 - 确保正确处理元组
        stall_row = response_stallInfo[0]
        # 无论返回的是字典还是元组，都统一处理
        if isinstance(stall_row, dict):
            stall_info = {
                "ID": stall_row.get("ID"),
                "name": stall_row.get("name"),
                "rating": float(stall_row.get("rating", 0)),
                "meanPrice": float(stall_row.get("meanPrice", 0)),
                "introduction": stall_row.get("introduction", ""),
                "canteen": stall_row.get("canteen", ""),
                "signatureDish": stall_row.get("signatureDish", ""),
                "pictureUrl": stall_row.get("pictureUrl", "")
            }
        else:
            # 元组格式 - 使用索引访问
            stall_info = {
                "ID": stall_row[0] if len(stall_row) > 0 else None,
                "name": stall_row[1] if len(stall_row) > 1 else "",
                "rating": float(stall_row[2]) if len(stall_row) > 2 and stall_row[2] is not None else 0.0,
                "meanPrice": float(stall_row[3]) if len(stall_row) > 3 and stall_row[3] is not None else 0.0,
                "introduction": stall_row[4] if len(stall_row) > 4 else "",
                "canteen": stall_row[5] if len(stall_row) > 5 else "",
                "signatureDish": stall_row[6] if len(stall_row) > 6 else "",
                "pictureUrl": stall_row[7] if len(stall_row) > 7 else ""
            }
        # 查询菜品列表
        response_dishList = db.execute_query(
            "SELECT ID, name, price, CASE WHEN (recommendCount + dislikeCount) = 0 THEN 0 ELSE (recommendCount * 5.0) / (recommendCount + dislikeCount) END as rating, pictureUrl FROM Dish WHERE stallID = %(stallID)s",
            {"stallID": stallID}
        )
        # 处理菜品列表
        dish_list = []
        if response_dishList and len(response_dishList) > 0:
            for dish_row in response_dishList:
                print(f"菜品行: {dish_row}, 类型: {type(dish_row)}")
                if isinstance(dish_row, dict):
                    dish = {
                        "ID": dish_row.get("ID"),
                        "name": dish_row.get("name"),
                        "price": float(dish_row.get("price", 0)),
                        "rating": float(dish_row.get("rating", 0)),
                        "pictureUrl": dish_row.get("pictureUrl", "")
                    }
                else:
                    # 元组格式
                    dish = {
                        "ID": dish_row[0] if len(dish_row) > 0 else None,
                        "name": dish_row[1] if len(dish_row) > 1 else "",
                        "price": float(dish_row[2]) if len(dish_row) > 2 and dish_row[2] is not None else 0.0,
                        "rating": float(dish_row[3]) if len(dish_row) > 3 and dish_row[3] is not None else 0.0,
                        "pictureUrl": dish_row[4] if len(dish_row) > 4 else ""
                    }
                dish_list.append(dish)
        # 查询评论列表
        response_commentList = db.execute_query(
            "SELECT sc.ID, sc.userName as reviewerName, u.avatarUrl, sc.dateTime, sc.rating, sc.recommendCount as `like`, sc.content, sc.picture1Url, sc.picture2Url, sc.picture3Url FROM StallComment sc INNER JOIN User u ON sc.userName = u.userName WHERE sc.stallID = %(stallID)s ORDER BY sc.dateTime DESC",
            {"stallID": stallID}
        )
        # 处理评论列表
        comment_list = []
        if response_commentList and len(response_commentList) > 0:
            for comment_row in response_commentList:
                print(f"评论行: {comment_row}, 类型: {type(comment_row)}")
                if isinstance(comment_row, dict):
                    comment = {
                        "ID": comment_row.get("ID"),
                        "reviewerName": comment_row.get("reviewerName"),
                        "avatarUrl": comment_row.get("avatarUrl"),
                        "dateTime": comment_row.get("dateTime").isoformat() if comment_row.get("dateTime") else None,
                        "rating": float(comment_row.get("rating", 0)),
                        "like": comment_row.get("like", 0),
                        "content": comment_row.get("content", ""),
                        "picture1Url": comment_row.get("picture1Url"),
                        "picture2Url": comment_row.get("picture2Url"),
                        "picture3Url": comment_row.get("picture3Url")
                    }
                else:
                    # 元组格式
                    comment = {
                        "ID": comment_row[0] if len(comment_row) > 0 else None,
                        "reviewerName": comment_row[1] if len(comment_row) > 1 else "",
                        "avatarUrl": comment_row[2] if len(comment_row) > 2 else "",
                        "dateTime": comment_row[3].isoformat() if len(comment_row) > 3 and comment_row[3] else None,
                        "rating": float(comment_row[4]) if len(comment_row) > 4 and comment_row[4] is not None else 0.0,
                        "like": comment_row[5] if len(comment_row) > 5 else 0,
                        "content": comment_row[6] if len(comment_row) > 6 else "",
                        "picture1Url": comment_row[7] if len(comment_row) > 7 else None,
                        "picture2Url": comment_row[8] if len(comment_row) > 8 else None,
                        "picture3Url": comment_row[9] if len(comment_row) > 9 else None
                    }
                comment_list.append(comment)
        db.disconnect()
        # 生成新 token
        payload = {
            "userName": userName,
            "password": password,
            "exp": time.time() + 3600
        }
        new_token = jwt.encode(payload, secret_key, algorithm=algorithm)
        # 构建最终结果
        result = {
            "code": 200,
            "data": {
                **stall_info,  # 使用字典解包
                "dishList": dish_list,
                "commentList": comment_list,
                "token": new_token
            }
        }
        print(f"最终返回结果: {result}")
        return result
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getStallInfo: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getStallInfo: 其他错误: {e}")
        import traceback
        traceback.print_exc()
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}

"""
test:
$body = @{
    stallID = 2
    numPerPage = 2
    pageIndex = 1
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYzMDI3NDkxLjkyODM5Nzd9.0VsFC8sYdKRGngudIOdxYTHHyr57JeqD7Qv-QNTaoek"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/food/getStallCommentList" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
"""

#@11 档口全部评论获取函数(老唐版)————测试完成
def getStallCommentList(stallID, numPerPage, pageIndex, token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    numPerPage_int = int(numPerPage)
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
        response = db.execute_query("""
            select sc.ID, sc.userName as reviewerName, u.avatarUrl, sc.dateTime,
            sc.rating, sc.recommendCount as `like`, sc.content, sc.picture1Url,
            sc.picture2Url, sc.picture3Url from StallComment sc inner join User u on sc.userName = u.userName
            where sc.stallID = %(stallID)s order by sc.dateTime desc""", {"stallID":stallID})
        response_rows = db.execute_query("""
            select count(*) as comment_count from StallComment sc inner 
            join User u on sc.userName = u.userName
            where sc.stallID = %(stallID)s""", {"stallID":stallID})
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
            commentList= []
            if response and len(response) > 0:
                for row in response:
                    if isinstance(row, dict):
                    # 字典格式
                        comment = {
                            "ID": row.get("ID"),
                            "reviewerName": row.get("reviewerName"),
                            "avatarUrl": row.get("avatarUrl"),
                            "dateTime": row.get("dateTime").isoformat() if row.get("dateTime") else None,
                            "rating": float(row.get("rating", 0)),
                            "like": row.get("like", 0),
                            "content": row.get("content", ""),
                            "picture1Url": row.get("picture1Url"),
                            "picture2Url": row.get("picture2Url"),
                            "picture3Url": row.get("picture3Url")
                        }
                    else:
                    # 元组格式
                        comment = {
                            "ID": row[0] if len(row) > 0 else None,
                            "reviewerName": row[1] if len(row) > 1 else "",
                            "avatarUrl": row[2] if len(row) > 2 else "",
                            "dateTime": row[3].isoformat() if len(row) > 3 and row[3] else None,
                            "rating": float(row[4]) if len(row) > 4 and row[4] is not None else 0.0,
                            "like": row[5] if len(row) > 5 else 0,
                            "content": row[6] if len(row) > 6 else "",
                            "picture1Url": row[7] if len(row) > 7 else None,
                            "picture2Url": row[8] if len(row) > 8 else None,
                            "picture3Url": row[9] if len(row) > 9 else None
                        }
                    commentList.append(comment)
            return {"code":200, "data": {"commentList":commentList, "totalPageNum":totalPageNum, "pageIndex":pageIndex, "token": token}}
        else:
            return {"code":999, "msg":"档口评论获取失败"}
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getStallCommentList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getStallCommentList: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}

"""
test:
$body = @{
    stallID = 1
    rating = 1
    content = "吃石都比吃这个好，爱吃的都是老八来的"
    picture1Url = "http://example.com/shit.jpg"
    picture2Url = $null
    picture3Url = $null
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYzMDM1MzY2LjY5MjU4ODN9.oSFV3IZADv2wDgVOgLoIaBLuKuq_a_CjE62ieJUagcg"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/food/createStallComment" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
"""

#@12 发表评论函数(老唐版)————测试成功
def createStallComment(stallID, rating, content, picture1Url, picture2Url, picture3Url, token):
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
        response = db.execute_query("""insert into StallComment (userName, stallID, content, 
            rating, picture1Url, picture2Url, picture3Url,dateTime) values (%(userName)s,%(stallID)s,%(content)s,
            %(rating)s,%(picture1Url)s,%(picture2Url)s,%(picture3Url)s,now())""",{"userName":userName,"stallID":stallID,"content":content,
            "rating":rating,"picture1Url":picture1Url,"picture2Url":picture2Url,"picture3Url":picture3Url})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"createStallComment: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"createStallComment: 其他错误: {e}")
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
        return {"code":200, "data": {"token": token}}
    else:
        return {"code":999, "msg":"档口评论获取失败"}

""" test:
$body = @{
    commentID = 5
    newEvaluation = "none"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYzMDM5OTM5LjI1MjI0ODV9.h-z7KO5IWvvjToTmfibLjhgz91XPRHHTv9l3L80CsSQ"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/food/evaluationComment" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
"""

#@13 评价评论函数(老唐版)————测试完成
def evaluationComment(commentID, newEvaluation, token):
    db = Database.Database()
    response={}
    operation_success = False
    userName=""
    password=""
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #先查找是否有过评价的经历
        response_search = db.execute_query("select * from UserComment where userName=%(userName)s and commentID=%(commentID)s",
            {"userName":userName,"commentID":commentID})
        print(f"查询结果: {response_search}")
        if newEvaluation=="like" :
            #如果是like且没有评价过，则插入一条记录，并将评论的推荐数加1；否则pass
            if not response_search or len(response_search) == 0:
                response = db.execute_query("insert into UserComment (userName, commentID) values (%(userName)s,%(commentID)s",
                    {"userName":userName,"commentID":commentID})
                response_add_like = db.execute_query("update StallComment set recommendCount = recommendCount + 1 where ID = %(commentID)s",{"commentID":commentID})
                print(f"点赞操作 - 插入: {response}, 更新: {response_add_like}")
                if (response and isinstance(response, dict) and response.get("rowcount", 0) > 0 and
                    response_add_like and isinstance(response_add_like, dict) and response_add_like.get("rowcount", 0) > 0):
                    operation_success = True
            else:
                operation_success = True
                pass
        elif newEvaluation=="none":
            #如果是none且评价过，则删除该记录，并将评论的推荐数-1，否则pass
            if response_search and len(response_search) > 0:
                response = db.execute_query("delete from UserComment where userName=%(userName)s and commentID=%(commentID)s",
                    {"userName":userName,"commentID":commentID})
                response_delete_like = db.execute_query("update StallComment set recommendCount = greatest(recommendCount-1,0) where ID = %(commentID)s",{"commentID":commentID})
                print(f"取消点赞操作 - 删除: {response}, 更新: {response_delete_like}")
                if (response and isinstance(response, dict) and response.get("rowcount", 0) > 0 and
                    response_delete_like and isinstance(response_delete_like, dict) and response_delete_like.get("rowcount", 0) > 0):
                    operation_success = True
            else:
                operation_success = True
                pass
        db.disconnect()
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"evaluationComment: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"evaluationComment: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if operation_success:
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
        return {"code":999, "msg":"评价评论失败"}

""" 
test:
$body = @{
    stallID = 1
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYzMDM5OTM5LjI1MjI0ODV9.h-z7KO5IWvvjToTmfibLjhgz91XPRHHTv9l3L80CsSQ"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/food/getStallDishList" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
"""
    
#@14 获取菜品列表(老唐版)————测试完成
def getStallDishList(stallID, token):
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
        response = db.execute_query("""select d.ID,d.name,d.price,d.recommendCount as `like`,
            d.dislikeCount as bad,d.pictureUrl, coalesce(de.evaluation, 'none') as evaluation
            from Dish d left join DishEvaluation de on d.ID = de.dishID and de.userName = %(userName)s
            where d.stallID = %(stallID)s order by d.ID""",{"userName":userName, "stallID":stallID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getStallDishList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getStallDishList: 其他错误: {e}")
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

        dishList = []
        if response and len(response) > 0:
            for row in response:
                # 根据返回的数据类型处理
                if isinstance(row, dict):
                    # 如果返回的是字典格式
                    dish = {
                        "ID": row.get("ID"),
                        "name": row.get("name"),
                        "price": float(row.get("price", 0)),
                        "like": row.get("like", 0),
                        "bad": row.get("bad", 0),
                        "pictureUrl": row.get("pictureUrl"),
                        "evaluation": row.get("evaluation", "none")
                    }
                else:
                    # 如果返回的是元组格式，使用索引访问
                    # 假设字段顺序与 SELECT 语句中的顺序一致
                    dish = {
                        "ID": row[0] if len(row) > 0 else None,
                        "name": row[1] if len(row) > 1 else "",
                        "price": float(row[2]) if len(row) > 2 else 0.0,
                        "like": row[3] if len(row) > 3 else 0,
                        "bad": row[4] if len(row) > 4 else 0,
                        "pictureUrl": row[5] if len(row) > 5 else None,
                        "evaluation": row[6] if len(row) > 6 else "none"
                    }
                dishList.append(dish)
        return {"code":200, "data": {"dishList":dishList, "token": token}}
    else:
        return {"code":999, "msg":"菜品列表获取失败"}

""" 
test:
$body = @{
    dishID = 5
    newEvaluation = "like"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyTmFtZSI6ImxqeSIsInBhc3N3b3JkIjoiMTIzNDU2IiwiZXhwIjoxNzYzMDQwOTQ1LjExMTQzNX0.T8CWRJD2dfM32UoKGHzT0Yc2sl8pdhlDGExJBMGnT5k"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/food/evaluateDish" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
"""

#@15 更新菜品评价函数(老唐版)————测试完成
def evaluateDish(dishID, newEvaluation, token):
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
        if newEvaluation=="like":
            newEvaluation="赞"
        elif newEvaluation=="bad":
            newEvaluation="踩"
        else:
            newEvaluation="无"
        #使用数据库进行更新
        response = db.execute_query("update DishEvaluation set evaluation=%(newEvaluation)s where dishID=%(dishID)s and userName=%(userName)s", {"newEvaluation":newEvaluation, "dishID":dishID, "userName":userName})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"evaluateDish: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"evaluateDish: 其他错误: {e}")
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
        return {"code":200, "data": {"token": token}}
    else:
        return {"code":999, "msg":"菜品评价更新失败"}
