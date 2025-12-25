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
from functools import wraps
from flask import Flask, send_from_directory, jsonify, request, g
from dotenv import load_dotenv
from api import user
from api import food
from api.background import admin
from api.background import user as bg_user
from api.background import food as bg_food
from api.background import dish as bg_dish
from api.background import adminManage as bg_adm
import scheduler

# 加载 .env
load_dotenv()

# === 路径设置（相对 backend/ 目录） ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.normpath(os.path.join(BASE_DIR, "../frontend/dist"))
IMGREPO_DIR = os.path.normpath(os.path.join(BASE_DIR, "../imgRepo"))

# 创建 Flask 应用；static_url_path 设为空字符串，允许直接以 /assets/... 等路径访问静态文件
app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")
app.config['JSON_AS_ASCII'] = False
# 设置 Secret Key
app.secret_key = os.getenv("SECRET_KEY", "dev-default-secret-key")

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


def _build_response(response_data, success_code=200, fail_status=401):
    """统一构建响应"""
    http_status = 200 if response_data.get("code") == success_code else fail_status
    return jsonify(response_data), http_status


# ==================== 装饰器 ====================

def require_token(error_code=998):
    """
    Token 验证装饰器
    - 用户端 API 使用 error_code=998
    - 后台 API 使用 error_code=997
    验证通过后，token 存入 g.token
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token, error = _extract_token_from_request()
            if not token:
                return jsonify(code=error_code, msg=error), 401
            from flask import g
            g.token = token
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_json(*required_fields):
    """
    JSON 请求体解析装饰器
    - 自动解析 JSON 并验证必填字段
    - 解析结果存入 g.json_data
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = request.get_json()
            except Exception as e:
                return jsonify(code=999, msg=f"JSON解析失败: {str(e)}"), 400

            if not data:
                return jsonify(code=999, msg="请求体为空或非JSON格式"), 400

            # 验证必填字段
            missing = [field for field in required_fields if not data.get(field)]
            if missing:
                return jsonify(code=999, msg=f"参数不完整，缺少: {', '.join(missing)}"), 400

            from flask import g
            g.json_data = data
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_args(*required_fields):
    """
    GET 请求参数验证装饰器
    - 验证必填的 query 参数
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            missing = [field for field in required_fields if not request.args.get(field)]
            if missing:
                return jsonify(code=999, msg=f"参数不完整，缺少: {', '.join(missing)}"), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def handle_exceptions(service_name="service"):
    """
    统一异常处理装饰器
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                print(f"Error in {service_name}: {e}")
                return jsonify(code=999, msg="服务器内部错误"), 500
        return wrapper
    return decorator


# ==================== 组合装饰器（常用场景） ====================

def user_api(json_fields=None, query_fields=None):
    """用户端 API 组合装饰器"""
    def decorator(f):
        wrapped = f
        wrapped = handle_exceptions(f.__name__)(wrapped)
        if json_fields:
            wrapped = require_json(*json_fields)(wrapped)
        if query_fields:
            wrapped = require_args(*query_fields)(wrapped)
        wrapped = require_token(error_code=998)(wrapped)
        return wrapped
    return decorator


def admin_api(json_fields=None, query_fields=None):
    """后台 API 组合装饰器"""
    def decorator(f):
        wrapped = f
        wrapped = handle_exceptions(f.__name__)(wrapped)
        if json_fields:
            wrapped = require_json(*json_fields)(wrapped)
        if query_fields:
            wrapped = require_args(*query_fields)(wrapped)
        wrapped = require_token(error_code=997)(wrapped)
        return wrapped
    return decorator


# === 业务健康检查（可选） ===
@app.get("/api/health")
def health():
    """简单存活探针，便于容器/负载均衡检查。"""
    return jsonify(code=200, msg="ok")

# === 验证 ===（1）
@app.get("/api/checkToken")
@require_token(error_code=998)
@handle_exceptions("user.checkToken")
def api_check_token():
    """Token 校验 API 接口"""
    response_data = user.checkToken(g.token)
    return _build_response(response_data)

# === 登录 === （2）
@app.post("/api/user/login")
@require_json("userName", "password")
@handle_exceptions("user.login")
def api_user_login():
    """用户登录 API 接口"""
    data = g.json_data
    response_data = user.login(data["userName"], data["password"])
    return _build_response(response_data)
# === 按 Task 文档列出的前端路由逐一注册（查询字符串会被浏览器保留，无需后端感知） ===

# === 用户注册 === （3）
@app.post("/api/user/signUp")
@require_json("userName", "nickName", "password")
@handle_exceptions("user.signUp")
def api_user_signUp():
    """用户注册 API 接口"""
    data = g.json_data
    response_data = user.signUp(data["userName"], data["nickName"], data["password"])
    return _build_response(response_data)

