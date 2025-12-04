# ==============================================================================
# Copilot Backend API 自动化测试脚本
# 环境要求: PowerShell 7.0+
# 功能: 自动化生产测试数据、执行业务逻辑、并在结束后清理数据。
# ==============================================================================

# 配置区域
$BASE_URL = "http://localhost:8000"
$ADMIN_ID = "10000000"        # 修正为数据库中存在的管理员ID
$ADMIN_PWD = "123456"         # 请确保密码正确
$TIMESTAMP = Get-Date -Format "mm:ss"

# 动态生成的测试数据标识
$TEST_USER_NAME = "AutoUser_${TIMESTAMP}"
$TEST_USER_PWD = "password123"
$TEST_STALL_NAME = "${TIMESTAMP}"
$TEST_DISH_NAME = "${TIMESTAMP}"
$TEST_COMMENT_CONTENT = "AutoComment_${TIMESTAMP}: This is a test comment."

# 全局状态变量
$USER_TOKEN = $null
$ADMIN_TOKEN = $null
$TARGET_STALL_ID = $null
$TARGET_DISH_ID = $null
$TARGET_COMMENT_ID = $null

$IMG_DIR = Join-Path $PSScriptRoot "img"
$TEST_IMAGES = "f1.jpg", "f2.jpg", "f3.jpg", "f4.jpg" | 
               ForEach-Object { Join-Path $IMG_DIR $_ }



# ==============================================================================
# 辅助函数
# ==============================================================================

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    # 1. 输出到控制台 (带颜色)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Get-TestImage {
    param([int]$Index)
    if ($Index -lt 0 -or $Index -ge $TEST_IMAGES.Count) {
        throw "图片索引越界: $Index"
    }
    $path = $TEST_IMAGES[$Index]
    if (-not (Test-Path $path)) {
        throw "测试图片不存在: $path"
    }
    return Get-Item $path
}

# [修改] 发送请求并断言结果 (增加文件记录)
function Invoke-Api {
    param(
        [string]$Name,
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [hashtable]$Form = $null,
        [bool]$RequireSuccess = $true, # 是否要求 code=200
        [bool]$SkipIfNull = $false,    # 如果前置条件为空则跳过
        [string]$SkipReason = ""
    )

    if ($SkipIfNull) {
        Write-Log "SKIP: $Name ($SkipReason)" "Yellow"
        return $null
    }

    # 控制台输出: 不换行
    Write-Host -NoNewline "TEST: $Name ... "
    #Write-Output -NoNewline "TEST: $Name ... "
    try {
        $params = @{
            Uri     = "$BASE_URL$Uri"
            Method  = $Method
            Headers = $Headers
        }

        if ($Form) {
            $params.Form = $Form
        } elseif ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
            $params.ContentType = "application/json"
        }

        $response = Invoke-RestMethod @params -ErrorAction Stop
        
        $logResult = ""

        # 后端通常返回 {code: 200, data: ...}
        if ($RequireSuccess) {
            if ($response.code -eq 200) {
                Write-Host "PASS" -ForegroundColor Green
            } else {
                Write-Host "FAIL (Code: $($response.code), Msg: $($response.msg))" -ForegroundColor Red
            }
        } else {
            Write-Host "DONE (Code: $($response.code))" -ForegroundColor Cyan
        }
        
        return $response

    } catch {
        Write-Host "ERROR" -ForegroundColor Red
        Write-Host "Details: $_" -ForegroundColor DarkRed
        Write-Host $params.Body -ForegroundColor DarkGray
        return $null
    }
}

# ==============================================================================
# 测试流程开始
# ==============================================================================

