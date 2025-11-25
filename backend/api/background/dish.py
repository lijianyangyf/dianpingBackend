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
    
#@28 后台菜品获取函数(老唐版)
def getDishList(stallID,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("select ID,name,price,recommendCount as 'like',dislikeCount as bad,pictureUrl from Dish where stallID=%(stallID)s",{"stallID":stallID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"getDishList: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"getDishList: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        dishList = []
        if response and len(response) > 0:
            for row in response:
                if isinstance(row, dict):
                    dish = {
                        "ID": int(row.get("ID")),
                        "name": row.get("name"),
                        "price": float(row.get("rating", 0)),
                        "like": int(row.get("meanPrice")),
                        "bad": int(row.get("canteen")),
                        "pictureUrl": row.get("pictureUrl")
                    }
                else:
                    dish = {
                        "ID": int(row[0]) if len(row) > 0 else 0,
                        "name": row[1] if len(row) > 1 else "",
                        "price": float(row[2]) if len(row) > 2 and row[2] is not None else 0.0,
                        "like": int(row[3]) if len(row) > 3 and row[3] is not None else 0,
                        "bad": int(row[4]) if len(row) > 4 and row[4] is not None else 0,
                        "pictureUrl": row[5] if len(row) > 6 else ""
                    }
                dishList.append(dish)
        return {"code":200, "data": {"dishList":dishList}}
    else:
        return {"code":999, "msg":"后台菜品获取失败"}
    
#@29 后台新增菜品函数(老唐版)
def addDish(stallID,name,price,picture,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        if picture:
            saveUrl = os.path.join(IMGREPO_DIR, f"dish_{name}_picture.png")
            picture.save(saveUrl)
            pictureUrl = f"/imgRepo/dish_{name}_picture.png"
        db.connect()
        response = db.execute_query("insert into Dish (name,price,stallID,pictureUrl) values (%(name)s,%(price)s,%(stallID)s,%(pictureUrl)s)",
            {"name":name,"price":price,"stallID":stallID,"pictureUrl":pictureUrl})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"addDish: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"addDish: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"菜品新增失败"}
    
#@30 后台编辑菜品函数(老唐版)
def editDishInfo(ID,name,price,picture,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        if picture:
            saveUrl = os.path.join(IMGREPO_DIR, f"dish_{name}_picture.png")
            picture.save(saveUrl)
            pictureUrl = f"/imgRepo/dish_{name}_picture.png"
        db.connect()
        response = db.execute_query("update Dish set name=%(name)s,price=%(price)s,pictureUrl=%(pictureUrl)s where ID=%(ID)s",
            {"name":name,"price":price,"pictureUrl":pictureUrl,"ID":ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"editDishInfo: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"editDishInfo: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"菜品修改失败"}
    
#@31 后台删除菜品函数(老唐版)
def deleteDish(ID,token):
    db=Database.Database()
    response={}
    try:
        token_check = checkToken(token)
        if token_check.get("code") != 200:
            return token_check
        db.connect()
        response = db.execute_query("delete from Dish where ID=%(ID)s",{"ID":ID})
        db.disconnect()
        print(response)
    except jwt.ExpiredSignatureError:
        return {"code": 999, "msg": "Token 已过期"}
    except jwt.InvalidTokenError as e:
        print(f"addDish: Token 无效: {e}")
        return {"code": 999, "msg": "Token 无效"}
    except Exception as e:
        print(f"addDish: 其他错误: {e}")
        return {"code": 999, "msg": f"服务器错误: {str(e)}"}
    if response is not None:
        return {"code":200}
    else:
        return {"code":999, "msg":"菜品删除失败"}