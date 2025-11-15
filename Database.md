-- 1. 用户表 (User)
CREATE TABLE IF NOT EXISTS User (
    userName VARCHAR(20) NOT NULL PRIMARY KEY COMMENT '主键',
    nickName VARCHAR(20) NOT NULL,
    password VARCHAR(20) NOT NULL COMMENT '至少8位，字母数字',
    avatarUrl CHAR(255) COMMENT '头像图片的url'
) COMMENT='用户表';

-- 2. 店铺表 (Stall)
CREATE TABLE IF NOT EXISTS Stall (
    ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    name VARCHAR(10) NOT NULL,
    rating FLOAT NOT NULL DEFAULT 5.0 COMMENT '店铺评分 1.0~5.0，定期统计更新',
    meanPrice FLOAT NOT NULL COMMENT '人均价格，定期统计更新',
    signatureDish VARCHAR(255) COMMENT '招牌菜名字',
    introduction TEXT COMMENT '简介',
    type varchar(20) NOT NULL COMMENT '分类，假设的枚举值',
    canteen ENUM('榕园','荔园','槿园','若海') NOT NULL COMMENT '饭堂，假设的枚举值',
    pictureUrl CHAR(255) NOT NULL COMMENT '档口图片的url'
) AUTO_INCREMENT = 1 COMMENT='店铺表';

-- 3. 菜品表 (Dish)
CREATE TABLE IF NOT EXISTS Dish (
    ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    name VARCHAR(10) NOT NULL,
    price FLOAT NOT NULL,
    recommendCount INT NOT NULL DEFAULT 0 COMMENT '点赞数，定期统计更新',
    dislikeCount INT NOT NULL DEFAULT 0 COMMENT '踩数，定期统计更新',
    stallID INT NOT NULL COMMENT '所属店铺ID，外键',
    pictureUrl CHAR(255) COMMENT '菜品图片URL',
    
    FOREIGN KEY (stallID) REFERENCES Stall(ID)
) COMMENT='菜品表';

-- 4. 店铺评论表 (StallComment)
CREATE TABLE IF NOT EXISTS StallComment (
    ID INT AUTO_INCREMENT PRIMARY KEY COMMENT '评价ID，主键',
    userName VARCHAR(20) NOT NULL COMMENT '用户名，外键',
    stallID INT NOT NULL COMMENT '店铺ID，外键',
    content TEXT NOT NULL COMMENT '评论内容',
    rating INT NOT NULL COMMENT '评分星级 1到5星',
    picture1Url VARCHAR(255),
    picture2Url VARCHAR(255),
    picture3Url VARCHAR(255),
    recommendCount INT NOT NULL DEFAULT 0 COMMENT '该评论的点赞数（定期统计更新）',
    dateTime DATETIME NOT NULL COMMENT '评论时间',
    
    FOREIGN KEY (userName) REFERENCES User(userName),
    FOREIGN KEY (stallID) REFERENCES Stall(ID)
) COMMENT='店铺评论表';

-- 5. 用户评论表 (UserComment - 用于存储用户对店铺评论的点赞关系)
-- 根据 API 文档和数据字典，此表可能用于表示用户对评论的“评价”，但在 API 中有专门的 evaluationComment 接口。
-- 此处表结构保持数据字典的联合主键定义，字段名更新。
CREATE TABLE IF NOT EXISTS UserComment (
    userName VARCHAR(20) NOT NULL COMMENT '主键，外键',
    commentID INT NOT NULL COMMENT '主键，外键',
    
    PRIMARY KEY (userName, commentID),
    
    FOREIGN KEY (userName) REFERENCES User(userName),
    FOREIGN KEY (commentID) REFERENCES StallComment(ID)
) COMMENT='用户评论关系表';

-- 6. 菜品评价表 (DishEvaluation - 用户对菜品的赞/踩关系)
CREATE TABLE IF NOT EXISTS DishEvaluation (
    userName VARCHAR(20) NOT NULL COMMENT '主键，外键',
    dishID INT NOT NULL COMMENT '主键，外键',
    evaluation ENUM('踩', '赞', '无') COMMENT '踩，赞，无',
    
    PRIMARY KEY (userName, dishID),
    
    FOREIGN KEY (userName) REFERENCES User(userName),
    FOREIGN KEY (dishID) REFERENCES Dish(ID)
) COMMENT='菜品评价表';

-- 7. 管理员表 (Admin)
CREATE TABLE IF NOT EXISTS Admin (
    account INT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '账号，主键',
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL COMMENT '姓名',
    authority ENUM('超级管理员', '普通管理员') NOT NULL COMMENT '权限',
    
    -- 设置自增起始值
) AUTO_INCREMENT = 10000000 COMMENT='管理员表';

-- 为外键字段创建索引以提高查询性能
CREATE INDEX idx_dish_stallID ON Dish (stallID);
CREATE INDEX idx_stallcomment_userName ON StallComment (userName);
CREATE INDEX idx_stallcomment_stallID ON StallComment (stallID);
CREATE INDEX idx_usercomment_commentID ON UserComment (commentID);
CREATE INDEX idx_dishevaluation_dishID ON DishEvaluation (dishID);