Write-Log "=== 开始自动化测试流程 ===" "Cyan"
Write-Log "日志文件: $OUTPUT_FILE"
Write-Log "测试目标: $BASE_URL"
Write-Log "测试用户: $TEST_USER_NAME"
Write-Log "测试档口: $TEST_STALL_NAME"
Write-Log "img目录: $TEST_IMAGES"
try {
    # --------------------------------------------------------------------------
    # 1. 基础与用户认证 (User Auth)
    # --------------------------------------------------------------------------
    # [3] 用户注册
    Invoke-Api "用户注册" "/api/user/signUp" -Method POST -Body @{
        userName = $TEST_USER_NAME
        nickName = "Nick_${TIMESTAMP}"
        password = $TEST_USER_PWD
    } | Out-Null

    # [2] 用户登录
    $loginRes = Invoke-Api "用户登录" "/api/user/login" -Method POST -Body @{
        userName = $TEST_USER_NAME
        password = $TEST_USER_PWD
    }

    if ($loginRes.code -eq 200) {
        $USER_TOKEN = $loginRes.data.token
        Write-Log "  > 获取到 User Token" "Gray"
    } else {
        throw "用户登录失败，无法继续执行用户相关测试"
    }

    # [1] 验证 Token
    Invoke-Api "验证 Token" "/api/checkToken" -Headers @{ Authorization = $USER_TOKEN } | Out-Null

    # --------------------------------------------------------------------------
    # 2. 管理员认证 (Admin Auth) - 必须成功才能进行后续的数据生产
    # --------------------------------------------------------------------------
    # [17] 管理员登录
    $adminLoginRes = Invoke-Api "管理员登录" "/api/background/admin/login" -Method POST -Body @{
        ID       = $ADMIN_ID
        password = $ADMIN_PWD
    }

    if ($adminLoginRes.code -eq 200) {
        $ADMIN_TOKEN = $adminLoginRes.data.token
        Write-Log "  > 获取到 Admin Token" "Gray"
    } else {
        throw "管理员登录失败 (请检查脚本顶部的管理员账号密码)，无法创建测试数据"
    }

    # --------------------------------------------------------------------------
    # 3. 数据生产 (Producer Phase) - 档口与菜品
    # --------------------------------------------------------------------------
    # [25] 创建档口
    Invoke-Api "后台-新增档口" "/api/background/food/addStall" -Method POST -Headers @{ Authorization = $ADMIN_TOKEN } -Form @{
        name         = $TEST_STALL_NAME
        type         = "汉堡"
        canteen      = "槿园食堂"
        introduction = "Auto Generated Stall"
        picture      = Get-TestImage 0
    } | Out-Null
    # [24] 获取档口 ID (由于add接口不返回ID，需通过查询获取)
    $stallListRes = Invoke-Api "后台-查询档口ID" "/api/background/food/getStallList?name=$TEST_STALL_NAME&type=全部&canteen=全部&numPerPage=10&pageIndex=1" -Headers @{ Authorization = $ADMIN_TOKEN }
    
    # 逻辑: 遍历列表找到名字匹配的
    $targetStall = $stallListRes.data.stallList | Where-Object { $_.name -eq $TEST_STALL_NAME } | Select-Object -First 1
    
    if ($targetStall) {
        $TARGET_STALL_ID = $targetStall.ID
        Write-Log "  > 捕获测试档口 ID: $TARGET_STALL_ID" "Green"
    } else {
        Write-Log "  > 未找到刚才创建的档口，数据链断裂" "Red"
    }

    # [29] 创建菜品 (仅当档口创建成功)
    Invoke-Api "后台-新增菜品" "/api/background/dish/addDish" -Method POST -Headers @{ Authorization = $ADMIN_TOKEN } -Form @{
        stallID = $TARGET_STALL_ID
        name    = $TEST_DISH_NAME
        price   = "12.50"
        picture = Get-TestImage 1
    } -SkipIfNull ($null -eq $TARGET_STALL_ID) -SkipReason "Stall ID missing" | Out-Null

    # [28] 获取菜品 ID
    $dishListRes = Invoke-Api "后台-查询菜品ID" "/api/background/dish/getDishList?stallID=$TARGET_STALL_ID" -Headers @{ Authorization = $ADMIN_TOKEN } -SkipIfNull ($null -eq $TARGET_STALL_ID) -SkipReason "Stall ID missing"
    
    if ($dishListRes) {
        $targetDish = $dishListRes.data.dishList | Where-Object { $_.name -eq $TEST_DISH_NAME } | Select-Object -First 1
        if ($targetDish) {
            $TARGET_DISH_ID = $targetDish.ID
            Write-Log "  > 捕获测试菜品 ID: $TARGET_DISH_ID" "Green"
        }
    }

    # --------------------------------------------------------------------------
    # 4. 业务逻辑消费 (Consumer Phase) - 用户交互
    # --------------------------------------------------------------------------

    # [10] 获取档口详情
    Invoke-Api "前台-获取档口详情" "/api/food/getStallInfo?stallID=$TARGET_STALL_ID" -Headers @{ Authorization = $USER_TOKEN } -SkipIfNull ($null -eq $TARGET_STALL_ID) -SkipReason "Stall ID missing" | Out-Null

    # [12] 发表评论
    Invoke-Api "前台-发表评论" "/api/food/createStallComment" -Method POST -Headers @{ Authorization = $USER_TOKEN } -Form @{
        stallID     = $TARGET_STALL_ID
        rating      = 5
        content     = $TEST_COMMENT_CONTENT
        picture1Url = ""
        picture2Url = ""
        picture3Url = ""
    } -SkipIfNull ($null -eq $TARGET_STALL_ID) -SkipReason "Stall ID missing" | Out-Null

    # [7] 获取并捕获评论 ID (查询用户自己的评论列表)
    $userCommentsRes = Invoke-Api "前台-查询评论列表" "/api/user/getCommentList?numPerPage=10&pageIndex=1" -Headers @{ Authorization = $USER_TOKEN }
    
    if ($userCommentsRes) {
        $targetComment = $userCommentsRes.data.comments | Where-Object { $_.content -eq $TEST_COMMENT_CONTENT } | Select-Object -First 1
        if ($targetComment) {
            $TARGET_COMMENT_ID = $targetComment.ID
            Write-Log "  > 捕获测试评论 ID: $TARGET_COMMENT_ID" "Green"
        } else {
             Write-Log "  > 未找到刚发布的评论" "Red"
        }
    }

    # [13] 评论点赞 (需要 CommentID)
    Invoke-Api "前台-点赞评论" "/api/food/evaluationComment" -Method POST -Headers @{ Authorization = $USER_TOKEN } -Body @{
        commentID     = $TARGET_COMMENT_ID
        newEvaluation = "like"
    } -SkipIfNull ($null -eq $TARGET_COMMENT_ID) -SkipReason "Comment ID missing" | Out-Null

    # [15] 菜品评价 (需要 DishID)
    Invoke-Api "前台-评价菜品" "/api/food/evaluateDish" -Method POST -Headers @{ Authorization = $USER_TOKEN } -Body @{
        dishID        = $TARGET_DISH_ID
        newEvaluation = "like"
    } -SkipIfNull ($null -eq $TARGET_DISH_ID) -SkipReason "Dish ID missing" | Out-Null


    # --------------------------------------------------------------------------
    # 5. 数据清理 (Cleanup Phase) - 倒序删除
    # --------------------------------------------------------------------------
    Write-Log "=== 进入数据清理阶段 ===" "Cyan"

    # [8] 删除用户评论 (用户自己删)
    Invoke-Api "清理-删除评论" "/api/user/deleteComment" -Method POST -Headers @{ Authorization = $USER_TOKEN } -Body @{
        commentID = $TARGET_COMMENT_ID
    }-SkipIfNull ($null -eq $TARGET_COMMENT_ID) -SkipReason "Comment ID missing" | Out-Null

    # [31] 删除菜品 (管理员删)
    Invoke-Api "清理-删除菜品" "/api/background/dish/deleteDish" -Method POST -Headers @{ Authorization = $ADMIN_TOKEN } -Body @{
        ID = $TARGET_DISH_ID
    } -SkipIfNull ($null -eq $TARGET_DISH_ID) -SkipReason "Dish ID missing" | Out-Null

    # [27] 删除档口 (管理员删 - 级联删除理论上会删掉菜品和评论，但手动删更保险)
    Invoke-Api "清理-删除档口" "/api/background/food/deleteStall" -Method POST -Headers @{ Authorization = $ADMIN_TOKEN } -Body @{
        ID = $TARGET_STALL_ID
    } -SkipIfNull ($null -eq $TARGET_STALL_ID) -SkipReason "Stall ID missing" | Out-Null

} catch {
    Write-Log "脚本执行过程中发生严重错误: $_" "Red"
} finally {
    Write-Log "=== 测试流程结束 ===" "Cyan"
}
