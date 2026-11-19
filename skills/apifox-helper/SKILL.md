---
name: apifox-helper
description: Apifox 接口文档工具集。功能1：导出接口文档 - 当用户说"导出接口文档"、"生成 apifox"、"导出到 apifox"时使用。功能2：枚举格式转换 - 当用户说"补充枚举项"、"补充枚举"、"填写枚举"、"转换枚举格式"、"文档里的枚举"、"apifox 枚举"、"枚举转 apifox"、"生成枚举 schema"时使用，将简单的枚举列表转换为 Apifox 的 x-apifox-enum JSON Schema 格式。
allowed-tools: Read, Write, Bash, Glob, Grep
disable-model-invocation: true
---

# Apifox 接口文档工具集 Skill

## 触发条件
当用户说以下内容时激活此 skill：

### 功能 1：导出接口文档
- "导出接口文档"
- "生成 apifox"
- "导出到 apifox"
- "生成接口文档 json"
- "帮我导出 xxx 接口"

### 功能 2：枚举格式转换
- "补充枚举项"
- "补充枚举"
- "填写枚举"
- "转换枚举格式"
- "文档里的枚举"
- "apifox 枚举"
- "枚举转 apifox"
- "生成枚举 schema"

## 功能说明

### 功能 1：接口文档导出
从代码中分析接口定义，生成可直接导入 Apifox 的 JSON 文件。

### 功能 2：枚举格式转换
将简单的枚举列表转换为 Apifox 的 x-apifox-enum JSON Schema 格式。

---

# 功能 2：枚举格式转换

## 输入格式
用户会提供简单的枚举列表，格式如下：
```
值1 名称1
值2 名称2
值3 名称3
```

**示例输入**：
```
01 语文
02 数学
03 英语
04 物理
```

## 输出格式
转换为 Apifox 的 JSON Schema 格式：

```json
{
    "type": "string",
    "enum": ["01", "02", "03", "04"],
    "x-apifox-enum": [
        {
            "value": "01",
            "name": "语文",
            "description": ""
        },
        {
            "value": "02",
            "name": "数学",
            "description": ""
        },
        {
            "value": "03",
            "name": "英语",
            "description": ""
        },
        {
            "value": "04",
            "name": "物理",
            "description": ""
        }
    ]
}
```

## 转换规则

1. **解析每行**：按空格分割，第一部分为 `value`，其余部分合并为 `name`
2. **生成 enum 数组**：提取所有 `value` 组成数组
3. **生成 x-apifox-enum 数组**：每个枚举项包含 `value`、`name`、`description`（默认为空字符串）
4. **保持顺序**：按输入顺序排列

## 特殊处理

### 带描述的输入
如果用户提供三列数据：
```
01 语文 语文学科
02 数学 数学学科
```

转换为：
```json
{
    "value": "01",
    "name": "语文",
    "description": "语文学科"
}
```

### 数字类型的值
如果值全是数字且用户指定为数字类型：
```json
{
    "type": "integer",
    "enum": [1, 2, 3, 4],
    "x-apifox-enum": [...]
}
```

默认情况下，值都作为字符串处理。

## 常见枚举参考（项目内）

### 学段 (segmentId)
```
1 学前
2 小学
3 初中
4 高中
```

### 年级 (gradeId)
```
00 学前
01 一年级
02 二年级
03 三年级
04 四年级
05 五年级
06 六年级
07 六年级
08 七年级
09 八年级
10 九年级
11 高一
12 高二
13 高三
14 初四
15 高四
```

### 学科 (courseId)
```
01 语文
02 数学
03 英语
04 物理
05 化学
06 历史
07 地理
08 政治
09 生物
10 日语
13 创客
14 通用
15 编程
16 体育
18 科学
19 俄语
```

---

# 功能 1：接口文档导出

## 执行步骤

### 1. 确定要导出的接口
用户会指定：
- 路由文件路径（如 `src/routes/resource.js`）
- 或具体接口路径（如 `/api/resource/videos`）
- 或 Controller 文件（如 `src/controllers/VideoController.js`）

### 2. 分析代码提取接口信息

#### 2.1 从路由文件提取
```javascript
// 路由定义模式
router.get('/videos', auth, VideoController.getList.bindVideoController));
router.post('/videos/:videoId/favorite', auth, VideoController.toggleFavorite.bind(VideoController));
```

提取：
- HTTP 方法 (get/post/put/delete)
- 路径 (含路径参数 :videoId)
- Controller 方法名

