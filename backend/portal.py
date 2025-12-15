# -*- coding: utf-8 -*-
"""
静态页面转发网关（Flask）
- 负责把用户访问的前端页面路径统一转发到 Vue 构建产物的入口文件 webIndex.html
- 同时提供静态资源文件(js/css/img等)的直接访问
- 谨慎处理兜底逻辑：/api/* 不做兜底，避免吞掉后端接口
项目结构与页面路径来源：Task 文档（见 README/任务说明）。
"""

import os
import inspect
from flask import Flask, send_from_directory, jsonify,request
from api import user
from api import food
from api.background import admin
from api.background import user as bg_user
from api.background import food as bg_food
from api.background import dish as bg_dish
from api.background import adminManage as bg_adm
# === 路径设置（相对 backend/ 目录） ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.normpath(os.path.join(BASE_DIR, "../frontend/dist"))
IMGREPO_DIR = os.path.normpath(os.path.join(BASE_DIR, "../imgRepo"))

# 创建 Flask 应用；static_url_path 设为空字符串，允许直接以 /assets/... 等路径访问静态文件
app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")
app.config['JSON_AS_ASCII'] = False

# 前端 SPA 的入口文件
INDEX_FILE = "home.html"  # frontend/dist/home.html

def _serve_index():
    """返回前端单页应用的入口文件。"""
    return send_from_directory(app.static_folder, INDEX_FILE)

def _extract_token_from_request():
    """从请求头或 Cookie 中提取 token。"""
    auth_header = request.headers.get("Authorization")
    if auth_header is not None:
        auth_header = auth_header.strip()
        if not auth_header:
            return None, "Authorization 头缺少 token"
        scheme, _, remainder = auth_header.partition(" ")
        if scheme.lower() == "bearer":
            token = remainder.strip()
            if not token:
                return None, "Authorization 头缺少 token"
            return token, None
        if " " in auth_header:
            return None, "Authorization 头格式错误"
        return auth_header, None

    cookie_token = request.cookies.get("token")
    if cookie_token:
        return cookie_token, None
    return None, "未检测到Token"

# === 业务健康检查（可选） ===
@app.get("/api/health")
def health():
    """简单存活探针，便于容器/负载均衡检查。"""
    return jsonify(code=200, msg="ok")

# === 验证 ===（1）
@app.get("/api/checkToken")
def api_check_token():
    """
    Token 校验 API 接口。
    负责从 Cookie 中获取 Token，并调用 user 模块的 checkToken 函数。
    """
    # 1. 从请求头的Authorization字段调取token
    token, token_error = _extract_token_from_request()
    # 2. 若不含token，回报401 UnAuthorized
    if not token:
        return jsonify(code=998, msg=token_error), 401

    # 3. 调用 user.py 中的业务逻辑
    try:
        # user.checkToken 会处理验证、数据库查询和新 token 的生成
        response_data = user.checkToken(token)

        # 4. 根据业务逻辑的返回码，决定 HTTP 状态码
        http_status_code = 200  # 默认 200
        if response_data.get("code") != 200:
            # 业务逻辑返回 998 (例如数据库中用户已不存在)
            http_status_code = 401  # 401 Unauthorized
        return jsonify(response_data), http_status_code

    except Exception as e:
        # 捕获 user.checkToken 中抛出的异常
        # 这通常意味着 Token 解码失败（例如：已过期、签名无效）
        print(f"Error calling user.checkToken: {e}")
        return jsonify(code=998, msg="Token无效或已过期"), 401

# === 登录 === （2）
@app.post("/api/user/login")  # 使用 app.post 来明确指定处理 POST 请求
def api_user_login():
    """
    用户登录 API 接口。
    负责从请求中解析 JSON 数据，并调用 user 模块的 login 函数。
    """
    # 1. 从请求体中获取 JSON 数据
    try:
        # 确保请求是 JSON 格式
        data = request.get_json()
        if not data:
            return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400

    # 2. 提取用户名和密码
    userName = data.get("userName")
    password = data.get("password")

    # 校验入参
    if not userName or not password:
        return jsonify(code=999, msg="用户名或密码错误"), 400

    # 3. 调用 user.py 中的业务逻辑
    try:
        response_data = user.login(userName, password)
        
        # 4. 根据业务逻辑的返回码，决定 HTTP 状态码
        http_status_code = 200 # 默认为 200
        if response_data.get("code") != 200:
            # 如果是业务错误（如密码错误），使用 401 (Unauthorized) 更符合 HTTP 语义
            http_status_code = 401 
            
        return jsonify(response_data), http_status_code
    
    except Exception as e:
        # 捕获 user.login 内部可能发生的未知错误（例如数据库连接失败）
        # 建议在实际生产中记录日志
        print(f"Error calling user.login: {e}") 
        return jsonify(code=999, msg="服务器内部错误"), 500
