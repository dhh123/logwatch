####  Realtime log view script based on HTTP
####  基于http chuncked的日志实时查看脚本
* 基于http
* tornado 异步非阻塞ioloop
* python 2.x.x 
* 其他的代码里面有注释

####  使用
* 安装pip: `yum install -y python-setuptools`
* 安装tornado: `pip install tornado==4.3`
* 启动脚本: `python logwatcher.py /opt/logs(log-dir) 10086(port)`
* request: `http://yourmache:port/file/tail-num` exp ( http://127.0.0.1:10086/redis.log/100 if /opt/logs/下面有redis.log的话-_-)
* curl,safari,firefox都没问题，但是chrome 在请求第二个相同连接时，浏览器会延时几秒发请求包包给服务器

* mail: duanhonghui@conew.com or 991368911@qq.com
