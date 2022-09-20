# lighthouse_bot
Tencent Cloud Lighthouse auto boot up and shutdown  
#### 腾讯云轻量实例，自动开机关机工具
× 流量用完自动关机，并发送Telegram通知  
× 每月流量重置后，或者流量还没用完自动开机，并发送Telegram通知。  

1. 需要先通过@Botfather创建Telegram bot，获取到token 
2. 获取腾讯云API密钥
> 先登录上腾讯云官网，然后点开下面这个链接：https://console.cloud.tencent.com/cam/capi
3. 设置环境变量，添加脚本到crontab定时任务
```bash
# 多个用逗号分隔，以此类推
export ak="SecretId1,SecretId2,SecretId3" 
export sk="SecretKey1,SecretKey2,SecretKey3"
export regs="ap-hongkong,ap-singapore,ap-singapore"
export tgtoken="XXXXXXXX:YYYYYYYYYYYYYYYYYYYYYYY" # Telegram token

pip install -r requirements.pip
python3 ./main.py 
```

Python推荐用3.8  
