import Database
import jwt
import time
import os
secret_key = "salt256"
algorithm = "HS256"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMGREPO_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../../imgRepo"))

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

#@24 后台获取档口列表函数(老唐版)————OK
def getStallList(name,type,canteen,numPerPage,pageIndex,token):
    db=Database.Database()
    response={}
    name = str(name) if name is not None else ""
    type = str(type) if type is not None else ""
    canteen = str(canteen) if canteen is not None else ""
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
        if name and name != "":
            where_conditions.append(f"name = '{name}'")
        if type and type != "全部":
            where_conditions.append(f"type = '{type}'")
        if canteen and canteen != "全部":
            where_conditions.append(f"canteen = '{canteen}'")
        where_clause = ""
        if where_conditions:
            where_clause = "where " + " and ".join(where_conditions)
        else:
            where_clause = ""
        base_query = f"select ID, name, rating, meanPrice, canteen, signatureDish, pictureUrl, type, introduction from Stall {where_clause}"
        offset = (pageIndex_int - 1) * numPerPage_int
        paginated_query = base_query + f" limit {numPerPage_int} offset {offset}"
        response = db.execute_query(paginated_query)
        response_rows = db.execute_query(f"select count(*) as total_rows from Stall {where_clause}")
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
        print(f"getStallList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getStallList: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        stallList = []
        if response and len(response) > 0:
            for row in response:
                if isinstance(row, dict):
                    stall = {
                        "ID": int(row.get("ID")),
                        "name": row.get("name"),
                        "rating": float(row.get("rating", 0)),
                        "meanPrice": float(row.get("meanPrice", 0)),
                        "canteen": row.get("canteen"),
                        "signatureDish": row.get("signatureDish"),
                        "pictureUrl": row.get("pictureUrl"),
                        "type": row.get("type"),
                        "introduction": row.get("introduction")
                    }
                else:
                    stall = {
                        "ID": int(row[0]) if len(row) > 0 else 0,
                        "name": row[1] if len(row) > 1 else "",
                        "rating": float(row[2]) if len(row) > 2 and row[2] is not None else 0.0,
                        "meanPrice": float(row[3]) if len(row) > 3 and row[3] is not None else 0.0,
                        "canteen": row[4] if len(row) > 4 else "",
                        "signatureDish": row[5] if len(row) > 5 else "",
                        "pictureUrl": row[6] if len(row) > 6 else "",
                        "type": row[7] if len(row) > 7 else "",
                        "introduction": row[8] if len(row) > 8 else ""
                    }
                stallList.append(stall)
        return {"code":200, "data": {"stallList":stallList, "totalPageNum":int(totalPageNum), "pageIndex":int(pageIndex)}}
    else:
        return {"code":999, "msg":"档口列表获取失败"}
    
#@25 后台新增档口函数(老唐版)
def addStall(name,type,canteen,introduction,picture,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        os.makedirs(IMGREPO_DIR, exist_ok=True)
        if picture and hasattr(picture, 'filename') and picture.filename:
            import re
            file_extension = os.path.splitext(picture.filename)[1] if '.' in picture.filename else '.png'
            safe_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name)
            filename = f"stall_{safe_name}_picture{file_extension}"
            saveUrl = os.path.join(IMGREPO_DIR, filename)
            picture.save(saveUrl)
            pictureUrl = f"/imgRepo/{filename}"
        else:
            return {"code": 999, "msg": "图片文件无效"}
        db.connect()
        response = db.execute_query("insert into Stall (name,type,rating,canteen,introduction,pictureUrl,meanPrice) values (%(name)s,%(type)s,%(rating)s,%(canteen)s,%(introduction)s,%(pictureUrl)s,%(meanPrice)s)",
            {"name":name,"type":type,"rating":5.0,"canteen":canteen,"introduction":introduction,"pictureUrl":pictureUrl,"meanPrice":0.0})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"addStall: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"addStall: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"档口新增失败"}
    
#@26 后台档口信息修改函数(老唐版)
def editStallInfo(ID,name,type,canteen,introduction,picture,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        os.makedirs(IMGREPO_DIR, exist_ok=True)
        if picture and hasattr(picture, 'filename') and picture.filename:
            import re
            file_extension = os.path.splitext(picture.filename)[1] if '.' in picture.filename else '.png'
            safe_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name)
            filename = f"stall_{safe_name}_picture{file_extension}"
            saveUrl = os.path.join(IMGREPO_DIR, filename)
            picture.save(saveUrl)
            pictureUrl = f"/imgRepo/{filename}"
        else:
            return {"code": 999, "msg": "图片文件无效"}
        db.connect()
        response = db.execute_query("update Stall set name=%(name)s,type=%(type)s,canteen=%(canteen)s,introduction=%(introduction)s,pictureUrl=%(pictureUrl)s where ID=%(ID)s",
            {"name":name,"type":type,"canteen":canteen,"introduction":introduction,"pictureUrl":pictureUrl,"ID":ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"editStallInfo: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"editStallInfo: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"档口信息修改失败"}

#@27 后台删除档口函数(老唐版)————OK
def deleteStall(ID,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        db.execute_query("delete uc from UserComment uc inner join StallComment sc on uc.commentID = sc.ID where sc.stallID = %(stallID)s",
            {"stallID": ID})
        db.execute_query("delete from StallComment where stallID = %(stallID)s",
            {"stallID": ID})
        db.execute_query("delete de from DishEvaluation de inner join Dish d on de.dishID = d.ID where d.stallID = %(stallID)s",
            {"stallID": ID})
        db.execute_query("delete from Dish where stallID = %(stallID)s",
            {"stallID": ID})
        response = db.execute_query("delete from Stall where ID=%(ID)s",
            {"ID":ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"deleteStall: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"deleteStall: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"档口删除失败"}
