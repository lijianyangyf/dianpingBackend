import Database
import jwt
import time
import os
secret_key = "salt256"
algorithm = "HS256"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMGREPO_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../imgRepo"))
"""
- **响应格式（成功）：**

    int code:200,

    class data:

    	recommendedStallList:[

    		int ID(档口的ID),

    		string name,

    		string type,

    		float rating(评分),

    		string signatureDish(招牌菜的名字),

    		float dishPrice(招牌菜价格),

    		string dishPictureUrl(招牌菜的图片)			

    	]

- **响应格式（失败）：**

    int code:999,

    msg:”请求推荐列表失败”
"""
def getRecommendedStall():
    """获取推荐档口列表"""
    db= Database.Database()
    try:
        db.connect()
        # 查询店铺基本信息
        response_stallInfo = db.execute_query(
            "SELECT ID,name,type,rating,signatureDish FROM Stall ORDER BY rating DESC LIMIT 6")
        # 检查店铺是否存在
        if not response_stallInfo or len(response_stallInfo) == 0:
            db.disconnect()
            return {"code": 999, "msg": "档口不存在"}
        result = []
        # 取出各档口的推荐菜品
        for recommendedStall in response_stallInfo:
            response_recommandedDishInfo = db.execute_query(
                "SELECT price,pictureUrl FROM Dish WHERE stallID = %(stallID)s AND name = %(name)s",
                {"stallID": recommendedStall[0], "name":recommendedStall[4]})
            
            dishPrice = 0
            dishPictureUrl = ""
            if response_recommandedDishInfo and len(response_recommandedDishInfo) >0:
                dishPrice = float(response_recommandedDishInfo[0][0])
                dishPictureUrl = response_recommandedDishInfo[0][1]
            print("success")
            result_stall = {
                "ID": recommendedStall[0],
                "name": recommendedStall[1],
                "type": recommendedStall[2],
                "rating": float(recommendedStall[3]),
                "signatureDish": recommendedStall[4],
                "dishPrice": dishPrice,
                "dishPictureUrl": dishPictureUrl
            }
            result.append(result_stall)
        db.disconnect()
        return {"code": 200, "data": {"recommendedStallList": result}}
    except Exception as e:
        db.disconnect()
        return {"code": 999, "msg": "请求推荐列表失败"}