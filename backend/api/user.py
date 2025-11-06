import Database
import jwt
import time
secret_key = "salt256"
algorithm = "HS256"

""" test:
$headers = @{ "Cookie" = "token=..." }
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/checkToken -Method Get -Headers $headers
"""
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
        response=db.execute_query("select * from user where userName=%(userName)s AND password=%(password)s",{"userName":userName,"password":password})
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
def login(userName,password):
    db=Database.Database()
    db.connect()
    response=db.execute_query("select * from user where userName=%(userName)s AND password=%(password)s",{"userName":userName,"password":password})
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