# === 用户信息修改 === （4）
@app.post("/api/user/editInfo")
@user_api()
def api_user_editInfo():
    """用户信息修改 API 接口"""
    nickName = request.form.get("nickName")
    if not nickName:
        return jsonify(code=999, msg="参数不完整"), 400
    avatar = request.files.get("avatar") or ""
    response_data = user.editInfo(nickName, avatar, g.token)
    return _build_response(response_data)

# === 用户密码修改 === （5）
@app.post("/api/user/editPassword")
@user_api(json_fields=["newPassword"])
def api_user_editPassword():
    """用户密码修改 API 接口"""
    data = g.json_data
    response_data = user.editPassword(data.get("password"), data["newPassword"], g.token)
    return _build_response(response_data)

# === 用户信息获取 === （6）
@app.get("/api/user/getInfo")
@user_api()
def api_user_getInfo():
    """用户信息获取 API 接口"""
    response_data = user.getInfo(g.token)
    return _build_response(response_data)

# === 用户评论获取 ===（7）
@app.get("/api/user/getCommentList")
@user_api(query_fields=["numPerPage", "pageIndex"])
def api_user_getCommentList():
    """用户评论获取 API 接口"""
    response_data = user.getCommentList(
        request.args.get("numPerPage"),
        request.args.get("pageIndex"),
        g.token
    )
    return _build_response(response_data)

# === 用户评论删除 ===（8）
@app.post("/api/user/deleteComment")
@user_api(json_fields=["commentID"])
def api_user_deleteComment():
    """用户评论删除 API 接口"""
    response_data = user.deleteComment(g.json_data["commentID"], g.token)
    return _build_response(response_data)

# === 档口列表获取 === (9)
@app.get("/api/food/getStallList")
@user_api(query_fields=["type", "canteen", "orderBy", "collation", "numPerPage", "pageIndex"])
def api_food_getStallList():
    """档口列表获取 API 接口"""
    args = request.args
    response_data = food.getStallList(
        args.get("type"), args.get("canteen"), args.get("orderBy"),
        args.get("collation"), args.get("numPerPage"), args.get("pageIndex"),
        g.token
    )
    return _build_response(response_data)

# === 档口详细信息获取 === (10)
@app.get("/api/food/getStallInfo")
@user_api(query_fields=["stallID"])
def api_food_getStallInfo():
    """档口详细信息获取 API 接口"""
    response_data = food.getStallInfo(request.args.get("stallID"), g.token)
    return _build_response(response_data)

# === 档口全部评论 === (11)
@app.get("/api/food/getStallCommentList")
@user_api(query_fields=["stallID", "numPerPage", "pageIndex"])
def api_food_getStallCommentList():
    """档口全部评论 API 接口"""
    response_data = food.getStallCommentList(
        request.args.get("stallID"),
        request.args.get("numPerPage"),
        request.args.get("pageIndex"),
        g.token
    )
    return _build_response(response_data)

# === 发表档口评论 === (12)
@app.post("/api/food/createStallComment")
@user_api()
def api_food_createStallComment():
    """发表档口评论 API 接口"""
    stallID = request.form.get("stallID")
    rating = request.form.get("rating")
    content = request.form.get("content")
    if not stallID or not rating or not content:
        return jsonify(code=999, msg="参数不完整"), 400
    picture1 = request.files.get("picture1") or None
    picture2 = request.files.get("picture2") or None
    picture3 = request.files.get("picture3") or None
    response_data = food.createStallComment(stallID, rating, content, picture1, picture2, picture3, g.token)
    return _build_response(response_data)
    

# === 评价评论 === (13)
@app.post("/api/food/evaluationComment")
@user_api(json_fields=["commentID", "newEvaluation"])
def api_food_evaluationComment():
    """评价评论 API 接口"""
    response_data = food.evaluationComment(g.json_data["commentID"], g.json_data["newEvaluation"], g.token)
    return _build_response(response_data)

# === 菜品列表获取 === (14)
@app.get("/api/food/getStallDishList")
@user_api(query_fields=["stallID"])
def api_food_getStallDishList():
    """菜品列表获取 API 接口"""
    response_data = food.getStallDishList(request.args.get("stallID"), g.token)
    return _build_response(response_data)

# === 菜品评论更改 === (15)
@app.post("/api/food/evaluateDish")
@user_api(json_fields=["dishID", "newEvaluation"])
def api_food_evaluateDish():
    """菜品评论更改 API 接口"""
    response_data = food.evaluateDish(g.json_data["dishID"], g.json_data["newEvaluation"], g.token)
    return _build_response(response_data)
    
# === 管理员token验证 === (16)
@app.get("/api/background/checkToken")
@require_token(error_code=997)
@handle_exceptions("admin.checkToken")
def api_background_checkToken():
    """管理员Token校验 API 接口"""
    response_data = admin.checkToken(g.token)
    return _build_response(response_data)
    