#### 2.2 从 Controller 提取
```javascript
/**
 * 获取视频列表
 * GET /api/resource/videos
 *
 * Query参数:
 * - pageNo: 页码（默认1）
 * - pageSize: 每页数量（默认20）
 * - keyword: 关键词搜索
 */
async getList(ctx) {
  const { pageNo = 1, pageSize = 20, keyword } = ctx.query;
  // ...
  ctx.body = {
    code: 200,
    message: '获取成功',
    data: { list, total, pageNo, pageSize }
  };
}
```

提取：
- 接口名称（从注释）
- 接口描述
- 请求参数（从 ctx.query / ctx.request.body / ctx.params）
- 响应结构（从 ctx.body）

### 3. 生成 Apifox JSON 格式

#### 3.1 项目结构
```json
{
  "apifoxProject": "1.0.0",
  "$schema": {
    "app": "apifox",
    "type": "project",
    "version": "1.2.0"
  },
  "info": {
    "name": "项目名称",
    "description": ""
  },
  "apiCollection": [
    {
      "name": "根目录",
      "items": [
        // 文件夹和接口
      ]
    }
  ],
  "environments": [],
  "schemaCollection": []
}
```

#### 3.2 文件夹结构
```json
{
  "name": "视频模块",
  "id": 生成唯一ID,
  "items": [
    // 接口列表
  ]
}
```

#### 3.3 单个接口结构
```json
{
  "name": "接口名称",
  "api": {
    "id": "生成唯一ID",
    "method": "get",
    "path": "/api/resource/videos",
    "parameters": {
      "query": [
        {
          "id": "生成唯一ID",
          "name": "pageNo",
          "required": false,
          "enable": true,
          "description": "页码（默认1）",
          "example": "1",
          "type": "string"
        }
      ],
      "path": [],
      "header": [],
      "cookie": []
    },
    "requestBody": {
      "type": "none"  // 或 "json" 带 jsonSchema
    },
    "responses": [
      {
        "id": "生成唯一ID",
        "code": 200,
        "name": "成功",
        "jsonSchema": {
          "type": "object",
          "properties": {
            "code": { "type": "integer", "description": "状态码" },
            "message": { "type": "string", "description": "提示信息" },
            "data": {
              "type": "object",
              "properties": {
                // 响应字段
              }
            }
          }
        },
        "contentType": "json"
      }
    ],
    "status": "released",
    "description": ""
  }
}
```

### 4. 参数类型映射

| JS 类型 | Apifox type |
|---------|-------------|
| String | "string" |
| Number/Int | "integer" |
| Float | "number" |
| Boolean | "boolean" |
| Array | "array" |
| Object | "object" |
| null | "null" |
| 可选 null | ["string", "null"] |

### 5. 枚举值处理
```json
{
  "name": "paperType",
  "type": "string",
  "schema": {
    "type": "string",
    "examples": ["月考", "期中", "期末"]
  }
}
```

### 6. 输出文件
将生成的 JSON 保存到 `ai/docs/apifox-export-{模块名}-{时间戳}.json`

## 关键字段说明

### 参数字段
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一标识，可用随机字符串 |
| name | string | 参数名 |
| required | boolean | 是否必填 |
| enable | boolean | 是否启用，通常为 true |
| description | string | 参数描述（中文） |
| example | string | 示例值 |
| type | string | 数据类型 |
| schema | object | 扩展定义（枚举等） |

### 响应 jsonSchema 字段
| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 数据类型 |
| properties | object | 对象属性定义 |
| items | object | 数组元素定义 |
| required | array | 必填字段列表 |
| x-apifox-orders | array | 字段显示顺序 |
| description | string | 字段描述 |

## 使用示例

用户: "帮我导出 /api/resource/videos 相关的接口文档"

执行:
1. 读取 `src/routes/resource.js` 找到 videos 相关路由
2. 读取 `src/controllers/VideoController.js` 分析接口详情
3. 生成 Apifox JSON
4. 保存到 `ai/docs/apifox-export-videos-20251213.json`
5. 告知用户文件位置，可直接导入 Apifox

## ID 生成规则
- 使用 10 位随机字母数字字符串
- 示例: `generateId()` => "aBcD1234Ef"

```javascript
function generateId() {
  return Math.random().toString(36).substring(2, 12);
}
```

## 注意事项

1. **描述信息**: 尽量从代码注释中提取，保留中文描述
2. **枚举值**: 从代码逻辑或注释中提取可能的枚举值
3. **必填判断**:
   - 有默认值的参数通常是非必填
   - 路径参数 (:id) 是必填
   - 从解构赋值中判断是否有默认值
4. **响应结构**: 从 ctx.body 赋值语句推断
5. **认证信息**: 如果有 auth 中间件，默认需要 Bearer Token
