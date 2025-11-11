import Database
import jwt
import time
secret_key = "salt256"
algorithm = "HS256"

#@9获取档口列表函数(老唐版)
def getStallList(type,canteen,collation,numPerPage,pageIndex,token):
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
        response = db.execute_query("select ID,name,rating,meanPrice,canteen,signatureDish,pictureUrl from Stall where type=%(type)s and canteen=%(canteen)s order by %(collation)s",{"type":type,"canteen":canteen,"collation":collation})
        response_rows = db.execute_query("select count(*) as total_rows from Stall where type=%(type)s and canteen=%(canteen)s", {"type":type,"canteen":canteen})
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
        return {"code":200, "data": {"stalls":response, "totalPageNum":totalPageNum, "pageIndex":pageIndex, "token": token}}
    else:
        return {"code":999, "msg":"档口列表获取失败"}

#@10 档口详细信息获取函数(老唐版)
def getStallInfo(stallID, token):
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
        response_stallInfo = db.execute_query("select ID, name, rating, meanPrice, introduction, canteen, signatureDish, pictureUrl from Stall where ID = %(stallID)s",{"stallID":stallID})
        response_dishList = db.execute_query("select ID, name, price, case when (recommendCount + dislikeCount) = 0 when 0 else (recommendCount * 5.0) / (recommendCount + dislikeCount) end as rating, pictureUrl from Dish where stallID = %(stallID)s",{"stallID":stallID})
        response_commentList = db.execute_query("select sc.ID, sc.userName as reviewerName, u.avatarUrl,sc.dateTime, sc.rating, sc.recommendCount as `like`, sc.content, sc.picture1Url, sc.picture2Url, sc.picture3Url from StallComment sc inner join User u on sc.userName = u.userName where sc.stallID = %(stallID)s order by sc.dateTime desc",{"stallID":stallID})
        result = {
        **response_stallInfo[0],
        "dishList": response_dishList,
        "commentList": response_commentList
        }
        db.disconnect()
        print(result)
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
        return {"code":200, "data": {"ID":response_stallInfo[0],"name":response_stallInfo[1],"rating":response_stallInfo[2],"meanPrice":response_stallInfo[3],\
                "introduction":response_stallInfo[4],"canteen":response_stallInfo[5],"signatureDish":response_stallInfo[6],"pictureUrl":response_stallInfo[7],\
                "dishList":response_dishList,"commentList":response_commentList,"token": token}}
    else:
        return {"code":999, "msg":"档口详细信息获取失败"}

#@11 档口全部评论获取函数(老唐版)
def getStallCommentList(stallID, numPerPage, pageIndex, token):
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
        return {"code":200, "data": {"commentList":response, "totalPageNum":totalPageNum, "pageIndex":pageIndex, "token": token}}
    else:
        return {"code":999, "msg":"档口评论获取失败"}

#@12 发表评论函数(老唐版)
def createStallComment(stallID, rating, content, pictrue1Url, picture2Url, picture3Url, token):
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
        response = db.execute_query("""insert into StallComment (userName, stallID, content, 
            rating, pictrue1Url, picture2Url, picture3Url) values (%(userName)s,%(stallID)s,%(content)s,
            %(rating)s,%(pictrue1Url)s,%(picture2Url)s,%(picture3Url)s)""",{"userName":userName,"stallID":stallID,"content":content,
            "rating":rating,"pictrue1Url":pictrue1Url,"picture2Url":picture2Url,"picture3Url":picture3Url})
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
        return {"code":999, "msg":"档口评论获取失败"}

#@13 评价评论函数(老唐版)
def evaluationComment(commentID, newEvaluation, token):
    db = Database.Database()
    response={}
    userName=""
    password=""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        userName = payload.get("userName")
        password = payload.get("password")
        db.connect()
        #先查找是否有过评价的经历
        response_search = db.execute_query("select * from UserComment where userName=%(userName)s, commentID=%(commentID)s",
            {"userName":userName,"commentID":commentID})
        if newEvaluation=="like":
            #如果是like且没有评价过，则插入一条记录，并将评论的推荐数加1；否则pass
            if not response_search:
                response = db.execute_query("insert into UserComment (userName, commentID) values (%(userName)s,%(commentID)s))",
                    {"userName":userName,"commentID":commentID})
                response_add_like = db.execute_query("update StallComment set recommendCount = recommendCount + 1 where ID = %(commentID)s",{"commentID":commentID})
                print(response, response_add_like)
            else:
                pass
        elif newEvaluation=="none":
            #如果是none且评价过，则删除该记录，并将评论的推荐数-1，否则pass
            if response_search:
                response = db.execute_query("delete from UserComment where userName=%(userName)s, commentID=%(commentID)s)",
                    {"userName":userName,"commentID":commentID})
                response_delete_like = db.execute_query("update StallComment set recommendCount = greatest(recommendCount-1,0) where ID = %(commentID)s",{"commentID":commentID})
                print(response, response_delete_like)
            else:pass
        db.disconnect()
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
        return {"code":999, "msg":"评价评论失败"}
    
#@14 获取菜品列表(老唐版)
def getStallDishList(stallID, token):
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
        response = db.execute_query("""select d.ID,d.name,d.price,d.recommendCount as `like`,
            d.dislikeCount as bad,d.pictureUrl, coalesce(de.evaluation, 'none') as evaluation
            from Dish d left join DishEvaluation de on d.ID = de.dishID and de.userName = %(userName)s
            where d.stallID = %(stallID)s order by d.ID""",{"userName":userName, "stallID":stallID})
        db.disconnect()
        print("response")
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
        return {"code":200, "data": {"dishList":response, "token": token}}
    else:
        return {"code":999, "msg":"菜品列表获取失败"}

#@15 更新菜品评价函数(老唐版)
def evaluateDish(dishID, newEvaluation, token):
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
        if newEvaluation=="like":
            newEvaluation="赞"
        elif newEvaluation=="bad":
            newEvaluation="踩"
        else:
            newEvaluation="无"
        #使用数据库进行更新
        response = db.execute_query("update DishEvaluation set evaluation=%(newEvaluation)s where dishID=%(dishID)s", {"newEvaluation":newEvaluation, "dishID":dishID})
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
        return {"code":999, "msg":"菜品评价更新失败"}