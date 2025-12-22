# API

## 1. Send Prative Message

``` request
POST /api/v1/message/send
```

### 请求参数

``` json
{
  "self_id": 1817547029,
  "user_id": 2812703122,
  "time": 1766416525,
  "message_id": 1374201205,
  "message_seq": 59,
  "message_type": "private",
  "sender": {
    "user_id": 2812703122,
    "nickname": "夜影星辰",
    "card": ""
  },
  "raw_message": "测试",
  "font": 14,
  "sub_type": "friend",
  "message": [
    {
      "type": "text",
      "data": {
        "text": "测试"
      }
    }
  ],
  "message_format": "array",
  "post_type": "message",
  "raw_pb": ""
}
```