# === 按 Task 文档列出的前端路由逐一注册（查询字符串会被浏览器保留，无需后端感知） ===

# === 用户注册 === （3）
@app.post("/api/user/signUp")
def api_user_signUp():
    try:
        data = request.get_json()
        if not data:
            return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    userName = data.get("userName")
    nickName = data.get("nickName")
    password = data.get("password")
    if not userName or not nickName or not password:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = user.signUp(userName, nickName, password)
        http_status_code = 200 
        if response_data.get("code") != 200:
            http_status_code = 401 
            
        return jsonify(response_data), http_status_code
    
    except Exception as e:
        print(f"Error calling user.login: {e}") 
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 用户信息修改 === （4）
@app.post("/api/user/editInfo")
def api_user_editInfo():

    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    nickName = request.form.get("nickName")
    avatar = request.files.get("avatar")
    if not nickName:
        return jsonify(code=999, msg="参数不完整"), 400
    if not avatar:
        avatar = ""
    try:
        response_data = user.editInfo(nickName,avatar,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling user.editInfo: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 用户密码修改 === （5）
@app.post("/api/user/editPassword")
def api_user_editPassword():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    password = data.get("password")
    newPassword = data.get("newPassword")
    if not newPassword:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = user.editPassword(password, newPassword, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        new_token = None
        if isinstance(response_data.get("data"), dict):
            new_token = response_data.get("data").get("token")
        if new_token:
            resp = jsonify(response_data)
            resp.set_cookie("token", new_token)
            return resp, http_status_code
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling user.editPassword: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 用户信息获取 === （6）
@app.get("/api/user/getInfo")
def api_user_getInfo():
    token,token_error= _extract_token_from_request()
    if not token:
        return jsonify(code=999, msg=token_error), 401
    try:
        response_data = user.getInfo(token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling user.getInfo: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 用户评论获取 ===（7）
@app.get("/api/user/getCommentList")
def api_user_getCommentList():
    try:
        data_1 = request.args.get("numPerPage")
        data_2 = request.args.get("pageIndex")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data_1 is None or data_2 is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    numPerPage = data_1
    pageIndex = data_2
    if not numPerPage or not pageIndex:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = user.getCommentList(numPerPage,pageIndex,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling user.getCommentList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 用户评论删除 ===（8）
@app.post("/api/user/deleteComment")
def api_user_deleteComment():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    commentID = data.get("commentID")
    if not commentID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = user.deleteComment(commentID,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling user.deleteComment: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 档口列表获取 === (9)
@app.get("/api/food/getStallList")
def app_food_getStallList():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    try:
        type = request.args.get("type")
        canteen = request.args.get("canteen")
        orderBy = request.args.get("orderBy")
        collation = request.args.get("collation")
        numPerPage = request.args.get("numPerPage")
        pageIndex = request.args.get("pageIndex")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if not type or not canteen or not orderBy or not collation or not numPerPage or not pageIndex:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = food.getStallList(type, canteen, orderBy, collation, numPerPage, pageIndex, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling food.getStallList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 档口详细信息获取 === (10)
@app.get("/api/food/getStallInfo")
def app_food_getStallInfo():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    try:
        stallID = request.args.get("stallID")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if not stallID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = food.getStallInfo(stallID,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling food.getStallInfo: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 档口全部评论 === (11)
@app.get("/api/food/getStallCommentList")
def app_food_getStallCommentList():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    try:
        stallID = request.args.get("stallID")
        numPerPage = request.args.get("numPerPage")
        pageIndex = request.args.get("pageIndex")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if not stallID or not numPerPage or not pageIndex:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = food.getStallCommentList(stallID,numPerPage,pageIndex,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling food.getStallCommentList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 发表档口评论 === (12)
@app.post("/api/food/createStallComment")
def app_food_createStallComment():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    stallID = request.form.get("stallID")
    rating = request.form.get("rating")
    content = request.form.get("content")
    picture1 = request.files.get("picture1")
    picture2 = request.files.get("picture2")
    picture3 = request.files.get("picture3")
    # picture1/2/3 可选；仅强制要求 stallID, rating, content
    if not stallID or not rating or not content:
        return jsonify(code=999, msg="参数不完整"), 400
    if not picture1:
        picture1 = None
    if not picture2:
        picture2 = None
    if not picture3:
        picture3 = None
    try:
        response_data = food.createStallComment(stallID, rating, content, picture1, picture2, picture3, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling food.getStallCommentList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    

# === 评价评论 === (13)
@app.post("/api/food/evaluationComment")
def app_food_evaluationComment():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    commentID = data.get("commentID")
    newEvaluation = data.get("newEvaluation")
    if not commentID or not newEvaluation:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = food.evaluationComment(commentID,newEvaluation,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling food.evaluationComment: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 菜品列表获取 === (14)
@app.get("/api/food/getStallDishList")
def app_food_getStallDishList():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    try:
        stallID = request.args.get("stallID")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if not stallID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = food.getStallDishList(stallID,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling food.evaluationComment: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 菜品评论更改 === (15)
@app.post("/api/food/evaluateDish")
def app_food_evaluateDish():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=998, msg=token_error), 401
    dishID = data.get("dishID")
    newEvaluation = data.get("newEvaluation")
    if not dishID or not newEvaluation:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = food.evaluateDish(dishID,newEvaluation,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling food.evaluateDish: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 管理员token验证 === (16)
@app.get("/api/background/checkToken")
def api_background_checkToken():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    try:
        response_data = admin.checkToken(token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling admin.checkToken: {e}")
        return jsonify(code=997, msg="Token无效或已过期"), 401
    
# === 管理员登录 === (17)
@app.post("/api/background/admin/login")
def api_admin_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    ID = data.get("ID")
    password = data.get("password")
    if not ID or not password:
        return jsonify(code=999, msg="用户名或密码错误"), 400
    try:
        response_data = admin.login(ID, password)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401 
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling admin.login: {e}") 
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 管理员信息修改 === (18)
@app.post("/api/background/admin/editInfo")
def api_admin_editInfo():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    name = request.form.get("name")
    avatar = request.files.get("avatar")
    if not name or not avatar:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = admin.editInfo(name,avatar,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling admin.editInfo: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 管理员密码修改 === (19)
@app.post("/api/background/admin/editPassword")
def api_admin_editPassword():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    #提取新密码
    password = data.get("password")
    newPassword = data.get("newPassword")
    if not newPassword or not password:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = admin.editPassword(password, newPassword, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        #更新token
        new_token = None
        if isinstance(response_data.get("data"), dict):
            new_token = response_data.get("data").get("token")
        if new_token:
            resp = jsonify(response_data)
            resp.set_cookie("token", new_token)
            return resp, http_status_code
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling admin.editPassword: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 管理员信息获取 === (20)
@app.get("/api/background/admin/getInfo")
def api_admin_getInfo():
    token,token_error= _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    try:
        response_data = admin.getInfo(token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling admin.getInfo: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 后台用户信息获取 === (21)
@app.get("/api/background/user/getUserList")
def api_background_user_getUserList():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    try:
        userName = request.args.get("userName")
        nickName = request.args.get("nickName")
        status = request.args.get("status")
        numPerPage = request.args.get("numPerPage")
        pageIndex = request.args.get("pageIndex")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if userName is None or nickName is None or not status or not numPerPage or not pageIndex:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_user.getUserList(userName, nickName, status, numPerPage, pageIndex, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.user.getUserList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 后台重置用户密码 === (22)
@app.post("/api/background/user/resetPassword")
def api_background_user_resetPassword():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    userName = data.get("userName")
    if not userName:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_user.resetPassword(userName,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.user.resetPassword: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 后台冻结用户账号 === (23)
@app.post("/api/background/user/freezeAccount")
def api_background_user_freezeAccount():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    userName = data.get("userName")
    if not userName:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_user.freezeAccount(userName,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.user.freezeAccount: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台解冻用户账号 === (24)
@app.post("/api/background/user/defrostAccount")
def api_background_user_defrostAccount():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    userName = data.get("userName")
    if not userName:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_user.defrostAccount(userName,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.user.defrostAccount: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 后台获取档口列表  === (25)
@app.get("/api/background/food/getStallList")
def api_background_food_getStallList():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    try:
        name = request.args.get("name")
        type = request.args.get("type")
        canteen = request.args.get("canteen")
        numPerPage = request.args.get("numPerPage")
        pageIndex = request.args.get("pageIndex")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if not type or not canteen or name is None or not numPerPage or not pageIndex:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_food.getStallList(name, type, canteen, numPerPage, pageIndex, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.food.getStallList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 后台新增档口 === (26)
@app.post("/api/background/food/addStall")
def api_background_food_addStall():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    name = request.form.get("name")
    stall_type  = request.form.get("type")
    canteen = request.form.get("canteen")
    introduction = request.form.get("introduction")
    picture = request.files.get("picture")
    if not name or not stall_type  or not canteen or not introduction:
        return jsonify(code=999, msg="参数不完整"), 400
    print(f"name: {name}, type: {type(name)}")
    try:
        response_data = bg_food.addStall(name, stall_type , canteen, introduction, picture, token)
        http_status_code = 200 
        if response_data.get("code") != 200:
            http_status_code = 401 
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.food.addStall: {e}") 
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 后台档口信息修改 === (27)
@app.post("/api/background/food/editStallInfo")
def api_background_food_editStallInfo():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    ID = request.form.get("ID")
    name = request.form.get("name")
    type = request.form.get("type")
    canteen = request.form.get("canteen")
    introduction = request.form.get("introduction")
    picture = request.files.get("picture")
    if not name or not type or not canteen or not introduction:
        return jsonify(code=999, msg="参数不完整"), 400
    if not picture:
        picture = ""
    try:
        response_data = bg_food.editStallInfo(ID, name, type, canteen, introduction, picture, token)
        http_status_code = 200 
        if response_data.get("code") != 200:
            http_status_code = 401 
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.food.editStallInfo: {e}") 
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台删除档口 === (28)
@app.post("/api/background/food/deleteStall")
def api_background_food_deleteStall():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    ID = data.get("ID")
    if not ID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_food.deleteStall(ID,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.food.deleteStall: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台获取菜品 === (29)
@app.get("/api/background/dish/getDishList")
def api_background_dish_getDishList():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    try:
        stallID = request.args.get("stallID")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if not stallID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_dish.getDishList(stallID, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.dish.getDishList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台新增菜品 === (30)
@app.post("/api/background/dish/addDish")
def api_background_dish_addDish():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    stallID = request.form.get("stallID")
    name = request.form.get("name")
    price = request.form.get("price")
    picture = request.files.get("picture")
    if not stallID or not name or not price:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_dish.addDish(stallID,name,price,picture,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.dish.addDish: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台修改菜品信息 === (31)
@app.post("/api/background/dish/editDishInfo")
def api_background_dish_editDishInfo():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    ID = request.form.get("ID")
    name = request.form.get("name")
    price = request.form.get("price")
    picture = request.files.get("picture")
    if not ID or not name or not price:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_dish.editDishInfo(ID,name,price,picture,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.dish.editDishInfo: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台删除菜品 === (32)
@app.post("/api/background/dish/deleteDish")
def api_background_dish_deleteDish():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    ID = data.get("ID")
    if not ID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_dish.deleteDish(ID,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.dish.deleteDish: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台获取管理员列表 === (33)
@app.get("/api/background/adminManage/getAdminList")
def api_background_adminManage_getAdminList():
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    try:
        adminID = request.args.get("adminID")
        name = request.args.get("name")
        permission = request.args.get("permission")
        numPerPage = request.args.get("numPerPage")
        pageIndex = request.args.get("pageIndex")
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if adminID is None or name is None or permission is None or not numPerPage or not pageIndex:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_adm.getAdminList(adminID, name, permission, numPerPage, pageIndex, token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.adminManage.getAdminList: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

# === 后台重置管理员密码 === (34)
@app.post("/api/background/adminManage/resetPassword")
def api_background_adminManage_resetPassword():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    ID = data.get("ID")
    if not ID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_adm.resetPassword(ID,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.adminManage.resetPassword: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台删除管理员 === (35)
@app.post("/api/background/adminManage/deleteAdmin")
def api_bakcground_adminManage_deleteAdmin():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    ID = data.get("ID")
    if not ID:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_adm.deleteAdmin(ID,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.adminManage.deleteAdmin: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500
    
# === 后台新增管理员 === (36)
@app.post("/api/background/adminManage/addAdmin")
def api_background_adminManage_addAdmin():
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400
    if data is None:
        return jsonify(code=999, msg="请求体为空或非JSON格式"), 400
    token, token_error = _extract_token_from_request()
    if not token:
        return jsonify(code=997, msg=token_error), 401
    name = data.get("name")
    if not name:
        return jsonify(code=999, msg="参数不完整"), 400
    try:
        response_data = bg_adm.addAdmin(name,token)
        http_status_code = 200
        if response_data.get("code") != 200:
            http_status_code = 401
        return jsonify(response_data), http_status_code
    except Exception as e:
        print(f"Error calling background.adminManage.addAdmin: {e}")
        return jsonify(code=999, msg="服务器内部错误"), 500

@app.route("/imgRepo/<path:filename>")
def get_avatar(filename):
    return send_from_directory(IMGREPO_DIR, filename)

SPA_PATHS = [
    "/",                            # 根路径，直接交给前端路由决定去向（通常跳登录）
    "/home",
    "/user/login",
    "/user/signUp",
    "/user/personalInfo",
    "/user/editPassword",
    "/user/myComment",
    "/foodReview",
    "/foodReview/stall",
    "/foodReview/stall/dish",
    "/foodReview/stall/comment",
]

def _serve_page_for(route_path: str):
    """
    访问route_path(如/a/b),返回/a/b.html。
    若无该网页，则返回/home.html。
    """
    # 显式地将路径视为文件进行检查
    relative_path = route_path.strip("/") + ".html"
    candidate_html = os.path.join(app.static_folder, relative_path)
    
    # 使用 isfile 进行精确判断，避免目录干扰
    if os.path.isfile(candidate_html):
        return send_from_directory(app.static_folder, relative_path)
        
    return send_from_directory(app.static_folder, INDEX_FILE)

# 将上述路径全部映射到 SPA 入口
for route in SPA_PATHS:
    def _mk_handler(p=route):
        return lambda: _serve_page_for(p)
    endpoint_name = "spa_" + (route.strip("/") or "root").replace("/", "_")
    app.add_url_rule(route, endpoint=endpoint_name, view_func=_mk_handler(), methods=["GET"])

@app.get("/background")
@app.get("/background/")
@app.get("/background/<path:subpath>")
def background_root():
    return send_from_directory(app.static_folder,"background/index.html")

# === 兜底静态与路由 ===
@app.get("/<path:path>")
def fallback(path: str):
    """
    兜底逻辑（按优先级处理）：
      1) 若请求命中 dist 目录下的真实文件（如 /assets/...、/favicon.ico），直接返回该静态文件；
      2) 若是前端路由的深链接（如 /foodReview/stall?stallID=123），统一回送 SPA 入口文件；
      3) /api/* 前缀不做兜底，返回 404，交由后端接口服务实现或网关转发。
    """
    # 明确排除 /api/*，避免吞掉接口请求（接口文档规定所有接口均以 /api/ 开头）
    if path.startswith("api/"):
        return jsonify(code=404, msg="Not Found"), 404

    # 命中构建产物内的真实静态资源则直出
    candidate = os.path.join(app.static_folder, path)
    if os.path.isfile(candidate):
        return send_from_directory(app.static_folder, path)

    # 把深链接按“基础路径页面”处理（/a/b/c?x=1 -> /a/b/c）
    base_route = "/" + path  # query 已被 Flask 剥离，无需额外处理
    return _serve_page_for(base_route)

# === 启动服务 ===
# python -m flask --app portal run --port 8000
if __name__ == "__main__":
    # 监听 0.0.0.0:8000，以满足“域名：localhost:8000”的本地开发访问需求
    app.run(host="0.0.0.0", port=8000, debug=True)
