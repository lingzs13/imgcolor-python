以安知鱼的[img2color-go](https://github.com/anzhiyu-c/img2color-go)为模板编写，为解决其方法不支持avif图片格式而制作。<br>
- 需要服务器。<br>
- 暂不支持`vercel`部署。<br>

使用方法
1.克隆本项目<br>
2.修改static/config.ini中的配置（不填写也能用，主要用来配置数据库做缓存加速）。<br>
3.将整个项目放到有python环境的docker中（我本人直接用的1panel的python允许环境中允许）。<br>
4.启动命令为
```
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple && pip config set install.trusted-host mirrors.aliyun.com  && pip install -r requirements.txt && python app.py runserver 0.0.0.0:5000
```