# === 管理员登录 === (17)
@app.post("/api/background/admin/login")
@require_json("ID", "password")
@handle_exceptions("admin.login")
def api_admin_login():
    """管理员登录 API 接口"""
    data = g.json_data
    response_data = admin.login(data["ID"], data["password"])
    return _build_response(response_data)

# === 管理员信息修改 === (18)
@app.post("/api/background/admin/editInfo")
@admin_api()
def api_admin_editInfo():
    """管理员信息修改 API 接口"""
    name = request.form.get("name")
    avatar = request.files.get("avatar")
    if not name or not avatar:
        return jsonify(code=999, msg="参数不完整"), 400
    response_data = admin.editInfo(name, avatar, g.token)
    return _build_response(response_data)
    
# === 管理员密码修改 === (19)
@app.post("/api/background/admin/editPassword")
@admin_api(json_fields=["password", "newPassword"])
def api_admin_editPassword():
    """管理员密码修改 API 接口"""
    data = g.json_data
    response_data = admin.editPassword(data["password"], data["newPassword"], g.token)
    return _build_response(response_data)
    
# === 管理员信息获取 === (20)
@app.get("/api/background/admin/getInfo")
@admin_api()
def api_admin_getInfo():
    """管理员信息获取 API 接口"""
    response_data = admin.getInfo(g.token)
    return _build_response(response_data)

# === 后台用户信息获取 === (21)
@app.get("/api/background/user/getUserList")
@admin_api(query_fields=["status", "numPerPage", "pageIndex"])
def api_background_user_getUserList():
    """后台用户信息获取 API 接口"""
    args = request.args
    response_data = bg_user.getUserList(
        args.get("userName", ""), args.get("nickName", ""),
        args.get("status"), args.get("numPerPage"), args.get("pageIndex"),
        g.token
    )
    return _build_response(response_data)

# === 后台重置用户密码 === (22)
@app.post("/api/background/user/resetPassword")
@admin_api(json_fields=["userName"])
def api_background_user_resetPassword():
    """后台重置用户密码 API 接口"""
    response_data = bg_user.resetPassword(g.json_data["userName"], g.token)
    return _build_response(response_data)

# === 后台冻结用户账号 === (23)
@app.post("/api/background/user/freezeAccount")
@admin_api(json_fields=["userName"])
def api_background_user_freezeAccount():
    """后台冻结用户账号 API 接口"""
    response_data = bg_user.freezeAccount(g.json_data["userName"], g.token)
    return _build_response(response_data)
    
# === 后台解冻用户账号 === (24)
@app.post("/api/background/user/defrostAccount")
@admin_api(json_fields=["userName"])
def api_background_user_defrostAccount():
    """后台解冻用户账号 API 接口"""
    response_data = bg_user.defrostAccount(g.json_data["userName"], g.token)
    return _build_response(response_data)

# === 后台获取档口列表  === (25)
@app.get("/api/background/food/getStallList")
@admin_api(query_fields=["type", "canteen", "numPerPage", "pageIndex"])
def api_background_food_getStallList():
    """后台获取档口列表 API 接口"""
    args = request.args
    response_data = bg_food.getStallList(
        args.get("name", ""), args.get("type"), args.get("canteen"),
        args.get("numPerPage"), args.get("pageIndex"), g.token
    )
    return _build_response(response_data)

# === 后台新增档口 === (26)
@app.post("/api/background/food/addStall")
@admin_api()
def api_background_food_addStall():
    """后台新增档口 API 接口"""
    form = request.form
    required = ["name", "type", "canteen", "introduction"]
    missing = [f for f in required if not form.get(f)]
    if missing:
        return jsonify(code=999, msg=f"参数不完整，缺少: {', '.join(missing)}"), 400

    response_data = bg_food.addStall(
        form.get("name"), form.get("type"), form.get("canteen"),
        form.get("introduction"), request.files.get("picture"),
        g.token
    )
    return _build_response(response_data)

# === 后台档口信息修改 === (27)
@app.post("/api/background/food/editStallInfo")
@admin_api()
def api_background_food_editStallInfo():
    """后台档口信息修改 API 接口"""
    form = request.form
    ID = form.get("ID")
    name = form.get("name")
    type = form.get("type")
    canteen = form.get("canteen")
    introduction = form.get("introduction")
    if not name or not type or not canteen or not introduction:
        return jsonify(code=999, msg="参数不完整"), 400
    picture = request.files.get("picture") or ""
    response_data = bg_food.editStallInfo(ID, name, type, canteen, introduction, picture, g.token)
    return _build_response(response_data)
    
