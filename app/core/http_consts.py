# 此文件用于存放 请求 与 响应头 的 字段常量
# 1.1

HDR_REQUEST_ID = 'X-Request-Id'
# 统一定义请求关联ID的HTTP头名：用于客户端传入或服务端回传同一个请求标识，方便链路追踪
# 请求关联ID是一个用来标识一次请求的唯一字符串（例如 f3a1c8... 或 a8b2-...）
# 目的不是业务功能，而是排查问题与链路追踪，把同一次请求在各处的日志串起来：API网关、后端服务、数据库日志、审计日志都能用同一个ID对齐。
#
# 常见是客户端/网关生成一个ID放到请求头里，例如X-Request-Id: <uuid>
# 服务端接收后原样回传到响应头，并在日志里带上这个字段。


HDR_RESPONSE_TIME_MS = 'X-Response-Time-Ms'
# 统一定义响应耗时的HTTP头名，用于在响应头里返回服务端处理耗时，此处是毫秒，便于排查性能


HDR_CACHE_CONTROL = 'Cache-Control'
# 统一定义Cache-Control头名：用于控制客户端/代理缓存策略，比如no-store，max-age=60等
# Cache-Control是一个HTTP响应/请求头
# 用来告诉浏览器、反向代理（Nginx）、公司网关这些中间缓存层这份内容能不能缓存、能缓存多久、缓存时要不要先重新验证等


STATE_REQUEST_ID = 'request_id'
# request.state里保存request_id的key，用来把request_id放进FastAPI/Starlette的request.state
# request.state是Starlette给每个请求挂的临时存储区，用来在一次请求的生命周期里塞一些自定义数据，方便在中间件、依赖、路由处理函数之间传递