# === 后台删除档口 === (28)
@app.post("/api/background/food/deleteStall")
@admin_api(json_fields=["ID"])
def api_background_food_deleteStall():
    """后台删除档口 API 接口"""
    response_data = bg_food.deleteStall(g.json_data["ID"], g.token)
    return _build_response(response_data)
    
# === 后台获取菜品 === (29)
@app.get("/api/background/dish/getDishList")
@admin_api(query_fields=["stallID"])
def api_background_dish_getDishList():
    """后台获取菜品 API 接口"""
    response_data = bg_dish.getDishList(request.args.get("stallID"), g.token)
    return _build_response(response_data)
    
# === 后台新增菜品 === (30)
@app.post("/api/background/dish/addDish")
@admin_api()
def api_background_dish_addDish():
    """后台新增菜品 API 接口"""
    stallID = request.form.get("stallID")
    name = request.form.get("name")
    price = request.form.get("price")
    if not stallID or not name or not price:
        return jsonify(code=999, msg="参数不完整"), 400
    response_data = bg_dish.addDish(stallID, name, price, request.files.get("picture"), g.token)
    return _build_response(response_data)
    
# === 后台修改菜品信息 === (31)
@app.post("/api/background/dish/editDishInfo")
@admin_api()
def api_background_dish_editDishInfo():
    """后台修改菜品信息 API 接口"""
    ID = request.form.get("ID")
    name = request.form.get("name")
    price = request.form.get("price")
    if not ID or not name or not price:
        return jsonify(code=999, msg="参数不完整"), 400
    response_data = bg_dish.editDishInfo(ID, name, price, request.files.get("picture"), g.token)
    return _build_response(response_data)
    
# === 后台删除菜品 === (32)
@app.post("/api/background/dish/deleteDish")
@admin_api(json_fields=["ID"])
def api_background_dish_deleteDish():
    """后台删除菜品 API 接口"""
    response_data = bg_dish.deleteDish(g.json_data["ID"], g.token)
    return _build_response(response_data)
    
# === 后台获取管理员列表 === (33)
@app.get("/api/background/adminManage/getAdminList")
@admin_api(query_fields=["numPerPage", "pageIndex"])
def api_background_adminManage_getAdminList():
    """后台获取管理员列表 API 接口"""
    args = request.args
    response_data = bg_adm.getAdminList(
        args.get("ID"), args.get("name"), args.get("permission"),
        args.get("numPerPage"), args.get("pageIndex"), g.token
    )
    return _build_response(response_data)

# === 后台重置管理员密码 === (34)
@app.post("/api/background/adminManage/resetPassword")
@admin_api(json_fields=["ID"])
def api_background_adminManage_resetPassword():
    """后台重置管理员密码 API 接口"""
    response_data = bg_adm.resetPassword(g.json_data["ID"], g.token)
    return _build_response(response_data)
    
# === 后台删除管理员 === (35)
@app.post("/api/background/adminManage/deleteAdmin")
@admin_api(json_fields=["ID"])
def api_bakcground_adminManage_deleteAdmin():
    """后台删除管理员 API 接口"""
    response_data = bg_adm.deleteAdmin(g.json_data["ID"], g.token)
    return _build_response(response_data)
    
# === 后台新增管理员 === (36)
@app.post("/api/background/adminManage/addAdmin")
@admin_api(json_fields=["name"])
def api_background_adminManage_addAdmin():
    """后台新增管理员 API 接口"""
    response_data = bg_adm.addAdmin(g.json_data["name"], g.token)
    return _build_response(response_data)
    
# === 手动触发评分更新（管理员接口） ===
@app.get("/api/background/triggerRatingUpdate")
@require_token(error_code=997)
@handle_exceptions("admin.triggerRatingUpdate")
def api_trigger_rating_update():
    """
    手动触发评分更新任务（仅限超级管理员）
    用于测试或紧急情况下手动更新所有店铺评分
    """
    # 验证管理员权限
    token_check = admin.checkToken(g.token)
    if token_check.get("code") != 200:
        return jsonify(code=997, msg="Token无效"), 401

    # 触发更新任务
    if scheduler.trigger_update():
        return jsonify(code=200, msg="更新任务已触发，请查看服务器日志"), 200
    else:
        return jsonify(code=999, msg="调度器未运行"), 500

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

# 避免 reloader 重复启动调度器
if os.environ.get("WERKZEUG_RUN_MAIN") != "false":
    # 首次加载或 reloader 子进程都会执行
    if not hasattr(scheduler.scheduler, '_started_flag'):
        scheduler.init_scheduler()
        scheduler.scheduler._started_flag = True

# === 启动服务 ===
# python -m flask --app portal run --port 8000
if __name__ == "__main__":
    # 监听 0.0.0.0:8000，以满足"域名：localhost:8000"的本地开发访问需求
    app.run(host="0.0.0.0", port=8000, debug=True)
